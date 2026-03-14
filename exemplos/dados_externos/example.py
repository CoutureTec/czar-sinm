"""
Exemplo de uso da biblioteca czarnm com dados lidos de arquivos CSV.

Uso:
    python example.py --dados dados/processo_001                                     # fluxo completo
    python example.py --dados dados/processo_001 --acao cadastraGleba
    python example.py --dados dados/processo_001 --acao cadastraAnaliseSolo   --chave_nm CHAVE
    python example.py --dados dados/processo_001 --acao cadastraSensoriamentoRemoto --chave_nm CHAVE
    python example.py --dados dados/processo_001 --acao consultaClassificacaoNM  --chave_nm CHAVE

Credenciais via arquivo .env (cp ../env.example .env).
Os resultados de cada execução são gravados em <diretorio>/resultado.csv.
"""

import argparse
import csv
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from czarnm import (
    SINMClient,
    DadoGleba, Produtor, Propriedade, Talhao,
    Manejo, Operacao, TipoOperacao, CoberturaSolo, Producao, Cultura,
    AnaliseSolo, Amostra,
    SensoriamentoRemoto, Indice,
    InterpretacaoCoberturaSolo, InterpretacaoCultura, InterpretacaoManejo,
)
from czarnm.exceptions import SINMError, NotFoundError, APIError, PermissaoError

ACOES = (
    "cadastraGleba",
    "cadastraAnaliseSolo",
    "cadastraSensoriamentoRemoto",
    "consultaClassificacaoNM",
)

# --------------------------------------------------------------------------
# Argumentos de linha de comando
# --------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Exemplo de integração com a API SINM usando dados de arquivos CSV.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--dados",
    required=True,
    metavar="DIRETORIO",
    help="Caminho para o diretório do processo contendo os arquivos CSV.",
)
parser.add_argument(
    "--acao",
    choices=ACOES,
    default=None,
    help=(
        "Ação a executar. Se omitido, executa o fluxo completo.\n"
        "  cadastraGleba\n"
        "  cadastraAnaliseSolo          (requer --chave_nm ou resultado.csv prévio)\n"
        "  cadastraSensoriamentoRemoto  (requer --chave_nm ou resultado.csv prévio)\n"
        "  consultaClassificacaoNM      (requer --chave_nm ou resultado.csv prévio)\n"
    ),
)
parser.add_argument(
    "--chave_nm",
    default=None,
    metavar="CHAVE",
    help="Chave de classificação NM. Se omitido, tenta ler do resultado.csv gerado por cadastraGleba.",
)
args = parser.parse_args()

DIRETORIO = Path(args.dados)
ACAO = args.acao
CHAVE_NM_ARG = args.chave_nm

if not DIRETORIO.is_dir():
    parser.error(f"Diretório não encontrado: {DIRETORIO}")

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# --------------------------------------------------------------------------
# Credenciais (.env)
# --------------------------------------------------------------------------
USUARIO       = os.environ["SINM_USERNAME"]
SENHA         = os.environ["SINM_PASSWORD"]
CLIENT_ID     = os.environ["SINM_CLIENT_ID"]
CLIENT_SECRET = os.environ["SINM_CLIENT_SECRET"]
AMBIENTE      = os.getenv("SINM_AMBIENTE", "hml")

# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------
client = SINMClient(
    username=USUARIO,
    password=SENHA,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    ambiente=AMBIENTE,
)

print("\n=== Autenticação ===")
roles = client.roles
print(f"Usuário : {USUARIO}")
print(f"Roles   : {roles}")

# --------------------------------------------------------------------------
# Helpers de leitura de CSV
# --------------------------------------------------------------------------

def _csv(arquivo):
    """Lê um CSV e retorna lista de dicts."""
    with arquivo.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _bool(val):
    return val.strip().lower() in ("true", "1", "sim", "s")


def _opt(val):
    v = val.strip()
    return v if v else None


# --------------------------------------------------------------------------
# Leitores de entidades a partir dos CSVs
# --------------------------------------------------------------------------

def ler_produtor(d):
    row = _csv(d / "talhao" / "produtor.csv")[0]
    return Produtor(nome=row["nome"], cpf=row["cpf"])


def ler_propriedade(d):
    row = _csv(d / "talhao" / "propriedade.csv")[0]
    return Propriedade(
        nome=row["nome"],
        cnpj=row["cnpj"],
        codigoCar=row["codigo_car"],
        codigoIbge=row["codigo_ibge"],
        poligono=row["poligono"],
    )


def ler_talhao(d):
    row = _csv(d / "talhao" / "talhao.csv")[0]
    return Talhao(
        poligono=row["poligono"],
        area=float(row["area"]),
        tipoProdutor=row["tipo_produtor"],
        plantioContorno=int(row["plantio_contorno"]),
    )


def ler_manejos(d):
    return [
        Manejo(
            data=row["data"],
            operacao=Operacao(nomeOperacao=row["nome_operacao"]),
            tipoOperacao=TipoOperacao(tipo=row["tipo_operacao"]),
        )
        for row in _csv(d / "talhao" / "manejos.csv")
    ]


