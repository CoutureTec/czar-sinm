"""
Exemplo 04 — Interface Interativa

Autentica o usuário e apresenta um menu interativo no terminal para explorar
e operar a API SINM: listar, cadastrar, buscar e consultar recursos, além de
inspecionar as autorizações da conta.

Se o arquivo .env não existir (ou estiver incompleto), as credenciais são
solicitadas diretamente no terminal. Após autenticar com sucesso, o usuário
pode optar por salvar as credenciais em .env para as próximas execuções.

Uso:
    python exemplo.py

Credenciais via arquivo .env (cp ../env.example .env) — ou informe
interativamente na inicialização.
"""

import csv
import getpass
import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from czarsinm import (
    SINMClient,
    DadoGleba, Produtor, Propriedade, Talhao,
    Manejo, Operacao, TipoOperacao, CoberturaSolo, Producao, Cultura,
    AnaliseSolo, Amostra, AmostraFisica,
    SensoriamentoRemoto, Indice,
    InterpretacaoCoberturaSolo, InterpretacaoCultura, InterpretacaoManejo,
)
from czarsinm.exceptions import SINMError, NotFoundError, APIError, PermissaoError

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
_log_level = logging.DEBUG if os.getenv("DEBUG", "").lower() == "true" else logging.INFO
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# --------------------------------------------------------------------------
# Apresentação
# --------------------------------------------------------------------------
LARGURA = 64
SEP  = "=" * LARGURA
SEP_ = "-" * LARGURA

_ROLES_SISTEMA    = {"offline_access", "uma_authorization"}
_CLIENTES_SISTEMA = {"account", "broker", "security-admin-console"}

_NOMES_ROLE = {
    "OPERADOR_CONTRATOS":            "Operador de Contratos",
    "OPERADOR_ANALISE_SOLO":         "Operador de Análise de Solo",
    "OPERADOR_SENSORIAMENTO_REMOTO": "Operador de Sensoriamento Remoto",
}

ENV_FILE = Path(__file__).parent / ".env"

# --------------------------------------------------------------------------
# Credenciais — leitura do .env ou coleta interativa
# --------------------------------------------------------------------------

def _carregar_ou_pedir_credenciais():
    """
    Tenta carregar credenciais do .env. Se alguma obrigatória estiver ausente,
    solicita interativamente. Retorna uma tupla com todos os valores e um flag
    indicando se as credenciais foram digitadas pelo usuário (e não lidas do .env).
    """
    load_dotenv(ENV_FILE)

    usuario       = os.getenv("SINM_USERNAME", "").strip()
    senha         = os.getenv("SINM_PASSWORD", "").strip()
    client_id     = os.getenv("SINM_CLIENT_ID", "").strip()
    client_secret = os.getenv("SINM_CLIENT_SECRET", "").strip()

    digitadas_pelo_usuario = not all([usuario, senha, client_id, client_secret])

    if digitadas_pelo_usuario:
        print()
        print(SEP)
        print("  SINM — Credenciais")
        print(SEP)
        if ENV_FILE.exists():
            print("  Arquivo .env encontrado, mas está incompleto.")
        else:
            print("  Arquivo .env não encontrado.")
        print("  Preencha as credenciais abaixo (senha não será exibida):")
        print()

        if not usuario:
            usuario = input("  Usuário       (SINM_USERNAME)    : ").strip()
        if not senha:
            senha = getpass.getpass("  Senha         (SINM_PASSWORD)    : ")
        if not client_id:
            client_id = input("  Client ID     (SINM_CLIENT_ID)   : ").strip()
        if not client_secret:
            client_secret = getpass.getpass("  Client Secret (SINM_CLIENT_SECRET): ")

    ambiente = os.getenv("SINM_AMBIENTE", "").strip()
    if not ambiente:
        if digitadas_pelo_usuario:
            raw = input("  Ambiente      [hml/prd, Enter=hml]: ").strip()
            ambiente = raw if raw else "hml"
        else:
            ambiente = "hml"

    backend_url    = os.getenv("SINM_BACKEND_URL", "").strip() or None
    keycloak_url   = os.getenv("SINM_KEYCLOAK", "").strip() or None
    keycloak_realm = os.getenv("SINM_KEYCLOAK_REALM", "").strip() or None
    grant_type     = os.getenv("SINM_GRANT_TYPE", "").strip() or None

    if digitadas_pelo_usuario and ambiente not in ("hml", "prd"):
        print()
        print("  Ambiente customizado — informe os endpoints (Enter para omitir):")
        raw = input("  URL da API     (SINM_BACKEND_URL)   : ").strip()
        backend_url = raw or None
        raw = input("  URL Keycloak   (SINM_KEYCLOAK)      : ").strip()
        keycloak_url = raw or None
        raw = input("  Realm          (SINM_KEYCLOAK_REALM): ").strip()
        keycloak_realm = raw or None

    return (
        usuario, senha, client_id, client_secret,
        ambiente, backend_url, keycloak_url, keycloak_realm,
        grant_type, digitadas_pelo_usuario,
    )


