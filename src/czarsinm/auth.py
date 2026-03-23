"""
Autenticação via Keycloak (OAuth2 Resource Owner Password Credentials).
"""

from __future__ import annotations

import base64
import json
import time
import logging
from typing import List, Optional

import requests

from .exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# Realm por ambiente
REALMS = {    
    "hml": "zarcnm-h",
    "prd": "zarcnm"    
}

KEYCLOAK_BASE = "https://www.keycloak.cnptia.embrapa.br/realms"


class KeycloakAuth:
    """
    Gerencia tokens de acesso do Keycloak.

    Faz cache do token e renova automaticamente quando próximo da expiração.
    """

    def __init__(
        self,
        username: str,
        password: str,
        client_id: str,
        client_secret: str,
        ambiente: str = "hml",
        keycloak_url: Optional[str] = None,
        keycloak_realm: Optional[str] = None,
        proxies: Optional[dict] = None,
    ):
        """
        Parameters
        ----------
        username:
            Login do usuário no Keycloak.
        password:
            Senha do usuário.
        client_id:
            Client ID fornecido pela equipe SINM.
        client_secret:
            Client secret fornecido pela equipe SINM.
        ambiente:
            'hml', 'prd' ou qualquer string para ambiente customizado.
            Em ambientes customizados, 'keycloak_url' e 'keycloak_realm'
            tornam-se obrigatórios.
        keycloak_url:
            URL base do Keycloak incluindo o segmento /realms
            (ex: 'https://meu-keycloak.exemplo.com/realms').
            Obrigatório para ambientes customizados; se None, usa a URL padrão da Embrapa.
        keycloak_realm:
            Nome do realm no Keycloak.
            Obrigatório para ambientes customizados; se None, usa o mapeamento
            padrão (hml → zarcnm-h, prd → zarcnm).
        proxies:
            Dicionário de proxies requests (ex: {'https': 'http://proxy:3128'}).
        """
        if ambiente not in REALMS and keycloak_url is None:
            raise ValueError(
                f"Ambiente '{ambiente}' não reconhecido. "
                "Para ambientes customizados, informe 'keycloak_url' "
                "(ou defina SINM_KEYCLOAK no arquivo .env)."
            )
        if ambiente not in REALMS and keycloak_realm is None:
            raise ValueError(
                f"Ambiente '{ambiente}' não reconhecido. "
                "Para ambientes customizados, informe 'keycloak_realm' "
                "(ou defina SINM_KEYCLOAK_REALM no arquivo .env)."
            )
        realm = keycloak_realm or REALMS.get(ambiente, ambiente)
        base = (keycloak_url or KEYCLOAK_BASE).rstrip("/")
        self._token_url = f"{base}/{realm}/protocol/openid-connect/token"

        self._credentials = {
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
            "scope": "openid profile email",
        }
        self._proxies = proxies
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float = 0.0
        self._refresh_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Público
    # ------------------------------------------------------------------

    @property
    def token(self) -> str:
        """Retorna um access token válido, renovando se necessário."""
        now = time.time()
        if self._access_token and now < self._expires_at - 30:
            return self._access_token

        if self._refresh_token and now < self._refresh_expires_at - 30:
            self._refresh()
        else:
            self._authenticate()

        return self._access_token  # type: ignore[return-value]

    @property
    def auth_header(self) -> dict:
        """Retorna o header Authorization pronto para uso em requests."""
        return {"Authorization": f"Bearer {self.token}"}

    @property
    def roles(self) -> List[str]:
        """Retorna os realm roles do usuário extraídos do token JWT."""
        _ = self.token  # garante que o token está carregado
        return self._decode_token_roles(self._access_token or "")

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    def _authenticate(self) -> None:
        """Obtém um novo par access_token / refresh_token."""
        logger.info("Autenticando no Keycloak: %s", self._token_url)
        try:
            resp = requests.post(
                self._token_url,
                data=self._credentials,
                timeout=15,
                proxies=self._proxies,
            )
        except requests.RequestException as exc:
            raise AuthenticationError(f"Falha na conexão com o Keycloak: {exc}") from exc

        if resp.status_code != 200:
            raise AuthenticationError(
                f"Keycloak retornou HTTP {resp.status_code}: {resp.text}"
            )
        logger.info("Usuário %s autenticado com sucesso no client %s", self._credentials["username"], self._credentials["client_id"])
        self._parse_token_response(resp.json())

    def _refresh(self) -> None:
        """Renova o token usando o refresh_token."""
        logger.debug("Renovando token via refresh_token")
        data = {
            "grant_type": "refresh_token",
            "client_id": self._credentials["client_id"],
            "client_secret": self._credentials["client_secret"],
            "refresh_token": self._refresh_token,
        }
        try:
            resp = requests.post(
                self._token_url,
                data=data,
                timeout=15,
                proxies=self._proxies,
            )
        except requests.RequestException as exc:
            raise AuthenticationError(f"Falha ao renovar token: {exc}") from exc

        if resp.status_code != 200:
            # Refresh falhou — tenta autenticação completa
            logger.warning("Refresh falhou (HTTP %s), reautenticando...", resp.status_code)
            self._authenticate()
            return

        self._parse_token_response(resp.json())

    def _parse_token_response(self, data: dict) -> None:
        now = time.time()
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token")
        self._expires_at = now + int(data.get("expires_in", 300))
        self._refresh_expires_at = now + int(data.get("refresh_expires_in", 1800))
        roles = self._decode_token_roles(self._access_token or "")
        logger.info("Token obtido, válido por %ss — roles: %s", data.get("expires_in"), roles)

    @staticmethod
    def _decode_token_roles(token: str) -> List[str]:
        """Extrai realm_access.roles do payload JWT sem verificar assinatura."""
        try:
            payload_b64 = token.split(".")[1]
            # Adiciona padding se necessário
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get("realm_access", {}).get("roles", [])
        except Exception:
            return []