def ler_coberturas(d):
    return [
        CoberturaSolo(
            dataAvaliacao=row["data_avaliacao"],
            porcentualPalhada=int(row["porcentual_palhada"]),
        )
        for row in _csv(d / "talhao" / "coberturas_solo.csv")
    ]


def ler_producoes(d):
    result = []
    for row in _csv(d / "talhao" / "producoes.csv"):
        ilp_raw = row.get("ilp", "").strip()
        result.append(Producao(
            cultura=Cultura(codigo=row["codigo_cultura"]),
            ilp=_bool(ilp_raw) if ilp_raw else None,
            dataPlantio=_opt(row.get("data_plantio", "")),
            dataColheita=_opt(row.get("data_colheita", "")),
            dataPrevisaoPlantio=_opt(row.get("data_previsao_plantio", "")),
            dataPrevisaoColheita=_opt(row.get("data_previsao_colheita", "")),
        ))
    return result


def ler_dado_gleba(d):
    return DadoGleba(
        produtor=ler_produtor(d),
        propriedade=ler_propriedade(d),
        talhao=ler_talhao(d),
        manejos=ler_manejos(d),
        coberturas=ler_coberturas(d),
        producoes=ler_producoes(d),
    )


def ler_analise_solo(d):
    row = _csv(d / "analise_solo" / "analise_solo.csv")[0]
    amostras = [
        Amostra(
            cpfResponsavelColeta=a["cpf_responsavel_coleta"],
            dataColeta=a["data_coleta"],
            pontoColeta=a["ponto_coleta"],
            camada=a["camada"],
            areia=float(a["areia"]),
            silte=float(a["silte"]),
            argila=float(a["argila"]),
            calcio=float(a["calcio"]),
            magnesio=float(a["magnesio"]),
            potassio=float(a["potassio"]),
            sodio=float(a["sodio"]),
            aluminio=float(a["aluminio"]),
            acidezPotencial=float(a["acidez_potencial"]),
            phh2o=float(a["ph_h2o"]),
            fosforoMehlich=float(a["fosforo_mehlich"]),
            enxofre=float(a["enxofre"]),
            mos=float(a["mos"]),
        )
        for a in _csv(d / "analise_solo" / "amostras_solo.csv")
    ]
    return AnaliseSolo(
        cpfProdutor=row["cpf_produtor"],
        cnpj=row["cnpj"],
        amostras=amostras,
    )


def ler_sensoriamento_remoto(d):
    sr = d / "sensoriamento_remoto"
    row = _csv(sr / "sensoriamento_remoto.csv")[0]
    indices = [
        Indice(
            codigoSatelite=i["codigo_satelite"],
            coordenada=i["coordenada"],
            data=i["data"],
            ndvi=float(i["ndvi"]),
            ndti=float(i["ndti"]),
        )
        for i in _csv(sr / "indices_sensoriamento_remoto.csv")
    ]
    interp_cobertura = [
        InterpretacaoCoberturaSolo(
            dataAvaliacao=r["data_avaliacao"],
            porcentualPalhada=int(r["porcentual_palhada"]),
        )
        for r in _csv(sr / "interpretacao_cobertura_solo.csv")
    ]
    interp_cultura = [
        InterpretacaoCultura(
            tipoCultivo=r["tipo_cultivo"],
            dataInicio=r["data_inicio"],
            dataFim=r["data_fim"],
        )
        for r in _csv(sr / "interpretacao_cultura.csv")
    ]
    interp_manejo = [
        InterpretacaoManejo(
            data=r["data"],
            operacao=r["operacao"],
        )
        for r in _csv(sr / "interpretacao_manejo.csv")
    ]
    return SensoriamentoRemoto(
        cpfProdutor=row["cpf_produtor"],
        cnpj=row["cnpj"],
        dataInicial=row["data_inicial"],
        dataFinal=row["data_final"],
        declividadeMedia=int(row["declividade_media"]),
        plantioContorno=int(row["plantio_contorno"]),
        terraceamento=int(row["terraceamento"]),
        codigoSateliteDeclividadeMedia=row["codigo_satelite_declividade_media"],
        codigoSatelitePlantioContorno=row["codigo_satelite_plantio_contorno"],
        codigoSateliteTerraceamento=row["codigo_satelite_terraceamento"],
        indices=indices,
        interpretacoesCoberturaSolo=interp_cobertura,
        interpretacoesCultura=interp_cultura,
        interpretacoesManejo=interp_manejo,
    )


# --------------------------------------------------------------------------
# Resultado CSV — leitura e escrita incremental
# --------------------------------------------------------------------------

CAMPOS_RESULTADO = [
    "uuid_gleba",
    "chave_nm",
    "uuid_analise_solo",
    "uuid_sensoriamento_remoto",
    "status_classificacao",
    "valor_classificacao",
]
RESULTADO_CSV = DIRETORIO / "resultado.csv"