def _salvar_env(usuario, senha, client_id, client_secret,
                ambiente, backend_url, keycloak_url, keycloak_realm):
    linhas = [
        "# Gerado pelo exemplo 04_interativo\n",
        f"SINM_AMBIENTE={ambiente}\n",
        "\n",
        f"SINM_USERNAME={usuario}\n",
        f"SINM_PASSWORD={senha}\n",
        f"SINM_CLIENT_ID={client_id}\n",
        f"SINM_CLIENT_SECRET={client_secret}\n",
    ]
    if backend_url:
        linhas.append(f"SINM_BACKEND_URL={backend_url}\n")
    if keycloak_url:
        linhas.append(f"SINM_KEYCLOAK={keycloak_url}\n")
    if keycloak_realm:
        linhas.append(f"SINM_KEYCLOAK_REALM={keycloak_realm}\n")

    with ENV_FILE.open("w", encoding="utf-8") as f:
        f.writelines(linhas)
    print(f"  Credenciais salvas em: {ENV_FILE}")


# --------------------------------------------------------------------------
# Autenticação (ocorre uma única vez na inicialização)
# --------------------------------------------------------------------------

(
    USUARIO, SENHA, CLIENT_ID, CLIENT_SECRET,
    AMBIENTE, BACKEND_URL, KEYCLOAK_URL, KEYCLOAK_REALM,
    GRANT_TYPE, _credenciais_manuais,
) = _carregar_ou_pedir_credenciais()

print()
print(SEP)
print("  SINM — Autenticando...")
print(SEP)
print(f"  Usuário : {USUARIO}")
print(f"  Ambiente: {AMBIENTE.upper()}")
print()

client = SINMClient(
    username=USUARIO,
    password=SENHA,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    ambiente=AMBIENTE,
    base_url=BACKEND_URL,
    keycloak_url=KEYCLOAK_URL,
    keycloak_realm=KEYCLOAK_REALM,
    grant_type=GRANT_TYPE,
)

print("  Autenticado com sucesso!")

if _credenciais_manuais:
    print()
    raw = input("  Salvar credenciais em .env para a próxima vez? [s/N]: ").strip().lower()
    if raw in ("s", "sim"):
        _salvar_env(
            USUARIO, SENHA, CLIENT_ID, CLIENT_SECRET,
            AMBIENTE, BACKEND_URL, KEYCLOAK_URL, KEYCLOAK_REALM,
        )

print(SEP)

# --------------------------------------------------------------------------
# Estado da sessão
# --------------------------------------------------------------------------
cnpj_ativo = None   # CNPJ do operador ativo selecionado pelo usuário

# --------------------------------------------------------------------------
# Helpers — leitura de CSV
# --------------------------------------------------------------------------

def _csv(arquivo):
    with arquivo.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _bool(val):
    return val.strip().lower() in ("true", "1", "sim", "s")


def _opt(val):
    v = val.strip()
    return v if v else None


# --------------------------------------------------------------------------
# Helpers — I/O interativo
# --------------------------------------------------------------------------

def _pedir_diretorio(prompt="Diretório de dados"):
    raw = input(f"  {prompt} (ex: ../02_dados_externos/dados/processo_001): ").strip()
    if not raw:
        return None
    d = Path(raw)
    if not d.is_dir():
        print(f"  Diretório não encontrado: {d}")
        return None
    return d


def _pedir(prompt):
    return input(f"  {prompt}: ").strip()


# --------------------------------------------------------------------------
# Helpers — formatação de saída
# --------------------------------------------------------------------------

def _formatar_cnpj(cnpj):
    c = cnpj.strip().replace(".", "").replace("/", "").replace("-", "")
    if len(c) == 14:
        return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
    return cnpj


