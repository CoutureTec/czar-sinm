"""
SINMClient — cliente HTTP para a API SiNM (Sistema de Informações de Níveis de Manejo).

Fluxo principal:
  1. Autenticar (Keycloak) → token JWT
  2. Cadastrar talhão/gleba → retorna uuid + chaveClassificacaoNM
  3. Cadastrar análise de solo (vinculada à chave ou ao CPF)
  4. Cadastrar sensoriamento remoto (vinculado à chave ou ao CPF)
  5. Consultar resultado da classificação de nível de manejo
"""

from __future__ import annotations

import logging
import re
import warnings
from typing import Optional

import requests

from .auth import KeycloakAuth
from .exceptions import APIError, NotFoundError, PermissaoError, ValidationError
from .models import (
    AnaliseSolo,
    AnaliseSoloFisica,
    AnaliseSoloQuimica,
    DadoGleba,
    DadosInput,
    SensoriamentoRemoto,
)

logger = logging.getLogger(__name__)

# URLs padrão por ambiente
API_URLS = {
    "hml": "https://www.zarcnm-h.cnptia.embrapa.br",
    "prd": "https://www.zarcnm.cnptia.embrapa.br",
}

API_VERSIONS = ("v1", "v2")
"""Versões de contrato da API que o cliente sabe endereçar.

O ``v2`` cobre apenas análise de solo (por tipo) e sensoriamento remoto — gleba,
operação e classificação existem só no ``v1`` e continuam sendo chamadas lá.
"""

# Roles exigidos por sufixo de endpoint, já sem o prefixo /api/vN
# (ordem: mais específico primeiro)
_ENDPOINT_ROLES = [
    ("/glebas",                    ["OPERADOR_CONTRATOS"]),
    ("/operacoes",                 ["OPERADOR_CONTRATOS"]),
    ("/classificacoes",            ["OPERADOR_CONTRATOS",]),
    ("/analises-solo/disponiveis", ["OPERADOR_ANALISE_SOLO", "OPERADOR_CONTRATOS"]),
    ("/analises-solo",             ["OPERADOR_ANALISE_SOLO"]),
    ("/sensoriamentos-remotos",    ["OPERADOR_SENSORIAMENTO_REMOTO"]),
]

_PREFIXO_VERSAO = re.compile(r"^/api/v\d+")


def _roles_para_endpoint(path: str) -> list:
    """Roles exigidos pelo endpoint, independentemente da versão do contrato.

    A autorização é idêntica no v1 e no v2 (só o payload muda), então o prefixo
    ``/api/vN`` é descartado antes de casar o sufixo.
    """
    sufixo = _PREFIXO_VERSAO.sub("", path, count=1)
    for prefix, roles in _ENDPOINT_ROLES:
        if sufixo.startswith(prefix):
            return roles
    return []


def _extrair_lista(response) -> list:
    """Extrai a lista de items de uma resposta da API.

    Aceita dois formatos:
    - Lista simples: retorna diretamente.
    - Spring HATEOAS PagedModel: extrai o primeiro valor de ``_embedded``.

    Quando o PagedModel está vazio o Spring HATEOAS omite o ``_embedded``
    (sobram apenas ``_links``/``page``); nesse caso a lista correta é ``[]``,
    não o dict cru — daí a checagem explícita de resposta HATEOAS.
    """
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        embedded = response.get("_embedded")
        if isinstance(embedded, dict):
            return next(iter(embedded.values()), [])
        # PagedModel/HAL vazio não traz _embedded → lista vazia
        if "page" in response or "_links" in response:
            return []
    return response


