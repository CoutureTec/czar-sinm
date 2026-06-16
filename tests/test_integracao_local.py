"""
Testes de integração contra a API zarc-nm local.

Requer:
  - API rodando localmente (via docker-compose em zarc-nm/docker/)
  - Arquivo .env.local na raiz do projeto czar-sinm com as credenciais
  - Variáveis de ambiente definidas (ou arquivo .env.local)

Para rodar:
    PYTHONPATH=src pytest tests/test_integracao_local.py -v

Todos os testes são skipped automaticamente se SINM_BACKEND_URL não estiver
definido no ambiente ou no arquivo .env.local.
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env.local da raiz do projeto (não o .env padrão)
_env_local = Path(__file__).parent.parent / ".env.local"
if _env_local.exists():
    load_dotenv(_env_local, override=False)

_BACKEND_URL = os.getenv("SINM_BACKEND_URL")
_SKIP_REASON = (
    "SINM_BACKEND_URL não definido — "
    "copie .env.local.example para .env.local e configure a API local"
)

pytestmark = pytest.mark.skipif(not _BACKEND_URL, reason=_SKIP_REASON)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from czarsinm import SINMClient

    return SINMClient(
        username=os.environ["SINM_USERNAME"],
        password=os.environ["SINM_PASSWORD"],
        client_id=os.environ["SINM_CLIENT_ID"],
        client_secret=os.environ["SINM_CLIENT_SECRET"],
        ambiente=os.getenv("SINM_AMBIENTE", "local"),
        base_url=os.environ["SINM_BACKEND_URL"],
        keycloak_url=os.getenv("SINM_KEYCLOAK"),
        keycloak_realm=os.getenv("SINM_KEYCLOAK_REALM"),
        grant_type=os.getenv("SINM_GRANT_TYPE") or None,
    )


@pytest.fixture(scope="module")
def dado_gleba_minimal():
    from czarsinm import (
        CoberturaSolo, Cultura, DadoGleba, Manejo, Operacao,
        Producao, Propriedade, Produtor, Talhao, TipoOperacao,
    )
    return DadoGleba(
        produtor=Produtor(cpf="68122528082", nome="Produtor Integração"),
        propriedade=Propriedade(
            nome="Fazenda Integração",
            codigoCar="MT-5107248-1025F299474640148FE845C7A0B62635",
            codigoIbge="3509502",
            poligono="POLYGON ((-58.91 -13.50,-58.86 -13.51,-58.91 -13.50))",
        ),
        talhao=Talhao(
            poligono="POLYGON ((-47.11 -22.80,-47.10 -22.81,-47.11 -22.80))",
            area=32.0,
            tipoProdutor="Proprietário",
            plantioContorno=1,
        ),
        manejos=[
            Manejo(
                data="2022-09-01",
                operacao=Operacao(nomeOperacao="Revolvimento do solo"),
                tipoOperacao=TipoOperacao(tipo="ARAÇÃO"),
            )
        ],
        coberturas=[CoberturaSolo(dataAvaliacao="2023-01-01", porcentualPalhada=50)],
        producoes=[
            Producao(
                cultura=Cultura(codigo="001"),
                ilp=False,
                dataPlantio="2022-10-01",
                dataColheita="2023-01-10",
            ),
            Producao(
                cultura=Cultura(codigo="001"),
                dataPrevisaoPlantio="2026-10-01",
                dataPrevisaoColheita="2027-01-10",
            ),
        ],
    )


@pytest.fixture(scope="module")
def analise_solo_minimal():
    from czarsinm import AmostraQuimica, AnaliseSolo
    return AnaliseSolo(
        cpfProdutor="68122528082",
        amostrasQuimicas=[
            AmostraQuimica(
                cpfResponsavelColeta="21750077078",
                dataColeta="2024-09-17",
                longitude=-47.108493,
                latitude=-22.811532,
                camada="00_020",
                calcio=0.9,
                magnesio=0.8,
                potassio=59.9,
                aluminio=0.36,
                acidezPotencial=5.0,
                enxofre=6.4,
                mos=10.8,
            )
        ],
    )


@pytest.fixture(scope="module")
def sensoriamento_minimal():
    from czarsinm import Indice, SensoriamentoRemoto
    return SensoriamentoRemoto(
        cpfProdutor="68122528082",
        dataInicial="2021-01-17",
        dataFinal="2024-05-14",
        declividadeMedia=60,
        plantioContorno=1,
        terraceamento=1,
        codigoSateliteDeclividadeMedia="S09",
        indices=[
            Indice(
                codigoSatelite="S01",
                longitude=-47.108493,
                latitude=-22.811532,
                data="2021-01-17",
                ndvi=0.5363,
                ndti=0.3363,
            )
        ],
    )


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestAutenticacao:
    def test_token_obtido(self, client):
        token = client._auth.token
        assert token and len(token) > 10

    def test_client_roles_presentes(self, client):
        roles = client.client_roles
        assert isinstance(roles, dict)


class TestGlebas:
    def test_listar_retorna_lista(self, client):
        result = client.listar_glebas()
        assert isinstance(result, list)

    def test_cadastrar_e_buscar(self, client, dado_gleba_minimal):
        gleba = client.cadastrar_gleba(dado_gleba_minimal)
        assert "chaveClassificacaoNM" in gleba
        assert "uuid" in gleba or "uuidGleba" in gleba

        uuid = gleba.get("uuid") or gleba.get("uuidGleba")
        detalhes = client.buscar_gleba(str(uuid))
        assert detalhes is not None


class TestAnaliseSolo:
    def test_listar_retorna_lista(self, client):
        result = client.listar_analises_solo()
        assert isinstance(result, list)

    def test_cadastrar_com_chave(self, client, dado_gleba_minimal, analise_solo_minimal):
        gleba = client.cadastrar_gleba(dado_gleba_minimal)
        chave = gleba["chaveClassificacaoNM"]

        analise = client.cadastrar_analise_solo(analise_solo_minimal, chave_classificacao_nm=chave)
        assert analise is not None


class TestSensoriamentoRemoto:
    def test_listar_retorna_lista(self, client):
        result = client.listar_sensoriamentos_remotos()
        assert isinstance(result, list)

    def test_cadastrar_com_chave(self, client, dado_gleba_minimal, sensoriamento_minimal):
        gleba = client.cadastrar_gleba(dado_gleba_minimal)
        chave = gleba["chaveClassificacaoNM"]

        sr = client.cadastrar_sensoriamento_remoto(sensoriamento_minimal, chave_classificacao_nm=chave)
        assert sr is not None


class TestClassificacao:
    def test_listar_retorna_lista(self, client):
        result = client.listar_classificacoes()
        assert isinstance(result, list)
