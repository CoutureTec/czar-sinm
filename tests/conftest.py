"""Fixtures compartilhadas entre todos os testes."""

import base64
import json
from unittest.mock import MagicMock

import pytest

from czarsinm import (
    SINMClient,
    Amostra,
    AnaliseSolo,
    CoberturaSolo,
    Cultura,
    DadoGleba,
    Indice,
    InterpretacaoCoberturaSolo,
    InterpretacaoCultura,
    InterpretacaoManejo,
    Manejo,
    Operacao,
    Producao,
    Propriedade,
    Produtor,
    SensoriamentoRemoto,
    Talhao,
    TipoOperacao,
)
from czarsinm.auth import KeycloakAuth

BASE_URL_HML = "https://www.zarcnm-h.cnptia.embrapa.br/zarcnm"


def make_jwt(roles: list, client_id: str = "client-id") -> str:
    """Constrói um JWT fake com os roles como client roles (sem assinatura real)."""
    payload = {"resource_access": {client_id: {"roles": roles}}}
    b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJSUzI1NiJ9.{b64}.assinatura_fake"


@pytest.fixture
def fake_token():
    return make_jwt(["OPERADOR_CONTRATOS", "BETA_USER"])


@pytest.fixture
def client(fake_token):
    """SINMClient com autenticação mockada (sem chamadas reais ao Keycloak)."""
    c = SINMClient(
        username="usuario@test.br",
        password="senha",
        client_id="client-id",
        client_secret="client-secret",
        ambiente="hml",
    )
    auth_mock = MagicMock(spec=KeycloakAuth)
    auth_mock.auth_header = {"Authorization": f"Bearer {fake_token}"}
    auth_mock.roles = ["OPERADOR_CONTRATOS", "BETA_USER"]
    auth_mock.client_roles = {"client-id": ["OPERADOR_CONTRATOS", "BETA_USER"]}
    c._auth = auth_mock
    return c


# ---------------------------------------------------------------------------
# Factories de modelos de exemplo
# ---------------------------------------------------------------------------

@pytest.fixture
def produtor():
    return Produtor(nome="Produtor Teste", cpf="68122528082")


@pytest.fixture
def propriedade():
    return Propriedade(
        nome="Fazenda Teste",
        cnpj="54194116000138",
        codigoCar="MT-5107248-1025F299474640148FE845C7A0B62635",
        codigoIbge="3509502",
        poligono="POLYGON ((-58.91 -13.50,-58.86 -13.51,-58.91 -13.50))",
    )


@pytest.fixture
def talhao():
    return Talhao(
        poligono="POLYGON ((-47.11 -22.80,-47.10 -22.81,-47.11 -22.80))",
        area=32.0,
        tipoProdutor="Proprietário",
        plantioContorno=1,
    )


@pytest.fixture
def manejo():
    return Manejo(
        data="2022-09-01",
        operacao=Operacao(nomeOperacao="Revolvimento do solo"),
        tipoOperacao=TipoOperacao(tipo="ARAÇÃO"),
    )


@pytest.fixture
def producao_passada():
    return Producao(
        cultura=Cultura(codigo="001"),
        ilp=False,
        dataPlantio="2022-10-01",
        dataColheita="2023-01-10",
    )


@pytest.fixture
def producao_futura():
    return Producao(
        cultura=Cultura(codigo="001"),
        dataPrevisaoPlantio="2026-10-01",
        dataPrevisaoColheita="2027-01-10",
    )


@pytest.fixture
def dado_gleba(produtor, propriedade, talhao, manejo, producao_passada, producao_futura):
    return DadoGleba(
        produtor=produtor,
        propriedade=propriedade,
        talhao=talhao,
        manejos=[manejo],
        coberturas=[CoberturaSolo(dataAvaliacao="2023-01-01", porcentualPalhada=50)],
        producoes=[producao_passada, producao_futura],
    )


@pytest.fixture
def amostra():
    return Amostra(
        cpfResponsavelColeta="21750077078",
        dataColeta="2024-09-17",
        pontoColeta="POINT (-47.108493 -22.811532)",
        camada="20",
        areia=78.0, silte=5.0, argila=17.0,
        calcio=0.9, magnesio=0.8, potassio=59.9, sodio=5.6,
        aluminio=0.36, acidezPotencial=5.0, phh2o=5.4,
        fosforoMehlich=1.1, enxofre=6.4, mos=10.8,
    )


@pytest.fixture
def analise_solo(amostra):
    return AnaliseSolo(
        cpfProdutor="68122528082",
        cnpj="54194116000138",
        amostras=[amostra],
    )


@pytest.fixture
def sensoriamento_remoto():
    return SensoriamentoRemoto(
        cpfProdutor="68122528082",
        cnpj="54194116000138",
        dataInicial="2021-01-17",
        dataFinal="2024-05-14",
        declividadeMedia=60,
        plantioContorno=1,
        terraceamento=1,
        codigoSateliteDeclividadeMedia="S09",
        codigoSatelitePlantioContorno="S08",
        codigoSateliteTerraceamento="S07",
        indices=[
            Indice(
                codigoSatelite="S01",
                coordenada="POINT (-47.108493 -22.811532)",
                data="2021-01-17",
                ndvi=0.5363,
                ndti=0.3363,
            )
        ],
        interpretacoesCoberturaSolo=[
            InterpretacaoCoberturaSolo(dataAvaliacao="2022-01-01", porcentualPalhada=50)
        ],
        interpretacoesCultura=[
            InterpretacaoCultura(
                tipoCultivo="Cultivo de 2ª safra",
                dataInicio="2023-10-01",
                dataFim="2024-02-01",
            )
        ],
        interpretacoesManejo=[
            InterpretacaoManejo(data="2021-01-28", operacao="Revolvimento do solo")
        ],
    )