def _dump(dados):
    print()
    print(json.dumps(dados, ensure_ascii=False, indent=2))


def _roles_cnpj(cnpj):
    return client.client_roles.get(cnpj, [])


# --------------------------------------------------------------------------
# Leitores de entidades a partir dos CSVs (mesma estrutura do exemplo 02)
# --------------------------------------------------------------------------

def ler_dado_gleba(d):
    row_p  = _csv(d / "talhao" / "produtor.csv")[0]
    row_pr = _csv(d / "talhao" / "propriedade.csv")[0]
    row_t  = _csv(d / "talhao" / "talhao.csv")[0]
    manejos = [
        Manejo(
            data=r["data"],
            operacao=Operacao(nomeOperacao=r["nome_operacao"]),
            tipoOperacao=TipoOperacao(tipo=r["tipo_operacao"]),
        )
        for r in _csv(d / "talhao" / "manejos.csv")
    ]
    coberturas = [
        CoberturaSolo(
            dataAvaliacao=r["data_avaliacao"],
            porcentualPalhada=int(r["porcentual_palhada"]),
        )
        for r in _csv(d / "talhao" / "coberturas_solo.csv")
    ]
    producoes = []
    for r in _csv(d / "talhao" / "producoes.csv"):
        ilp_raw = r.get("ilp", "").strip()
        producoes.append(Producao(
            cultura=Cultura(codigo=r["codigo_cultura"]),
            ilp=_bool(ilp_raw) if ilp_raw else None,
            dataPlantio=_opt(r.get("data_plantio", "")),
            dataColheita=_opt(r.get("data_colheita", "")),
            dataPrevisaoPlantio=_opt(r.get("data_previsao_plantio", "")),
            dataPrevisaoColheita=_opt(r.get("data_previsao_colheita", "")),
        ))
    return DadoGleba(
        produtor=Produtor(nome=row_p["nome"], cpf=row_p["cpf"]),
        propriedade=Propriedade(
            nome=row_pr["nome"],
            cnpj=row_pr["cnpj"],
            codigoCar=row_pr["codigo_car"],
            codigoIbge=row_pr["codigo_ibge"],
            poligono=row_pr["poligono"],
        ),
        talhao=Talhao(
            poligono=row_t["poligono"],
            area=float(row_t["area"]),
            tipoProdutor=row_t["tipo_produtor"],
            plantioContorno=int(row_t["plantio_contorno"]),
            cnpjOperador=_opt(row_t["cnpj_operador"]),
        ),
        manejos=manejos,
        coberturas=coberturas,
        producoes=producoes,
    )


def ler_analise_solo(d):
    row = _csv(d / "analise_solo" / "analise_solo.csv")[0]
    amostras_quimicas = [
        Amostra(
            cpfResponsavelColeta=a["cpf_responsavel_coleta"],
            dataColeta=a["data_coleta"],
            longitude=float(a["longitude"]),
            latitude=float(a["latitude"]),
            camada=a["camada"],
            calcio=float(a["calcio"]),
            magnesio=float(a["magnesio"]),
            potassio=float(a["potassio"]),
            sodio=float(a["sodio"]) if a.get("sodio") else None,
            aluminio=float(a["aluminio"]),
            acidezPotencial=float(a["acidez_potencial"]),
            phh2o=float(a["ph_h2o"]) if a.get("ph_h2o") else None,
            fosforoMehlich=float(a["fosforo_mehlich"]) if a.get("fosforo_mehlich") else None,
            enxofre=float(a["enxofre"]),
            mos=float(a["mos"]),
        )
        for a in _csv(d / "analise_solo" / "amostras_quimicas.csv")
    ]
    amostras_fisicas_path = d / "analise_solo" / "amostras_fisicas.csv"
    amostras_fisicas = [
        AmostraFisica(
            cpfResponsavelColeta=a.get("cpf_responsavel_coleta") or None,
            dataColeta=a["data_coleta"],
            longitude=float(a["longitude"]),
            latitude=float(a["latitude"]),
            camada=a["camada"],
            areia=float(a["areia"]),
            silte=float(a["silte"]),
            argila=float(a["argila"]),
        )
        for a in _csv(amostras_fisicas_path)
    ] if amostras_fisicas_path.exists() else []
    return AnaliseSolo(
        cpfProdutor=row["cpf_produtor"],
        cnpj=row["cnpj"],
        amostrasQuimicas=amostras_quimicas,
        amostrasFisicas=amostras_fisicas,
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
# Ações do menu
# --------------------------------------------------------------------------

def acao_listar_glebas():
    print(f"\n{SEP_}\n  Listar Glebas\n{SEP_}")
    try:
        t0 = time.perf_counter()
        items = client.listar_glebas()
        elapsed = time.perf_counter() - t0
        total = len(items) if isinstance(items, list) else "?"
        print(f"  Total: {total}  ({elapsed:.2f}s)")
        if items:
            _dump(items)
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())