class SINMClient:
    """
    Cliente para a API SiNM (Sistema de Informações de Níveis de Manejo) (SiNM).

    Exemplo de uso::

        from czarsinm import SINMClient

        client = SINMClient(
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
        keycloak_realm: Optional[str] = None,
        proxies: Optional[dict] = None,
        timeout: int = 60,
        grant_type: Optional[str] = None,
        api_version: str = "v1",
    ):
        """
        Parameters
        ----------
        username:
            Login do usuário no Keycloak/SiNM.
        password:
            Senha do usuário.
        client_id:
            Client ID fornecido pela equipe SiNM.
        client_secret:
            Client secret fornecido pela equipe SiNM.
        ambiente:
            'hml', 'prd' ou qualquer string para ambiente customizado.
            Em ambientes customizados, 'base_url' e 'keycloak_url' tornam-se
            obrigatórios.
        base_url:
            URL base da API ZarcNM
            (ex: 'https://meu-zarcnm.exemplo.com').
            Obrigatório para ambientes customizados; se None, usa o padrão do ambiente.
        keycloak_url:
            URL base do Keycloak incluindo o segmento /realms
            (ex: 'https://meu-keycloak.exemplo.com/realms').
            Obrigatório para ambientes customizados; se None, usa a URL padrão da Embrapa.
        keycloak_realm:
            Nome do realm no Keycloak.
            Obrigatório para ambientes customizados; se None, usa o mapeamento
            padrão (hml → zarcnm-h, prd → zarcnm).
        proxies:
            Proxies para requests. Ex: {'https': 'http://proxy.cnptia.embrapa.br:3128'}
        timeout:
            Timeout em segundos para chamadas à API.
        api_version:
            Contrato da API para análise de solo e sensoriamento remoto: 'v1'
            (padrão, contrato congelado — aceita os nomes legados) ou 'v2'
            (contrato limpo: só nomes canônicos e ``cnpjLaboratorio``
            obrigatório). O v2 estreia em homologação em 04/08/2026; em produção,
            na entrega seguinte. Gleba, operação e classificação não têm v2 e são
            sempre chamadas no /api/v1.
        """
        if ambiente not in API_URLS and base_url is None:
            raise ValueError(
                f"Ambiente '{ambiente}' não reconhecido. "
                "Para ambientes customizados, informe 'base_url' "
                "(ou defina SINM_BACKEND_URL no arquivo .env)."
            )
        if api_version not in API_VERSIONS:
            raise ValueError(
                f"api_version '{api_version}' não reconhecida. "
                f"Use uma de: {', '.join(API_VERSIONS)}."
            )
        self._auth = KeycloakAuth(
            client_id=client_id,
            client_secret=client_secret,
            ambiente=ambiente,
            keycloak_url=keycloak_url,
            keycloak_realm=keycloak_realm,
            proxies=proxies,
            username=username,
            password=password,
            grant_type=grant_type,
        )
        self._base_url = (base_url or API_URLS.get(ambiente, API_URLS["hml"])).rstrip("/")
        self._proxies = proxies
        self._timeout = timeout
        self._api_version = api_version
        self._session = requests.Session()

    @property
    def api_version(self) -> str:
        """Contrato usado nas rotas de análise de solo e sensoriamento ('v1' ou 'v2')."""
        return self._api_version

    def _rota(self, recurso: str) -> str:
        """Path do recurso na versão configurada. Ex.: '/analises-solo' → '/api/v2/analises-solo'."""
        return f"/api/{self._api_version}{recurso}"

    @property
    def roles(self) -> list:
        """Realm roles do usuário autenticado extraídos do token JWT."""
        return self._auth.roles

    @property
    def client_roles(self) -> dict:
        """Client roles do usuário autenticado agrupados por client ID.

        Formato: {client_id: [role1, role2, ...]}
        """
        return self._auth.client_roles

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
        return _extrair_lista(self._get("/api/v1/glebas"))

    # ------------------------------------------------------------------
    # Análise de Solo
    # ------------------------------------------------------------------

    def cadastrar_analise_solo(
        self,
        analise: AnaliseSolo,
        chave_classificacao_nm: Optional[str] = None,
    ) -> dict:
        """
        Cadastra uma análise de solo pelo payload **combinado** (química + física).

        Fachada legada do ``/api/v1``: cria as duas metades — química e física —
        numa única transação. Mantida sem prazo de remoção, mas não existe no v2:
        com ``api_version='v2'`` use :meth:`cadastrar_analise_solo_quimica` e
        :meth:`cadastrar_analise_solo_fisica` (ou ``AnaliseSolo.separar()``).

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
            Resumo das duas metades cadastradas (``{'quimica': ..., 'fisica': ...}``).
        """
        if self._api_version != "v1":
            raise ValueError(
                "O cadastro combinado existe apenas no /api/v1. Com api_version='v2' "
                "use cadastrar_analise_solo_quimica/cadastrar_analise_solo_fisica."
            )
        path = "/api/v1/analises-solo"
        if chave_classificacao_nm:
            path = f"{path}/{chave_classificacao_nm}"
        return self._post(path, analise.to_dict("v1"))

    def buscar_analise_solo(self, uuid_analise: str) -> dict:
        """DEPRECIADO — use :meth:`buscar_analise_solo_quimica` ou
        :meth:`buscar_analise_solo_fisica`.

        A consulta de análise de solo é **por tipo**: não existe (nem existia)
        ``GET /analises-solo/{uuid}``. Este método delega para a metade química,
        que é o registro primário criado pelo cadastro combinado.
        """
        warnings.warn(
            "buscar_analise_solo está depreciado: a consulta é por tipo. Use "
            "buscar_analise_solo_quimica ou buscar_analise_solo_fisica.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.buscar_analise_solo_quimica(uuid_analise)

    def listar_analises_solo(self) -> list:
        """Lista as análises de solo (metade química) do usuário autenticado.

        No ``/api/v1`` a rota combinada continua respondendo por compatibilidade;
        prefira :meth:`listar_analises_solo_quimicas` / :meth:`listar_analises_solo_fisicas`.
        """
        if self._api_version != "v1":
            return self.listar_analises_solo_quimicas()
        return _extrair_lista(self._get("/api/v1/analises-solo"))

    # -- Análise de solo por tipo (química / física) --------------------

    def cadastrar_analise_solo_quimica(
        self,
        analise: AnaliseSoloQuimica,
        chave_classificacao_nm: Optional[str] = None,
    ) -> dict:
        """Cadastra uma análise de solo **química**.

        Sem ``chave_classificacao_nm`` o vínculo é feito pelo CPF do produtor no
        payload. No contrato v2 o ``cnpjLaboratorio`` é obrigatório — o modelo
        levanta ``ValueError`` antes da chamada, em vez de deixar a API responder 400.
        """
        path = self._rota("/analises-solo/quimica")
        if chave_classificacao_nm:
            path = f"{path}/{chave_classificacao_nm}"
        return self._post(path, analise.to_dict(self._api_version))

    def atualizar_analise_solo_quimica(self, uuid_analise: str, analise: AnaliseSoloQuimica) -> dict:
        """Substitui os dados de uma análise de solo química já cadastrada."""
        return self._put(
            f"{self._rota('/analises-solo/quimica')}/{uuid_analise}",
            analise.to_dict(self._api_version),
        )

    def buscar_analise_solo_quimica(self, uuid_analise: str) -> dict:
        """Busca uma análise de solo química pelo UUID.

        Quem cadastrou a análise recebe a visão completa; quem apenas opera a
        classificação recebe a visão parcial (sem amostras nem laboratório). O uuid
        de uma análise física neste endpoint responde 404.
        """
        return self._get(f"{self._rota('/analises-solo/quimica')}/{uuid_analise}")

    def listar_analises_solo_quimicas(self) -> list:
        """Lista as análises de solo químicas do usuário autenticado."""
        return _extrair_lista(self._get(self._rota("/analises-solo/quimica")))

    def cadastrar_analise_solo_fisica(
        self,
        analise: AnaliseSoloFisica,
        chave_classificacao_nm: Optional[str] = None,
    ) -> dict:
        """Cadastra uma análise de solo **física**.

        Sem ``chave_classificacao_nm`` o vínculo é feito pelo CPF do produtor no
        payload. No contrato v2 o ``cnpjLaboratorio`` é obrigatório.
        """
        path = self._rota("/analises-solo/fisica")
        if chave_classificacao_nm:
            path = f"{path}/{chave_classificacao_nm}"
        return self._post(path, analise.to_dict(self._api_version))

    def atualizar_analise_solo_fisica(self, uuid_analise: str, analise: AnaliseSoloFisica) -> dict:
        """Substitui os dados de uma análise de solo física já cadastrada."""
        return self._put(
            f"{self._rota('/analises-solo/fisica')}/{uuid_analise}",
            analise.to_dict(self._api_version),
        )

    def buscar_analise_solo_fisica(self, uuid_analise: str) -> dict:
        """Busca uma análise de solo física pelo UUID.

        Mesmas regras da química: visão completa para quem cadastrou, parcial para
        quem só opera a classificação. O uuid de uma análise química aqui responde 404.
        """
        return self._get(f"{self._rota('/analises-solo/fisica')}/{uuid_analise}")

    def listar_analises_solo_fisicas(self) -> list:
        """Lista as análises de solo físicas do usuário autenticado."""
        return _extrair_lista(self._get(self._rota("/analises-solo/fisica")))

    # -- Disponibilidade por CPF do produtor ----------------------------

    def consultar_analises_disponiveis(
        self,
        cpf: str,
        data_referencia: Optional[str] = None,
    ) -> dict:
        """
        Diz **quais análises de solo o produtor já tem e até quando valem**, sem
        expor o conteúdo.

        Responde duas listas independentes — ``analisesQuimicas`` e
        ``analisesFisicas`` —, cada item com ``uuidAnaliseSolo``, ``validaAte``,
        ``valida`` e ``motivoInvalidade`` (``RN15`` quando expirada). Ordenadas da
        validade mais distante para a mais próxima; as expiradas também vêm, com
        ``valida=false``.

        Com o ``uuidAnaliseSolo`` em mãos, consulte a análise em
        :meth:`buscar_analise_solo_quimica` ou :meth:`buscar_analise_solo_fisica`,
        **conforme a lista de onde o item veio** — o uuid de uma no endpoint da outra
        responde 404. O uuid identifica, não autoriza: consultar a análise segue
        exigindo ``OPERADOR_ANALISE_SOLO`` na operadora da classificação.

        Só existe no ``/api/v1``: é chamada nessa rota mesmo com ``api_version='v2'``.

        Parameters
        ----------
        cpf:
            CPF do produtor (somente dígitos). A consulta não é restrita à sua
            carteira de clientes.
        data_referencia:
            Data ('YYYY-MM-DD') usada para decidir a validade. Default: hoje.

        Returns
        -------
        dict
            ``{'analisesQuimicas': [...], 'analisesFisicas': [...]}``
        """
        params = {"cpf": cpf}
        if data_referencia:
            params["dataReferencia"] = data_referencia
        return self._get("/api/v1/analises-solo/disponiveis", params=params)

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
            f"{self._rota('/sensoriamentos-remotos')}/{chave_classificacao_nm}",
            sensoriamento.to_dict(self._api_version),
        )

    def atualizar_sensoriamento_remoto(
        self,
        uuid_sensoriamento: str,
        sensoriamento: SensoriamentoRemoto,
    ) -> dict:
        """Substitui os dados de um sensoriamento remoto já cadastrado."""
        return self._put(
            f"{self._rota('/sensoriamentos-remotos')}/{uuid_sensoriamento}",
            sensoriamento.to_dict(self._api_version),
        )

    def buscar_sensoriamento_remoto(self, uuid_sensoriamento: str) -> dict:
        """Busca um sensoriamento remoto pelo UUID."""
        return self._get(f"{self._rota('/sensoriamentos-remotos')}/{uuid_sensoriamento}")

    def listar_sensoriamentos_remotos(self) -> list:
        """Lista os sensoriamentos do usuário autenticado."""
        return _extrair_lista(self._get(self._rota("/sensoriamentos-remotos")))

    def remover_sensoriamento_remoto(self, uuid_sensoriamento: str) -> dict:
        """Remove um sensoriamento remoto pelo UUID (204 → dict vazio)."""
        return self._delete(f"{self._rota('/sensoriamentos-remotos')}/{uuid_sensoriamento}")

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

    def consultar_racional(self, chave_classificacao_nm: str) -> dict:
        """
        Consulta o racional do cálculo do nível de manejo: *por que* a gleba
        recebeu aquele NM (indicadores, fatores restritivos e narrativa).

        Disponível apenas para a classificação COMPLETA — uma classificação
        preliminar ou ainda em processamento responde 404 (NotFoundError).

        A projeção depende dos papéis do usuário autenticado: com
        OPERADOR_ANALISE_SOLO na empresa operadora, vêm valores/faixas/scores
        parciais (projeção completa); sem ele, só os campos de causa e o efeito na
        nota (projeção compacta).

        Leitura causal (v6.2026)
        ------------------------
        A nota nem sempre vem da média: regras de teto podem fixá-la. Quatro campos
        dizem *qual* fator limitou:

        - ``regraDeterminante`` (na classificação) — regra que fixou a nota:
          ``DOIS_OU_MAIS_NM1``, ``DOIS_OU_MAIS_NM2``, ``UM_NM1_UM_NM2``,
          ``SATURACAO_ALUMINIO_CRITICA``, ``SATURACAO_ALUMINIO_ALTA``,
          ``SOJA_EM_SUCESSAO``, ``LEGUMINOSAS_EM_SUCESSAO``,
          ``DECLIVIDADE_ACENTUADA``, ``TETO_AMBIENTAL``, ou ``BANDA_DA_MEDIA``
          quando a nota veio mesmo da média.
        - ``limitantesPrincipais`` (na classificação) — nomes dos indicadores que
          foram o gatilho da regra. Vazio quando não há limitante (ex.: NM4).
        - ``papelNaNota`` (por indicador) — ``LIMITANTE_PRINCIPAL``, ``LIMITANTE``,
          ``FAVORAVEL`` ou ``ALINHADO``. Vem nas duas projeções.
        - ``contribuicao`` (por indicador) — ``ACIMA``, ``NA_MEDIA`` ou ``ABAIXO``
          em relação ao score médio. Só na projeção completa.

        ``efeitoNaNota`` (``ELEVOU``/``REBAIXOU``/``NEUTRO``) continua na resposta
        com o mesmo comportamento, porém **depreciado**: ele compara o indicador com
        a nota *final*, então quando a nota é travada por um teto os indicadores que
        a causaram saem como ``NEUTRO``. Prefira ``papelNaNota`` + ``contribuicao``.

        Parameters
        ----------
        chave_classificacao_nm:
            Chave obtida no cadastro do talhão/gleba.

        Returns
        -------
        dict
            Racional do cálculo (RacionalCalculoModel).

        Raises
        ------
        NotFoundError
            Se não houver classificação completa para a chave.
        """
        return self._get(f"/api/v1/classificacoes/{chave_classificacao_nm}/racional")

    def listar_classificacoes(self) -> list:
        """Lista todas as classificações do usuário autenticado."""
        return _extrair_lista(self._get("/api/v1/classificacoes"))

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

    def _put(self, path: str, payload: dict) -> dict:
        url = self._base_url + path
        logger.debug("PUT %s", url)
        try:
            resp = self._session.put(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self._timeout,
                proxies=self._proxies,
            )
        except requests.RequestException as exc:
            raise APIError(0, f"Erro de conexão: {exc}") from exc

        return self._handle_response(resp, path)

    def _delete(self, path: str) -> dict:
        url = self._base_url + path
        logger.debug("DELETE %s", url)
        try:
            resp = self._session.delete(
                url,
                headers=self._headers(),
                timeout=self._timeout,
                proxies=self._proxies,
            )
        except requests.RequestException as exc:
            raise APIError(0, f"Erro de conexão: {exc}") from exc

        return self._handle_response(resp, path)

    def _get(self, path: str, params: Optional[dict] = None):
        url = self._base_url + path
        logger.debug("GET %s params=%s", url, params)
        try:
            resp = self._session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self._timeout,
                proxies=self._proxies,
            )
        except requests.RequestException as exc:
            raise APIError(0, f"Erro de conexão: {exc}") from exc

        return self._handle_response(resp, path)

    def _handle_response(self, resp: requests.Response, path: str = ""):
        logger.debug("Response [%s] %s: %s", resp.status_code, path, resp.text)

        if resp.status_code in (200, 201, 204):
            if not resp.content:
                return {}
            return resp.json()

        try:
            parsed = resp.json()
            body = parsed if isinstance(parsed, dict) else {}
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
