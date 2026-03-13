"""
Exemplo de uso da biblioteca zarcnm.

Demonstra o fluxo completo:
  1. Autenticar no ZARC-NM via Keycloak
  2. Cadastrar talhão/gleba
  3. Cadastrar análise de solo
  4. Cadastrar sensoriamento remoto
  5. Consultar classificação de nível de manejo

  Alternativa: usar POST /api/v1/operacoes (cadastrar_operacao) para
  disparar a classificação referenciando recursos já cadastrados pelos UUIDs.

Para executar:
    pip install -e .
    cp .env.example .env   # preencha com suas credenciais
    python example.py
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()  # carrega variáveis do arquivo .env

from zarcnm import (
    ZarcNMClient,
    # Modelos para Gleba
    DadoGleba,
    Produtor,
    Propriedade,
    Talhao,
    Manejo,
    Operacao,
    TipoOperacao,
    CoberturaSolo,
    Producao,
    Cultura,
    # Modelos para Análise de Solo
    AnaliseSolo,
    Amostra,
    # Modelos para Sensoriamento Remoto
    SensoriamentoRemoto,
    Indice,
    InterpretacaoCoberturaSolo,
    InterpretacaoCultura,
    InterpretacaoManejo,
    # Modelo para Operação combinada
    DadosInput,
)
from zarcnm.exceptions import ZarcNMError, NotFoundError, APIError, PermissaoError

# --------------------------------------------------------------------------
# Configuração de log (opcional)
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# --------------------------------------------------------------------------
# Configuração carregada do arquivo .env
# --------------------------------------------------------------------------
USUARIO         = os.environ["ZARCNM_USERNAME"]
SENHA           = os.environ["ZARCNM_PASSWORD"]
CLIENT_ID       = os.environ["ZARCNM_CLIENT_ID"]
CLIENT_SECRET   = os.environ["ZARCNM_CLIENT_SECRET"]
AMBIENTE        = os.getenv("ZARCNM_AMBIENTE", "hml")

# --------------------------------------------------------------------------
# 1. Instanciar o client e verificar roles do usuário
# --------------------------------------------------------------------------
client = ZarcNMClient(
    username=USUARIO,
    password=SENHA,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    ambiente=AMBIENTE,
)

print("\n=== Autenticação ===")
roles = client.roles
print(f"Usuário: {USUARIO}")
print(f"Roles  : {roles}")

ROLES_NECESSARIOS = {"OPERADOR_CONTRATOS", "BETA_USER", "ADMINISTRADOR"}
if not ROLES_NECESSARIOS.intersection(roles):
    print(
        f"\n[AVISO] O usuário não possui os roles necessários para cadastrar glebas.\n"
        f"         Necessário: {ROLES_NECESSARIOS}\n"
        f"         Encontrado: {set(roles)}\n"
        f"         Solicite à equipe ZARC-NM a atribuição do role adequado."
    )

# --------------------------------------------------------------------------
# 2. Montar o payload do talhão/gleba
# --------------------------------------------------------------------------
dado_gleba = DadoGleba(
    produtor=Produtor(
        nome="Produtor Exemplo",
        cpf="68122528082",
    ),
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
        # Safras passadas
        Producao(
            cultura=Cultura(codigo="001"),  # Soja
            ilp=False,
            dataPlantio="2022-10-01",
            dataColheita="2023-01-10",
        ),
        Producao(
            cultura=Cultura(codigo="018"),  # Milho
            ilp=False,
            dataPlantio="2023-02-21",
            dataColheita="2023-08-01",
        ),
        Producao(
            cultura=Cultura(codigo="001"),  # Soja
            ilp=False,
            dataPlantio="2024-10-01",
            dataColheita="2025-01-10",
        ),
        # Safra futura (obrigatória)
        Producao(
            cultura=Cultura(codigo="001"),  # Soja
            dataPrevisaoPlantio="2026-10-01",
            dataPrevisaoColheita="2027-01-10",
        ),
    ],
)

# --------------------------------------------------------------------------
# 3. Cadastrar o talhão
# --------------------------------------------------------------------------
print("\n=== Cadastrando talhão/gleba ===")
try:
    resposta_gleba = client.cadastrar_gleba(dado_gleba)
    print("Gleba cadastrada com sucesso!")
    print(f"  UUID: {resposta_gleba.get('uuid')}")
    print(f"  Chave Classificação NM: {resposta_gleba.get('chaveClassificacaoNM')}")
except PermissaoError as exc:
    print(exc.format_report())
    raise SystemExit(1)
except APIError as exc:
    print(exc.format_report())
    raise SystemExit(1)

uuid_gleba = resposta_gleba.get("uuid")
chave_nm = resposta_gleba.get("chaveClassificacaoNM")

# --------------------------------------------------------------------------
# 4. Montar e cadastrar análise de solo
# --------------------------------------------------------------------------
print("\n=== Cadastrando análise de solo ===")

analise_solo = AnaliseSolo(
    cpfProdutor="68122528082",
    cnpj="54194116000138",
    amostras=[
        Amostra(
            cpfResponsavelColeta="21750077078",
            dataColeta="2024-09-17",
            pontoColeta="POINT (-47.108493 -22.811532)",
            camada="20",
            areia=78.0,
            silte=5.0,
            argila=17.0,
            calcio=0.9,
            magnesio=0.8,
            potassio=59.9,
            sodio=5.6,
            aluminio=0.36,
            acidezPotencial=5.0,
            phh2o=5.4,
            fosforoMehlich=1.1,
            enxofre=6.4,
            mos=10.8,
        ),
        Amostra(
            cpfResponsavelColeta="21750077078",
            dataColeta="2024-09-17",
            pontoColeta="POINT (-47.106733 -22.812530)",
            camada="20",
            areia=75.0,
            silte=6.0,
            argila=19.0,
            calcio=0.8,
            magnesio=0.7,
            potassio=59.2,
            sodio=5.9,
            aluminio=0.36,
            acidezPotencial=4.4,
            phh2o=5.5,
            fosforoMehlich=1.2,
            enxofre=7.3,
            mos=12.6,
        ),
        Amostra(
            cpfResponsavelColeta="21750077078",
            dataColeta="2024-09-17",
            pontoColeta="POINT (-47.103408 -22.812253)",
            camada="40",
            areia=71.0,
            silte=7.0,
            argila=22.0,
            calcio=0.5,
            magnesio=1.1,
            potassio=42.9,
            sodio=7.9,
            aluminio=1.215,
            acidezPotencial=5.2,
            phh2o=5.2,
            fosforoMehlich=0.8,
            enxofre=6.4,
            mos=7.2,
        ),
    ],
)

uuid_analise = None
try:
    resposta_analise = client.cadastrar_analise_solo(
        analise_solo,
        chave_classificacao_nm=chave_nm,
    )
    uuid_analise = resposta_analise.get("uuid")
    print("Análise de solo cadastrada com sucesso!")
    print(f"  UUID: {uuid_analise}")
except PermissaoError as exc:
    print(exc.format_report())
except APIError as exc:
    print(exc.format_report())

# --------------------------------------------------------------------------
# 5. Montar e cadastrar sensoriamento remoto
# --------------------------------------------------------------------------
print("\n=== Cadastrando sensoriamento remoto ===")

# Série temporal de índices NDVI/NDTI (exemplo reduzido — usar série completa em produção)
indices_satelite = [
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

sensoriamento = SensoriamentoRemoto(
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
    indices=indices_satelite,
    interpretacoesCoberturaSolo=[
        InterpretacaoCoberturaSolo(dataAvaliacao="2022-01-01", porcentualPalhada=50),
        InterpretacaoCoberturaSolo(dataAvaliacao="2023-01-01", porcentualPalhada=55),
        InterpretacaoCoberturaSolo(dataAvaliacao="2024-01-01", porcentualPalhada=60),
    ],
    interpretacoesCultura=[
        InterpretacaoCultura(
            tipoCultivo="Cultivo de 2ª safra",
            dataInicio="2023-10-01",
            dataFim="2024-02-01",
        ),
    ],
    interpretacoesManejo=[
        InterpretacaoManejo(data="2021-01-28", operacao="Revolvimento do solo"),
    ],
)

uuid_sr = None
try:
    resposta_sr = client.cadastrar_sensoriamento_remoto(
        sensoriamento,
        chave_classificacao_nm=chave_nm,
    )
    uuid_sr = resposta_sr.get("uuid")
    print("Sensoriamento remoto cadastrado com sucesso!")
    print(f"  UUID: {uuid_sr}")
except PermissaoError as exc:
    print(exc.format_report())
except APIError as exc:
    print(exc.format_report())

# --------------------------------------------------------------------------
# 6. Consultar resultado da classificação de nível de manejo
# --------------------------------------------------------------------------
print("\n=== Consultando classificação de nível de manejo ===")
if chave_nm:
    try:
        classificacao = client.consultar_classificacao(chave_nm)
        print(f"Classificação obtida para chave: {chave_nm}")
        print(f"  Resultado: {classificacao}")
    except NotFoundError:
        print("Classificação ainda não disponível (processamento em andamento).")
    except ZarcNMError as exc:
        print(f"Erro ao consultar classificação: {exc}")
else:
    print("Chave de classificação não disponível — verifique o cadastro da gleba.")

# --------------------------------------------------------------------------
# Listagens (opcional)
# --------------------------------------------------------------------------
print("\n=== Listando glebas cadastradas ===")
glebas = client.listar_glebas()
print(f"Total de glebas: {len(glebas) if isinstance(glebas, list) else '?'}")