def acao_cadastrar_gleba():
    print(f"\n{SEP_}\n  Cadastrar Gleba\n{SEP_}")
    d = _pedir_diretorio()
    if not d:
        return
    try:
        t0 = time.perf_counter()
        resp = client.cadastrar_gleba(ler_dado_gleba(d))
        elapsed = time.perf_counter() - t0
        print()
        print("  Gleba cadastrada com sucesso!")
        print(f"  UUID Gleba          : {resp.get('uuidGleba') or resp.get('uuid')}")
        print(f"  Chave Classificação : {resp.get('chaveClassificacaoNM')}")
        print(f"  Tempo               : {elapsed:.2f}s")
        _dump(resp)
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())
    except Exception as exc:
        print(f"  Erro ao ler dados: {exc}")


def acao_buscar_gleba():
    print(f"\n{SEP_}\n  Buscar Gleba por UUID\n{SEP_}")
    uuid = _pedir("UUID da gleba")
    if not uuid:
        return
    try:
        t0 = time.perf_counter()
        resp = client.buscar_gleba(uuid)
        elapsed = time.perf_counter() - t0
        _dump(resp)
        print(f"\n  Tempo: {elapsed:.2f}s")
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())


def acao_listar_analises():
    print(f"\n{SEP_}\n  Listar Análises de Solo\n{SEP_}")
    try:
        t0 = time.perf_counter()
        items = client.listar_analises_solo()
        elapsed = time.perf_counter() - t0
        total = len(items) if isinstance(items, list) else "?"
        print(f"  Total: {total}  ({elapsed:.2f}s)")
        if items:
            _dump(items)
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())


def acao_cadastrar_analise_solo():
    print(f"\n{SEP_}\n  Cadastrar Análise de Solo\n{SEP_}")
    d = _pedir_diretorio()
    if not d:
        return
    chave = _pedir("Chave de Classificação NM (chaveClassificacaoNM)")
    if not chave:
        print("  Chave obrigatória.")
        return
    try:
        t0 = time.perf_counter()
        resp = client.cadastrar_analise_solo(ler_analise_solo(d), chave_classificacao_nm=chave)
        elapsed = time.perf_counter() - t0
        print()
        print("  Análise de solo cadastrada com sucesso!")
        print(f"  UUID  : {resp.get('uuid')}")
        print(f"  Tempo : {elapsed:.2f}s")
        _dump(resp)
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())
    except Exception as exc:
        print(f"  Erro ao ler dados: {exc}")


def acao_buscar_analise_solo():
    print(f"\n{SEP_}\n  Buscar Análise de Solo por UUID\n{SEP_}")
    uuid = _pedir("UUID da análise de solo")
    if not uuid:
        return
    try:
        t0 = time.perf_counter()
        resp = client.buscar_analise_solo(uuid)
        elapsed = time.perf_counter() - t0
        _dump(resp)
        print(f"\n  Tempo: {elapsed:.2f}s")
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())


def acao_listar_sensoriamentos():
    print(f"\n{SEP_}\n  Listar Sensoriamentos Remotos\n{SEP_}")
    try:
        t0 = time.perf_counter()
        items = client.listar_sensoriamentos_remotos()
        elapsed = time.perf_counter() - t0
        total = len(items) if isinstance(items, list) else "?"
        print(f"  Total: {total}  ({elapsed:.2f}s)")
        if items:
            _dump(items)
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())


