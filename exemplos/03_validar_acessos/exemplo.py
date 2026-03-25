"""
Exemplo 03 — Validar Acessos

Autentica o usuário no Keycloak e imprime um relatório completo das
autorizações presentes no token JWT: realm roles e client roles por empresa
(CNPJ / client ID), com a descrição de cada capacidade habilitada.

Uso:
    python exemplo.py

Credenciais via arquivo .env (cp ../env.example .env).
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

from czarsinm import SINMClient

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
# Mapeamento de client roles → capacidades
# --------------------------------------------------------------------------

# Roles de sistema que não representam permissões funcionais do SINM
_ROLES_SISTEMA = {"offline_access", "uma_authorization"}

_NOMES_ROLE = {
    "OPERADOR_CONTRATOS":           "Operador de Contratos",
    "OPERADOR_ANALISE_SOLO":        "Operador de Análise de Solo",
    "OPERADOR_SENSORIAMENTO_REMOTO": "Operador de Sensoriamento Remoto",
}

# Para cada role, lista de ações que o usuário pode realizar na empresa
_CAPACIDADES_ROLE = {
    "OPERADOR_CONTRATOS": [
        "Cadastrar glebas (talhões) vinculadas a contratos da empresa",
        "Listar e consultar glebas da empresa",
        "Consultar operações de nível de manejo (NM) da empresa",
        "Acompanhar a classificação de nível de manejo das glebas cadastradas",
    ],
    "OPERADOR_ANALISE_SOLO": [
        "Cadastrar análises de solo para as operações de nível de manejo da empresa",
        "Enviar amostras de solo associadas a glebas da empresa",
    ],
    "OPERADOR_SENSORIAMENTO_REMOTO": [
        "Cadastrar dados de sensoriamento remoto para operações de nível de manejo da empresa",
        "Enviar índices espectrais (NDVI, NDTI) e interpretações de cobertura/cultura/manejo",
    ],
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ: 14 dígitos → XX.XXX.XXX/XXXX-XX."""
    c = cnpj.strip().replace(".", "").replace("/", "").replace("-", "")
    if len(c) == 14:
        return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
    return cnpj


def _separador(char: str = "-", largura: int = 60) -> str:
    return char * largura


# --------------------------------------------------------------------------
# Relatório
# --------------------------------------------------------------------------

def relatorio_acessos() -> None:
    print()
    print(_separador("="))
    print("  RELATORIO DE AUTORIZACOES DO USUARIO")
    print(_separador("="))
    print(f"  Usuario : {USUARIO}")
    print(f"  Ambiente: {AMBIENTE.upper()}")

    realm_roles  = client.roles
    client_roles = client.client_roles

    # -- Realm roles -------------------------------------------------------
    print()
    print(_separador())
    print("  Roles de Realm")
    print(_separador())

    roles_relevantes = sorted(
        r for r in realm_roles
        if not r.startswith("default-roles") and r not in _ROLES_SISTEMA
    )
    if roles_relevantes:
        for role in roles_relevantes:
            print(f"  * {role}")
    else:
        print("  (nenhum role de realm relevante encontrado)")

    # -- Client roles por empresa ------------------------------------------
    print()
    print(_separador())
    print("  Autorizacoes por Empresa (Client ID / CNPJ)")
    print(_separador())

    # Remove clientes de sistema (account, broker, etc.)
    _CLIENTES_SISTEMA = {"account", "broker", "security-admin-console"}
    empresas = {
        cid: roles
        for cid, roles in client_roles.items()
        if cid not in _CLIENTES_SISTEMA
    }

    if not empresas:
        print()
        print("  Nenhuma autorizacao por empresa encontrada no token.")
    else:
        for cnpj_raw, roles in sorted(empresas.items()):
            cnpj_fmt = _formatar_cnpj(cnpj_raw)
            print()
            print(f"  Empresa  : {cnpj_fmt}")
            print(f"  Client ID: {cnpj_raw}")
            print(f"  Roles    : {', '.join(sorted(roles)) if roles else '(nenhuma)'}")
            print()

            if not roles:
                print("    Nenhum role atribuido para esta empresa.")
                continue

            print("  Capacidades habilitadas:")
            for role in sorted(roles):
                nome_role  = _NOMES_ROLE.get(role, role)
                capacidades = _CAPACIDADES_ROLE.get(role)

                print()
                print(f"    [{nome_role}]")

                if capacidades:
                    for cap in capacidades:
                        print(f"      + {cap} — empresa {cnpj_fmt}")
                else:
                    print(f"      (role '{role}' nao possui descricao mapeada)")

    print()
    print(_separador("="))
    print()


relatorio_acessos()
