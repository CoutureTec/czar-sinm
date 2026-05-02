"""
Autenticação via Keycloak (OAuth2 Client Credentials).
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
        client_id: str,
        client_secret: str,
        ambiente: str = "hml",
        keycloak_url: Optional[str] = None,
        keycloak_realm: Optional[str] = None,
        proxies: Optional[dict] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        grant_type: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        client_id:
            CNPJ da empresa (Client ID no Keycloak).
        client_secret:
            Client secret fornecido pela equipe SiNM.
        ambiente:
            'hml', 'prd' ou qualquer string para ambiente customizado.
            Em ambientes customizados, 'keycloak_url' e 'keycloak_realm'
            tornam-se obrigatórios.
        keycloak_url:
            URL base do Keycloak incluindo o segmento /realms.
            Obrigatório para ambientes customizados.
        keycloak_realm:
            Nome do realm no Keycloak.
            Obrigatório para ambientes customizados.
        proxies:
            Dicionário de proxies requests (ex: {'https': 'http://proxy:3128'}).
        username, password:
            Usados apenas quando grant_type='password' (ROPC). Ignorados em
            client_credentials (default).
        grant_type:
            Opcional. Default 'client_credentials'. Use 'password' para ROPC
            (precisa username + password). Mantido como último parâmetro para
            preservar compatibilidade com chamadas posicionais existentes.
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

        effective_grant = grant_type or "client_credentials"
        if effective_grant == "password":
            if not username or not password:
                raise ValueError(
                    "grant_type='password' requer username e password."
                )
            self._credentials = {
                "grant_type": "password",
                "client_id": client_id,
                "client_secret": client_secret,
                "username": username,
                "password": password,
            }
        elif effective_grant == "client_credentials":
            self._credentials = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        else:
            raise ValueError(
                f"grant_type '{effective_grant}' não suportado. "
                "Use 'client_credentials' (default) ou 'password'."
            )
        self._grant_type = effective_grant
        self._proxies = proxies
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Público
    # ------------------------------------------------------------------

    @property
    def token(self) -> str:
        """Retorna um access token válido, renovando se necessário."""
        if self._access_token and time.time() < self._expires_at - 30:
            return self._access_token
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

    @property
    def client_roles(self) -> dict:
        """Retorna todos os client roles do usuário agrupados por client ID.

        Formato: {client_id: [role1, role2, ...]}
        """
        _ = self.token  # garante que o token está carregado
        return self._decode_client_roles(self._access_token or "")

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    def _authenticate(self) -> None:
        logger.info("Autenticando no Keycloak (%s): client=%s url=%s",
                    self._grant_type, self._credentials["client_id"], self._token_url)
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
        self._parse_token_response(resp.json())

    def _parse_token_response(self, data: dict) -> None:
        now = time.time()
        self._access_token = data["access_token"]
        self._expires_at = now + int(data.get("expires_in", 300))
        logger.info("Token obtido para client %s, válido por %ss",
                    self._credentials["client_id"], data.get("expires_in"))

    @staticmethod
    def _jwt_payload(token: str) -> dict:
        """Decodifica o payload de um JWT sem verificar assinatura."""
        try:
            payload_b64 = token.split(".")[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            return json.loads(base64.urlsafe_b64decode(payload_b64))
        except Exception:
            return {}

    @staticmethod
    def _decode_token_roles(token: str) -> List[str]:
        """Extrai realm_access.roles do payload JWT."""
        try:
            payload_b64 = token.split(".")[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get("realm_access", {}).get("roles", [])
        except Exception:
            return []

    @staticmethod
    def _decode_client_roles(token: str) -> dict:
        """Extrai resource_access do payload JWT.

        Retorna {client_id: [roles]} para todos os clients presentes no token.
        """
        try:
            payload_b64 = token.split(".")[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return {
                client: data.get("roles", [])
                for client, data in payload.get("resource_access", {}).items()
            }
        except Exception:
            return {}