def acao_cadastrar_sensoriamento():
    print(f"\n{SEP_}\n  Cadastrar Sensoriamento Remoto\n{SEP_}")
    d = _pedir_diretorio()
    if not d:
        return
    chave = _pedir("Chave de Classificação NM (chaveClassificacaoNM)")
    if not chave:
        print("  Chave obrigatória.")
        return
    try:
        t0 = time.perf_counter()
        resp = client.cadastrar_sensoriamento_remoto(
            ler_sensoriamento_remoto(d), chave_classificacao_nm=chave
        )
        elapsed = time.perf_counter() - t0
        print()
        print("  Sensoriamento remoto cadastrado com sucesso!")
        print(f"  UUID  : {resp.get('uuid')}")
        print(f"  Tempo : {elapsed:.2f}s")
        _dump(resp)
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())
    except Exception as exc:
        print(f"  Erro ao ler dados: {exc}")


def acao_buscar_sensoriamento():
    print(f"\n{SEP_}\n  Buscar Sensoriamento Remoto por UUID\n{SEP_}")
    uuid = _pedir("UUID do sensoriamento")
    if not uuid:
        return
    try:
        t0 = time.perf_counter()
        resp = client.buscar_sensoriamento_remoto(uuid)
        elapsed = time.perf_counter() - t0
        _dump(resp)
        print(f"\n  Tempo: {elapsed:.2f}s")
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())


def acao_listar_classificacoes():
    print(f"\n{SEP_}\n  Listar Classificações NM\n{SEP_}")
    try:
        t0 = time.perf_counter()
        items = client.listar_classificacoes()
        elapsed = time.perf_counter() - t0
        total = len(items) if isinstance(items, list) else "?"
        print(f"  Total: {total}  ({elapsed:.2f}s)")
        if items:
            _dump(items)
    except (PermissaoError, APIError) as exc:
        print(exc.format_report())


def acao_consultar_classificacao():
    print(f"\n{SEP_}\n  Consultar Classificação NM por Chave\n{SEP_}")
    chave = _pedir("Chave de Classificação NM (chaveClassificacaoNM)")
    if not chave:
        return
    try:
        t0 = time.perf_counter()
        resp = client.consultar_classificacao(chave)
        elapsed = time.perf_counter() - t0
        print(f"\n  Chave : {chave}")
        _dump(resp)
        print(f"\n  Tempo : {elapsed:.2f}s")
    except NotFoundError:
        print("  Classificação ainda não disponível (processamento em andamento).")
    except (PermissaoError, APIError, SINMError) as exc:
        msg = exc.format_report() if hasattr(exc, "format_report") else str(exc)
        print(f"  Erro: {msg}")


def acao_definir_cnpj_ativo():
    global cnpj_ativo
    print(f"\n{SEP_}\n  Definir CNPJ Operador Ativo\n{SEP_}")

    empresas = {
        cid: roles
        for cid, roles in client.client_roles.items()
        if cid not in _CLIENTES_SISTEMA
    }

    if not empresas:
        print("  Nenhuma empresa (CNPJ) encontrada no token.")
        return

    lista = sorted(empresas.items())
    print()
    for i, (cnpj_raw, roles) in enumerate(lista, start=1):
        marcador = "* " if cnpj_raw == cnpj_ativo else "  "
        roles_str = ", ".join(sorted(roles)) if roles else "sem roles"
        print(f"  {marcador}[{i}] {_formatar_cnpj(cnpj_raw)}  ({roles_str})")

    print()
    raw = _pedir("Número da empresa (Enter para cancelar)")
    if not raw:
        return

    try:
        idx = int(raw) - 1
        cnpj_ativo, roles = lista[idx]
    except (ValueError, IndexError):
        print("  Opção inválida.")
        return

    cnpj_fmt = _formatar_cnpj(cnpj_ativo)
    print()
    print(f"  CNPJ Ativo: {cnpj_fmt}")

    if roles:
        print()
        print("  Roles e capacidades habilitadas:")
        caps_por_role = {
            "OPERADOR_CONTRATOS": [
                "Cadastrar e listar glebas (talhões) vinculadas a contratos",
                "Consultar operações e classificações de nível de manejo (NM)",
            ],
            "OPERADOR_ANALISE_SOLO": [
                "Cadastrar análises de solo para operações de NM",
                "Enviar amostras de solo associadas a glebas",
            ],
            "OPERADOR_SENSORIAMENTO_REMOTO": [
                "Cadastrar dados de sensoriamento remoto para operações de NM",
                "Enviar índices espectrais (NDVI, NDTI) e interpretações",
            ],
        }
        for role in sorted(roles):
            nome = _NOMES_ROLE.get(role, role)
            print(f"\n    [{nome}]")
            for cap in caps_por_role.get(role, []):
                print(f"      + {cap}")
    else:
        print("  Nenhum role atribuído para esta empresa.")


