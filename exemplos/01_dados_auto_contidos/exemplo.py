"""
Exemplo de uso da biblioteca czarsinm.

Uso:
    python example.py                                          # fluxo completo
    python example.py --acao autenticacao
    python example.py --acao listarGlebas
    python example.py --acao listarSensoriamentos
    python example.py --acao cadastraGleba
    python example.py --acao cadastraAnaliseSolo   --chave_nm CHAVE
    python example.py --acao cadastraSensoriamentoRemoto --chave_nm CHAVE
    python example.py --acao consultaClassificacaoNM  --chave_nm CHAVE

Credenciais via arquivo .env (cp .env.example .env).
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from czarsinm import (
    SINMClient,
    DadoGleba, Produtor, Propriedade, Talhao,
    Manejo, Operacao, TipoOperacao, CoberturaSolo, Producao, Cultura,
    AnaliseSolo, Amostra, AmostraFisica,
    SensoriamentoRemoto, Indice,
    InterpretacaoCoberturaSolo, InterpretacaoCultura, InterpretacaoManejo,
    DadosInput,
)
from czarsinm.exceptions import SINMError, NotFoundError, APIError, PermissaoError

ACOES = (
    "autenticacao",
    "listarGlebas",
    "listarSensoriamentos",
    "cadastraGleba",
    "cadastraAnaliseSolo",
    "cadastraSensoriamentoRemoto",
    "consultaClassificacaoNM",
)

# --------------------------------------------------------------------------
# Argumentos de linha de comando
# --------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Exemplo de integração com a API SiNM.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--acao",
    choices=ACOES,
    default=None,
    help=(
        "Ação a executar. Se omitido, executa o fluxo completo.\n"
        "  autenticacao\n"
        "  listarGlebas\n"
        "  listarSensoriamentos\n"
        "  cadastraGleba\n"
        "  cadastraAnaliseSolo          (requer --chave_nm)\n"
        "  cadastraSensoriamentoRemoto  (requer --chave_nm)\n"
        "  consultaClassificacaoNM      (requer --chave_nm)\n"
    ),
)
parser.add_argument(
    "--chave_nm",
    default=None,
    metavar="CHAVE",
    help="Chave de classificação NM retornada no cadastro da gleba.",
)
args = parser.parse_args()

ACAO = args.acao
CHAVE_NM = args.chave_nm

# Valida dependências
if ACAO in ("cadastraAnaliseSolo", "cadastraSensoriamentoRemoto", "consultaClassificacaoNM"):
    if not CHAVE_NM:
        parser.error(f"--chave_nm é obrigatório para a ação '{ACAO}'.")

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
_log_level = logging.DEBUG if os.getenv("DEBUG", "").lower() == "true" else logging.INFO
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# --------------------------------------------------------------------------
# Credenciais (.env)
# --------------------------------------------------------------------------
USUARIO        = os.environ["SINM_USERNAME"]
SENHA          = os.environ["SINM_PASSWORD"]
CLIENT_ID      = os.environ["SINM_CLIENT_ID"]
CLIENT_SECRET  = os.environ["SINM_CLIENT_SECRET"]
AMBIENTE       = os.getenv("SINM_AMBIENTE", "hml")
BACKEND_URL    = os.getenv("SINM_BACKEND_URL")
KEYCLOAK_URL   = os.getenv("SINM_KEYCLOAK")
KEYCLOAK_REALM = os.getenv("SINM_KEYCLOAK_REALM")

# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------
client = SINMClient(
    username=USUARIO,
    password=SENHA,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    ambiente=AMBIENTE,
    base_url=BACKEND_URL,
    keycloak_url=KEYCLOAK_URL,
    keycloak_realm=KEYCLOAK_REALM,
)

# --------------------------------------------------------------------------
# Payloads de exemplo (reutilizados pelas funções abaixo)
# --------------------------------------------------------------------------

def _dado_gleba() -> DadoGleba:
    return DadoGleba(
        produtor=Produtor(nome="Produtor Exemplo", cpf="68122528082"),
        propriedade=Propriedade(
            nome="Fazenda Exemplo",
            cnpj="54194116000138",
            codigoCar="MT-5107248-1025F299474640148FE845C7A0B62635",
            codigoIbge="3509502",
            poligono=(
                "POLYGON (("
                "-58.9144585643381 -13.5072128852218,"
                "-58.8657268985861 -13.5134933385645,"
                "-58.8657268985861 -13.5139585573307,"
                "-58.8666573361184 -13.5153542136291,"
                "-58.9144585643381 -13.5072128852218"
                "))"
            ),
        ),
        talhao=Talhao(
            poligono=(
                "POLYGON (("
                "-47.112207 -22.809752,"
                "-47.104869 -22.809969,"
                "-47.102916 -22.809000,"
                "-47.101350 -22.809633,"
                "-47.100041 -22.811749,"
                "-47.106500 -22.813253,"
                "-47.112358 -22.809910,"
                "-47.112207 -22.809752"
                "))"
            ),
            area=32.0,
            tipoProdutor="Proprietário",
            plantioContorno=1,
            cnpjOperador=CLIENT_ID,
        ),
        manejos=[
            Manejo(
                data="2022-09-01",
                operacao=Operacao(nomeOperacao="Revolvimento do solo"),
                tipoOperacao=TipoOperacao(tipo="ARAÇÃO"),
            ),
        ],
        coberturas=[
            CoberturaSolo(dataAvaliacao="2023-01-01", porcentualPalhada=50),
            CoberturaSolo(dataAvaliacao="2024-01-01", porcentualPalhada=55),
            CoberturaSolo(dataAvaliacao="2025-01-01", porcentualPalhada=60),
        ],
        producoes=[
            Producao(cultura=Cultura(codigo="001"), ilp=False,
                     dataPlantio="2022-10-01", dataColheita="2023-01-10"),
            Producao(cultura=Cultura(codigo="018"), ilp=False,
                     dataPlantio="2023-02-21", dataColheita="2023-08-01"),
            Producao(cultura=Cultura(codigo="001"), ilp=False,
                     dataPlantio="2024-10-01", dataColheita="2025-01-10"),
            # Safra futura (obrigatória)
            Producao(cultura=Cultura(codigo="001"),
                     dataPrevisaoPlantio="2026-10-01",
                     dataPrevisaoColheita="2027-01-10"),
        ],
    )


def _analise_solo() -> AnaliseSolo:
    return AnaliseSolo(
        cpfProdutor="68122528082",
        cnpj="54194116000138",
        amostrasQuimicas=[
            Amostra(
                cpfResponsavelColeta="21750077078", dataColeta="2024-09-17",
                longitude=-47.108493, latitude=-22.811532, camada="00_020",
                calcio=0.9, magnesio=0.8, potassio=59.9, sodio=5.6,
                aluminio=0.36, acidezPotencial=5.0,
                phh2o=5.4, fosforoMehlich=1.1, enxofre=6.4, mos=10.8,
            ),
            Amostra(
                cpfResponsavelColeta="21750077078", dataColeta="2024-09-17",
                longitude=-47.106733, latitude=-22.812530, camada="00_020",
                calcio=0.8, magnesio=0.7, potassio=59.2, sodio=5.9,
                aluminio=0.36, acidezPotencial=4.4,
                phh2o=5.5, fosforoMehlich=1.2, enxofre=7.3, mos=12.6,
            ),
            Amostra(
                cpfResponsavelColeta="21750077078", dataColeta="2024-09-17",
                longitude=-47.103408, latitude=-22.812253, camada="20_040",
                calcio=0.5, magnesio=1.1, potassio=42.9, sodio=7.9,
                aluminio=1.215, acidezPotencial=5.2,
                phh2o=5.2, fosforoMehlich=0.8, enxofre=6.4, mos=7.2,
            ),
            Amostra(
                cpfResponsavelColeta="21750077078", dataColeta="2024-09-18",
                longitude=-47.103418, latitude=-22.812263, camada="20_040",
                calcio=0.5, magnesio=1.2, potassio=42.9, sodio=7.9,
                aluminio=1.215, acidezPotencial=5.2,
                phh2o=5.2, fosforoMehlich=0.8, enxofre=6.4, mos=7.2,
            ),
        ],
        amostrasFisicas=[
            AmostraFisica(
                cpfResponsavelColeta="21750077078", dataColeta="2024-09-17",
                longitude=-47.108493, latitude=-22.811532, camada="00_020",
                areia=78.0, silte=5.0, argila=17.0,
            ),
            AmostraFisica(
                cpfResponsavelColeta="21750077078", dataColeta="2024-09-17",
                longitude=-47.106733, latitude=-22.812530, camada="00_020",
                areia=75.0, silte=6.0, argila=19.0,
            ),
            AmostraFisica(
                cpfResponsavelColeta="21750077078", dataColeta="2024-09-17",
                longitude=-47.103408, latitude=-22.812253, camada="20_040",
                areia=71.0, silte=7.0, argila=22.0,
            ),
            AmostraFisica(
                cpfResponsavelColeta="21750077078", dataColeta="2024-09-17",
                longitude=-47.103418, latitude=-22.811531, camada="20_040",
                areia=71.0, silte=8.0, argila=22.0,
            ),
        ],
    )


def _sensoriamento_remoto() -> SensoriamentoRemoto:
    indices = [
        Indice(codigoSatelite="S01", coordenada="POINT (-47.108493 -22.811532)",
               data="2021-01-17", ndvi=0.5363, ndti=0.3363),
        Indice(codigoSatelite="S01", coordenada="POINT (-47.108493 -22.811532)",
               data="2021-04-07", ndvi=0.8810, ndti=0.6810),
        Indice(codigoSatelite="S01", coordenada="POINT (-47.108493 -22.811532)",
               data="2022-04-07", ndvi=0.9119, ndti=0.7119),
        Indice(codigoSatelite="S01", coordenada="POINT (-47.108493 -22.811532)",
               data="2022-09-01", ndvi=0.3342, ndti=0.1342),
        Indice(codigoSatelite="S01", coordenada="POINT (-47.108493 -22.811532)",
               data="2023-03-30", ndvi=0.9151, ndti=0.7151),
        Indice(codigoSatelite="S01", coordenada="POINT (-47.108493 -22.811532)",
               data="2023-09-22", ndvi=0.3370, ndti=0.1370),
        Indice(codigoSatelite="S01", coordenada="POINT (-47.108493 -22.811532)",
               data="2024-03-29", ndvi=0.9355, ndti=0.7355),
        Indice(codigoSatelite="S01", coordenada="POINT (-47.108493 -22.811532)",
               data="2024-05-08", ndvi=0.9153, ndti=0.7153),
    ]
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
        indices=indices,
        interpretacoesCoberturaSolo=[
            InterpretacaoCoberturaSolo(dataAvaliacao="2022-01-01", porcentualPalhada=50),
            InterpretacaoCoberturaSolo(dataAvaliacao="2023-01-01", porcentualPalhada=55),
            InterpretacaoCoberturaSolo(dataAvaliacao="2024-01-01", porcentualPalhada=60),
        ],
        interpretacoesCultura=[
            InterpretacaoCultura(tipoCultivo="Cultivo de 2ª safra",
                                 dataInicio="2023-10-01", dataFim="2024-02-01"),
        ],
        interpretacoesManejo=[
            InterpretacaoManejo(data="2021-01-28", operacao="Revolvimento do solo"),
        ],
    )


# --------------------------------------------------------------------------
# Ações individuais
# --------------------------------------------------------------------------

def autenticacao() -> None:
    print("\n=== Autenticação ===")
    roles        = client.roles
    client_roles = client.client_roles
    print(f"Usuário     : {USUARIO}")
    print(f"Realm roles : {roles}")
    for client_id, cr in client_roles.items():
        print(f"Papeis de acesso no client {client_id}:")
        for papel in cr:
            print(f"  - {papel}")
    if not roles and not client_roles:
        print("ERRO: nenhum role encontrado no token.", file=sys.stderr)
        sys.exit(1)


def listar_glebas() -> None:
    print("\n=== Listando glebas cadastradas ===")
    try:
        t0 = time.perf_counter()
        glebas = client.listar_glebas()
        elapsed = time.perf_counter() - t0
        total = len(glebas) if isinstance(glebas, list) else "?"
        print(f"Total de glebas: {total}")
        print(f"  Tempo: {elapsed:.2f}s")
    except PermissaoError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)
    except APIError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)


def listar_sensoriamentos() -> None:
    print("\n=== Listando sensoriamentos remotos cadastrados ===")
    try:
        t0 = time.perf_counter()
        sensoriamentos = client.listar_sensoriamentos_remotos()
        elapsed = time.perf_counter() - t0
        total = len(sensoriamentos) if isinstance(sensoriamentos, list) else "?"
        print(f"Total de sensoriamentos: {total}")
        print(f"  Tempo: {elapsed:.2f}s")
    except PermissaoError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)
    except APIError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)


def cadastra_gleba() -> str:
    """Cadastra gleba e retorna a chaveClassificacaoNM."""
    print("\n=== Cadastrando talhão/gleba ===")
    try:
        t0 = time.perf_counter()
        resp = client.cadastrar_gleba(_dado_gleba())
        elapsed = time.perf_counter() - t0
        chave = resp.get("chaveClassificacaoNM")
        print("Gleba cadastrada com sucesso!")
        print(f"  UUID              : {resp.get('uuidGleba')}")
        print(f"  Chave Classificação NM: {chave}")
        print(f"  Tempo: {elapsed:.2f}s")
        # Linha parsável para captura em CI (ex: GitHub Actions)
        print(f"CHAVE_NM={chave}")
        return chave
    except PermissaoError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)
    except APIError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)


def cadastra_analise_solo(chave_nm: str) -> None:
    print("\n=== Cadastrando análise de solo ===")
    try:
        t0 = time.perf_counter()
        resp = client.cadastrar_analise_solo(_analise_solo(), chave_classificacao_nm=chave_nm)
        elapsed = time.perf_counter() - t0
        print("Análise de solo cadastrada com sucesso!")
        print(f"  UUID: {resp.get('uuidAnaliseSolo')}")
        print(f"  Tempo: {elapsed:.2f}s")
    except PermissaoError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)
    except APIError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)


def cadastra_sensoriamento_remoto(chave_nm: str) -> None:
    print("\n=== Cadastrando sensoriamento remoto ===")
    try:
        t0 = time.perf_counter()
        resp = client.cadastrar_sensoriamento_remoto(
            _sensoriamento_remoto(), chave_classificacao_nm=chave_nm
        )
        elapsed = time.perf_counter() - t0
        print("Sensoriamento remoto cadastrado com sucesso!")
        print(f"  UUID: {resp.get('uuidSensoriamentoRemoto')}")
        print(f"  Tempo: {elapsed:.2f}s")
    except PermissaoError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)
    except APIError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)


def consulta_classificacao_nm(chave_nm: str) -> None:
    print("\n=== Consultando classificação de nível de manejo ===")
    try:
        t0 = time.perf_counter()
        classificacao = client.consultar_classificacao(chave_nm)
        elapsed = time.perf_counter() - t0
        print(f"Classificação obtida para chave: {chave_nm}")
        print(f"  Resultado: {classificacao}")
        print(f"  Tempo: {elapsed:.2f}s")
    except NotFoundError:
        print("Classificação ainda não disponível (processamento em andamento).")
    except PermissaoError as exc:
        print(exc.format_report(), file=sys.stderr)
        sys.exit(1)
    except SINMError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)


# --------------------------------------------------------------------------
# Despacho
# --------------------------------------------------------------------------

if ACAO == "autenticacao":
    autenticacao()

elif ACAO == "listarGlebas":
    autenticacao()
    listar_glebas()

elif ACAO == "listarSensoriamentos":
    autenticacao()
    listar_sensoriamentos()

elif ACAO == "cadastraGleba":
    autenticacao()
    cadastra_gleba()

elif ACAO == "cadastraAnaliseSolo":
    autenticacao()
    cadastra_analise_solo(CHAVE_NM)

elif ACAO == "cadastraSensoriamentoRemoto":
    autenticacao()
    cadastra_sensoriamento_remoto(CHAVE_NM)

elif ACAO == "consultaClassificacaoNM":
    autenticacao()
    consulta_classificacao_nm(CHAVE_NM)

else:
    # Fluxo completo: cadastra gleba, análise, sensoriamento e consulta classificação
    autenticacao()
    chave_nm = cadastra_gleba()
    if chave_nm:
        cadastra_analise_solo(chave_nm)
        cadastra_sensoriamento_remoto(chave_nm)
        consulta_classificacao_nm(chave_nm)
    listar_glebas()
