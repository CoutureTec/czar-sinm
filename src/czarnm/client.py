"""
ZarcNMClient — cliente HTTP para a API ZARC Nível de Manejo.

Fluxo principal:
  1. Autenticar (Keycloak) → token JWT
  2. Cadastrar talhão/gleba → retorna uuid + chaveClassificacaoNM
  3. Cadastrar análise de solo (vinculada à chave ou ao CPF)
  4. Cadastrar sensoriamento remoto (vinculado à chave ou ao CPF)
  5. Consultar resultado da classificação de nível de manejo
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from .auth import KeycloakAuth
from .exceptions import APIError, NotFoundError, PermissaoError, ValidationError
from .models import DadoGleba, AnaliseSolo, SensoriamentoRemoto, DadosInput

logger = logging.getLogger(__name__)

# URLs padrão por ambiente
API_URLS = {    
    "hml": "https://www.zarcnm-h.cnptia.embrapa.br/zarcnm",
    "prd": "https://www.zarcnm.cnptia.embrapa.br/zarcnm",
}

# Roles exigidos por prefixo de endpoint (ordem: mais específico primeiro)
_ENDPOINT_ROLES = [
    ("/api/v1/glebas",                  ["OPERADOR_CONTRATOS"]),
    ("/api/v1/operacoes",               ["OPERADOR_CONTRATOS"]),
    ("/api/v1/classificacoes",          ["OPERADOR_CONTRATOS",]),
    ("/api/v1/analises-solo",           ["OPERADOR_ANALISE_SOLO"]),
    ("/api/v1/sensoriamentos-remotos",  ["OPERADOR_SENSORIAMENTO_REMOTO"]),
]


def _roles_para_endpoint(path: str) -> list:
    for prefix, roles in _ENDPOINT_ROLES:
        if path.startswith(prefix):
            return roles
    return []


class ZarcNMClient:
    """
    Cliente para a API ZARC Nível de Manejo (ZARC-NM).

    Exemplo de uso::

        from czarnm import ZarcNMClient

        client = ZarcNMClient(
            username="meu.usuario@embrapa.br",
            password="minha_senha",
            client_id="meu-client-id",
            client_secret="meu-client-secret",
            ambiente="hml",
        )

        gleba = client.cadastrar_gleba(dado_gleba)
        chave = gleba["chaveClassificacaoNM"]

        client.cadastrar_analise_solo(analise, chave_classificacao_nm=chave)
        client.cadastrar_sensoriamento_remoto(sensoriamento, chave_classificacao_nm=chave)

        resultado = client.consultar_classificacao(chave)
    """

    def __init__(
        self,
        username: str,
        password: str,
        client_id: str,
        client_secret: str,
        ambiente: str = "hml",
        base_url: Optional[str] = None,
        keycloak_url: Optional[str] = None,
        proxies: Optional[dict] = None,
        timeout: int = 60,
    ):
        """
        Parameters
        ----------
        username:
            Login do usuário no Keycloak/ZARC-NM.
        password:
            Senha do usuário.
        client_id:
            Client ID fornecido pela equipe ZARC-NM.
        client_secret:
            Client secret fornecido pela equipe ZARC-NM.
        ambiente:
            'hml' ou 'prd'. Define realm e URL base automaticamente.
        base_url:
            URL base da API. Se None, usa o padrão do ambiente selecionado.
        keycloak_url:
            URL base do Keycloak. Se None, usa a URL padrão da Embrapa.
        proxies:
            Proxies para requests. Ex: {'https': 'http://proxy.cnptia.embrapa.br:3128'}
        timeout:
            Timeout em segundos para chamadas à API.
        """
        self._auth = KeycloakAuth(
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            ambiente=ambiente,
            keycloak_url=keycloak_url,
            proxies=proxies,
        )
        self._base_url = (base_url or API_URLS.get(ambiente, API_URLS["hml"])).rstrip("/")
        self._proxies = proxies
        self._timeout = timeout
        self._session = requests.Session()

    @property
    def roles(self) -> list:
        """Roles do usuário autenticado extraídos do token JWT."""
        return self._auth.roles

    # ------------------------------------------------------------------
    # Talhão / Gleba
    # ------------------------------------------------------------------

    def cadastrar_gleba(self, dado: DadoGleba) -> dict:
        """
        Cadastra um talhão/gleba na API.

        Returns
        -------
        dict
            Resposta da API com os dados resumidos da gleba, incluindo
            o campo 'chaveClassificacaoNM' necessário para as próximas etapas.

        Raises
        ------
        ValidationError
            Se o payload enviado contiver dados inválidos (HTTP 400/422).
        APIError
            Para outros erros HTTP.
        """
        return self._post("/api/v1/glebas", dado.to_dict())

    def buscar_gleba(self, uuid_gleba: str) -> dict:
        """Busca os dados de uma gleba pelo UUID."""
        return self._get(f"/api/v1/glebas/{uuid_gleba}")

    def listar_glebas(self) -> list:
        """Lista as glebas do usuário autenticado."""
        return self._get("/api/v1/glebas")

    # ------------------------------------------------------------------
    # Análise de Solo
    # ------------------------------------------------------------------

    def cadastrar_analise_solo(
        self,
        analise: AnaliseSolo,
        chave_classificacao_nm: Optional[str] = None,
    ) -> dict:
        """
        Cadastra uma análise de solo.

        Parameters
        ----------
        analise:
            Dados da análise de solo (amostras, CPF do produtor, CNPJ).
        chave_classificacao_nm:
            Chave retornada no cadastro da gleba. Se informada, vincula a
            análise ao talhão correspondente. Caso contrário, o vínculo é
            feito pelo CPF do produtor contido no payload.

        Returns
        -------
        dict
            Resumo da análise cadastrada.
        """
        if chave_classificacao_nm:
            path = f"/api/v1/analises-solo/{chave_classificacao_nm}"
        else:
            path = "/api/v1/analises-solo"
        return self._post(path, analise.to_dict())

    def buscar_analise_solo(self, uuid_analise: str) -> dict:
        """Busca uma análise de solo pelo UUID."""
        return self._get(f"/api/v1/analises-solo/{uuid_analise}")

    def listar_analises_solo(self) -> list:
        """Lista as análises de solo do usuário autenticado."""
        return self._get("/api/v1/analises-solo")

    # ------------------------------------------------------------------
    # Sensoriamento Remoto
    # ------------------------------------------------------------------

    def cadastrar_sensoriamento_remoto(
        self,
        sensoriamento: SensoriamentoRemoto,
        chave_classificacao_nm: str,
    ) -> dict:
        """
        Cadastra dados de sensoriamento remoto.

        Parameters
        ----------
        sensoriamento:
            Dados de monitoramento via satélite.
        chave_classificacao_nm:
            Chave retornada no cadastro da gleba. Obrigatória para vincular
            o sensoriamento ao talhão correspondente.

        Returns
        -------
        dict
            Resumo do sensoriamento cadastrado.
        """
        return self._post(
            f"/api/v1/sensoriamentos-remotos/{chave_classificacao_nm}",
            sensoriamento.to_dict(),
        )

    def buscar_sensoriamento_remoto(self, uuid_sensoriamento: str) -> dict:
        """Busca um sensoriamento remoto pelo UUID."""
        return self._get(f"/api/v1/sensoriamentos-remotos/{uuid_sensoriamento}")

    def listar_sensoriamentos_remotos(self) -> list:
        """Lista os sensoriamentos do usuário autenticado."""
        return self._get("/api/v1/sensoriamentos-remotos")

    # ------------------------------------------------------------------
    # Operação (fluxo combinado por UUIDs)
    # ------------------------------------------------------------------

    def cadastrar_operacao(self, dados: DadosInput) -> dict:
        """
        Executa a operação de classificação usando recursos já cadastrados.

        Recebe os UUIDs de uma gleba, análise de solo e sensoriamento remoto
        previamente registrados, junto com a produção atual e anteriores, e
        dispara o processamento da classificação de nível de manejo.

        Parameters
        ----------
        dados:
            DadosInput com uuidGleba, uuidAnaliseSolo, uuidSensoriamentoRemoto,
            producaoAtual e producoesAnteriores.

        Returns
        -------
        dict
            Resumo da operação (OperacaoNivelManejoResumoModel).
        """
        return self._post("/api/v1/operacoes", dados.to_dict())

    # ------------------------------------------------------------------
    # Classificação Nível de Manejo
    # ------------------------------------------------------------------

    def consultar_classificacao(self, chave_classificacao_nm: str) -> dict:
        """
        Consulta o resultado da classificação de nível de manejo.

        Parameters
        ----------
        chave_classificacao_nm:
            Chave obtida no cadastro do talhão/gleba.

        Returns
        -------
        dict
            Resultado completo da classificação (NivelManejoResumoModel).

        Raises
        ------
        NotFoundError
            Se a classificação não for encontrada.
        """
        return self._get(f"/api/v1/classificacoes/{chave_classificacao_nm}")

    def listar_classificacoes(self) -> list:
        """Lista todas as classificações do usuário autenticado."""
        return self._get("/api/v1/classificacoes")

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {
            **self._auth.auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, path: str, payload: dict) -> dict:
        url = self._base_url + path
        logger.debug("POST %s", url)
        try:
            resp = self._session.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self._timeout,
                proxies=self._proxies,
            )
        except requests.RequestException as exc:
            raise APIError(0, f"Erro de conexão: {exc}") from exc

        return self._handle_response(resp, path)

    def _get(self, path: str):
        url = self._base_url + path
        logger.debug("GET %s", url)
        try:
            resp = self._session.get(
                url,
                headers=self._headers(),
                timeout=self._timeout,
                proxies=self._proxies,
            )
        except requests.RequestException as exc:
            raise APIError(0, f"Erro de conexão: {exc}") from exc

        return self._handle_response(resp, path)

    def _handle_response(self, resp: requests.Response, path: str = ""):
        if resp.status_code in (200, 201, 204):
            if not resp.content:
                return {}
            return resp.json()

        try:
            body = resp.json()
        except Exception:
            body = {}

        raw = resp.text or ""
        message = body.get("detail") or body.get("message") or raw or "Sem corpo na resposta"
        if raw and "raw" not in body:
            body["raw"] = raw

        if resp.status_code == 403:
            roles_necessarios = _roles_para_endpoint(path)
            roles_usuario = self._auth.roles
            raise PermissaoError(
                resp.status_code,
                message,
                body,
                endpoint=path,
                roles_usuario=roles_usuario,
                roles_necessarios=roles_necessarios,
            )
        if resp.status_code == 404:
            raise NotFoundError(resp.status_code, message, body)
        if resp.status_code in (400, 422):
            raise ValidationError(resp.status_code, message, body)

        raise APIError(resp.status_code, message, body)