def acao_ver_autorizacoes():
    print(f"\n{SEP_}\n  Autorizações do Usuário\n{SEP_}")

    realm_roles  = client.roles
    client_roles = client.client_roles

    roles_relevantes = sorted(
        r for r in realm_roles
        if not r.startswith("default-roles") and r not in _ROLES_SISTEMA
    )
    print()
    print("  Roles de Realm:")
    if roles_relevantes:
        for r in roles_relevantes:
            print(f"    * {r}")
    else:
        print("    (nenhum role de realm relevante)")

    empresas = {
        cid: roles
        for cid, roles in client_roles.items()
        if cid not in _CLIENTES_SISTEMA
    }
    print()
    print("  Autorizações por Empresa (CNPJ):")
    if not empresas:
        print("    (nenhuma empresa encontrada no token)")
    else:
        for cnpj_raw, roles in sorted(empresas.items()):
            marcador = " [ATIVO]" if cnpj_raw == cnpj_ativo else ""
            print()
            print(f"    Empresa  : {_formatar_cnpj(cnpj_raw)}{marcador}")
            print(f"    Roles    : {', '.join(sorted(roles)) if roles else '(nenhuma)'}")


# --------------------------------------------------------------------------
# Definição do menu
# --------------------------------------------------------------------------

_MENU = [
    ("GLEBAS",          " 1", "Listar Glebas",                     acao_listar_glebas),
    ("GLEBAS",          " 2", "Cadastrar Gleba",                   acao_cadastrar_gleba),
    ("GLEBAS",          " 3", "Buscar Gleba por UUID",             acao_buscar_gleba),
    ("ANÁLISE DE SOLO", " 4", "Listar Análises de Solo",           acao_listar_analises),
    ("ANÁLISE DE SOLO", " 5", "Cadastrar Análise de Solo",         acao_cadastrar_analise_solo),
    ("ANÁLISE DE SOLO", " 6", "Buscar Análise de Solo por UUID",   acao_buscar_analise_solo),
    ("SENSORIAMENTO",   " 7", "Listar Sensoriamentos Remotos",     acao_listar_sensoriamentos),
    ("SENSORIAMENTO",   " 8", "Cadastrar Sensoriamento Remoto",    acao_cadastrar_sensoriamento),
    ("SENSORIAMENTO",   " 9", "Buscar Sensoriamento por UUID",     acao_buscar_sensoriamento),
    ("CLASSIFICAÇÃO",   "10", "Listar Classificações NM",          acao_listar_classificacoes),
    ("CLASSIFICAÇÃO",   "11", "Consultar Classificação por Chave", acao_consultar_classificacao),
    ("CONTA",           "12", "Definir CNPJ Operador Ativo",       acao_definir_cnpj_ativo),
    ("CONTA",           "13", "Ver Autorizações Completas",        acao_ver_autorizacoes),
]

_DISPATCH = {num.strip(): fn for (_, num, _, fn) in _MENU}


def _imprimir_menu():
    print()
    print(SEP)
    print(f"  SINM — Interface Interativa  |  {AMBIENTE.upper()}")
    print(f"  Usuário : {USUARIO}")
    if cnpj_ativo:
        roles = _roles_cnpj(cnpj_ativo)
        roles_str = f"  [{', '.join(sorted(roles))}]" if roles else ""
        print(f"  CNPJ    : {_formatar_cnpj(cnpj_ativo)}{roles_str}")
    print(SEP)

    grupo_atual = None
    for (grupo, num, rotulo, _) in _MENU:
        if grupo != grupo_atual:
            print(f"\n  {grupo}")
            grupo_atual = grupo
        print(f"  [{num}] {rotulo}")

    print(f"\n  [ 0] Sair")
    print(SEP)


# --------------------------------------------------------------------------
# Loop principal
# --------------------------------------------------------------------------

while True:
    _imprimir_menu()
    try:
        escolha = input("  Opção: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Encerrando.")
        break

    if escolha == "0":
        print("  Até logo!")
        break

    fn = _DISPATCH.get(escolha)
    if fn is None:
        print("  Opção inválida.")
        continue

    fn()

    print()
    try:
        input("  [Enter para voltar ao menu]")
    except (KeyboardInterrupt, EOFError):
        print("\n  Encerrando.")
        break