def ler_resultado():
    if RESULTADO_CSV.exists():
        rows = _csv(RESULTADO_CSV)
        if rows:
            return rows[0]
    return {c: "" for c in CAMPOS_RESULTADO}


def salvar_resultado(dados):
    with RESULTADO_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_RESULTADO)
        writer.writeheader()
        writer.writerow({c: dados.get(c, "") for c in CAMPOS_RESULTADO})
    print(f"  Resultado salvo em: {RESULTADO_CSV}")


# --------------------------------------------------------------------------
# Ações
# --------------------------------------------------------------------------

def cadastra_gleba():
    print("\n=== Cadastrando talhão/gleba ===")
    try:
        resp = client.cadastrar_gleba(ler_dado_gleba(DIRETORIO))
        print("Gleba cadastrada com sucesso!")
        print(f"  UUID              : {resp.get('uuid')}")
        print(f"  Chave Classificação NM: {resp.get('chaveClassificacaoNM')}")
        resultado = ler_resultado()
        resultado["uuid_gleba"] = resp.get("uuid", "")
        resultado["chave_nm"] = resp.get("chaveClassificacaoNM", "")
        salvar_resultado(resultado)
        return resp.get("chaveClassificacaoNM")
    except PermissaoError as exc:
        print(exc.format_report())
        return None
    except APIError as exc:
        print(exc.format_report())
        return None


def cadastra_analise_solo(chave_nm):
    print("\n=== Cadastrando análise de solo ===")
    try:
        resp = client.cadastrar_analise_solo(
            ler_analise_solo(DIRETORIO), chave_classificacao_nm=chave_nm
        )
        print("Análise de solo cadastrada com sucesso!")
        print(f"  UUID: {resp.get('uuid')}")
        resultado = ler_resultado()
        resultado["uuid_analise_solo"] = resp.get("uuid", "")
        salvar_resultado(resultado)
    except PermissaoError as exc:
        print(exc.format_report())
    except APIError as exc:
        print(exc.format_report())


def cadastra_sensoriamento_remoto(chave_nm):
    print("\n=== Cadastrando sensoriamento remoto ===")
    try:
        resp = client.cadastrar_sensoriamento_remoto(
            ler_sensoriamento_remoto(DIRETORIO), chave_classificacao_nm=chave_nm
        )
        print("Sensoriamento remoto cadastrado com sucesso!")
        print(f"  UUID: {resp.get('uuid')}")
        resultado = ler_resultado()
        resultado["uuid_sensoriamento_remoto"] = resp.get("uuid", "")
        salvar_resultado(resultado)
    except PermissaoError as exc:
        print(exc.format_report())
    except APIError as exc:
        print(exc.format_report())


def consulta_classificacao_nm(chave_nm):
    print("\n=== Consultando classificação de nível de manejo ===")
    resultado = ler_resultado()
    try:
        classificacao = client.consultar_classificacao(chave_nm)
        print(f"Classificação obtida para chave: {chave_nm}")
        print(f"  Resultado: {classificacao}")
        resultado["status_classificacao"] = "disponivel"
        resultado["valor_classificacao"] = str(classificacao)
        salvar_resultado(resultado)
    except NotFoundError:
        print("Classificação ainda não disponível (processamento em andamento).")
        resultado["status_classificacao"] = "em_processamento"
        salvar_resultado(resultado)
    except PermissaoError as exc:
        print(exc.format_report())
    except SINMError as exc:
        print(f"Erro: {exc}")


# --------------------------------------------------------------------------
# Resolve chave_nm: argumento CLI > resultado.csv > erro
# --------------------------------------------------------------------------

def _chave_nm_efetiva():
    if CHAVE_NM_ARG:
        return CHAVE_NM_ARG
    return ler_resultado().get("chave_nm") or None


# --------------------------------------------------------------------------
# Despacho
# --------------------------------------------------------------------------

if ACAO == "cadastraGleba":
    cadastra_gleba()

elif ACAO == "cadastraAnaliseSolo":
    chave = _chave_nm_efetiva()
    if not chave:
        parser.error("--chave_nm é obrigatório (ou execute cadastraGleba antes para gerar resultado.csv).")
    cadastra_analise_solo(chave)

elif ACAO == "cadastraSensoriamentoRemoto":
    chave = _chave_nm_efetiva()
    if not chave:
        parser.error("--chave_nm é obrigatório (ou execute cadastraGleba antes para gerar resultado.csv).")
    cadastra_sensoriamento_remoto(chave)

elif ACAO == "consultaClassificacaoNM":
    chave = _chave_nm_efetiva()
    if not chave:
        parser.error("--chave_nm é obrigatório (ou execute cadastraGleba antes para gerar resultado.csv).")
    consulta_classificacao_nm(chave)

else:
    # Fluxo completo
    chave_nm = _chave_nm_efetiva() or cadastra_gleba()
    if chave_nm:
        cadastra_analise_solo(chave_nm)
        cadastra_sensoriamento_remoto(chave_nm)
        consulta_classificacao_nm(chave_nm)
