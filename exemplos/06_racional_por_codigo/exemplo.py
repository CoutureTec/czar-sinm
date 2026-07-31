"""
Exemplo 06 — Racional do cálculo a partir do código (ambiente do .env)

Variante do exemplo 05 dirigida inteiramente pelo `.env`: monta o SINMClient
com as credenciais e o ambiente configurados (client id, client secret/key,
usuário, senha) e respeita o SINM_GRANT_TYPE definido — `client_credentials`
(service account, padrão) ou `password` (ROPC, usuário humano autenticado).

Recebe o `--codigo` (a chaveClassificacaoNM) e imprime o racional do cálculo:
*por que* a gleba recebeu aquele nível de manejo — a regra que determinou a
nota, os indicadores limitantes, os fatores restritivos ativados e a narrativa
do cálculo. Desde a v6.2026 a leitura é causal (`regraDeterminante`,
`limitantesPrincipais`, `papelNaNota`, `contribuicao`); `efeitoNaNota` continua
na resposta, mas está depreciado.

O racional só existe para a classificação COMPLETA — preliminar/sem cálculo
responde "não disponível" (404). A projeção depende dos papéis do autenticado
na empresa operadora da gleba:
  - com OPERADOR_ANALISE_SOLO  → completa (valor, faixa, score e contribuição)
  - sem OPERADOR_ANALISE_SOLO  → compacta (nome, origem e papel na nota)

Uso:
    python exemplo.py --codigo SUA_CHAVE
    python exemplo.py --codigo SUA_CHAVE --json     # imprime o JSON cru
    python exemplo.py                               # pergunta o código no terminal

Configuração: tudo vem do .env (cp ../env.example .env). O ambiente é o que
estiver em SINM_AMBIENTE (hml/prd ou customizado com SINM_BACKEND_URL,
SINM_KEYCLOAK e SINM_KEYCLOAK_REALM).
"""

import argparse
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from czarsinm import SINMClient
from czarsinm.exceptions import (
    SINMError,
    AuthenticationError,
    NotFoundError,
    PermissaoError,
    APIError,
)

# --------------------------------------------------------------------------
# Argumentos
# --------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Imprime o racional do cálculo de uma classificação a partir do código "
    "(credenciais e ambiente vêm do .env).",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--codigo",
    "--chave",
    dest="codigo",
    default=None,
    help="código da classificação (chaveClassificacaoNM) a consultar.",
)
parser.add_argument("--json", action="store_true", help="imprime o JSON cru em vez do relatório.")
args = parser.parse_args()

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
_log_level = logging.DEBUG if os.getenv("DEBUG", "").lower() == "true" else logging.INFO
logging.basicConfig(level=_log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

SEP = "=" * 64
SEP_ = "-" * 64

# --------------------------------------------------------------------------
# Configuração — tudo do .env (ambiente setado em SINM_AMBIENTE)
# --------------------------------------------------------------------------
USUARIO        = os.getenv("SINM_USERNAME")
SENHA          = os.getenv("SINM_PASSWORD")
CLIENT_ID      = os.getenv("SINM_CLIENT_ID")
CLIENT_SECRET  = os.getenv("SINM_CLIENT_SECRET")
AMBIENTE       = os.getenv("SINM_AMBIENTE", "hml")
BACKEND_URL    = os.getenv("SINM_BACKEND_URL")
KEYCLOAK_URL   = os.getenv("SINM_KEYCLOAK")
KEYCLOAK_REALM = os.getenv("SINM_KEYCLOAK_REALM")
# Padrão client_credentials (service account); use SINM_GRANT_TYPE=password para ROPC.
GRANT_TYPE     = os.getenv("SINM_GRANT_TYPE") or "client_credentials"
# Proxy (opcional): o backend de hml é interno e só resolve via proxy da Embrapa.
# Ex.: SINM_PROXY=http://proxy.cnptia.embrapa.br:3128
PROXY          = os.getenv("SINM_PROXY")
PROXIES        = {"http": PROXY, "https": PROXY} if PROXY else None

if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit("Defina SINM_CLIENT_ID e SINM_CLIENT_SECRET no .env.")
if GRANT_TYPE == "password" and not (USUARIO and SENHA):
    raise SystemExit("grant_type=password exige SINM_USERNAME e SINM_PASSWORD no .env.")

CODIGO = args.codigo or input("código (chaveClassificacaoNM): ").strip()
if not CODIGO:
    raise SystemExit("Informe o código da classificação (--codigo ou no prompt).")

# Identidade autenticada (humano no ROPC, service account no client_credentials).
IDENTIDADE = USUARIO if GRANT_TYPE == "password" else f"service-account-{CLIENT_ID}"


# --------------------------------------------------------------------------
# Apresentação do racional
# --------------------------------------------------------------------------
def _papel_legivel(papel) -> str:
    nomes = {
        "LIMITANTE_PRINCIPAL": "limitante principal",
        "LIMITANTE": "limitante",
        "FAVORAVEL": "favorável",
        "ALINHADO": "alinhado à nota",
    }
    return nomes.get(papel, str(papel or "—"))


def _contribuicao_legivel(contribuicao) -> str:
    nomes = {
        "ACIMA": "acima da média",
        "NA_MEDIA": "na média",
        "ABAIXO": "abaixo da média",
    }
    return nomes.get(contribuicao, str(contribuicao or "—"))


def _regra_legivel(regra) -> str:
    nomes = {
        "BANDA_DA_MEDIA": "a nota veio da média dos indicadores",
        "DOIS_OU_MAIS_NM1": "dois ou mais indicadores em NM1",
        "DOIS_OU_MAIS_NM2": "dois ou mais indicadores em NM2",
        "UM_NM1_UM_NM2": "um indicador em NM1 e outro em NM2",
        "SATURACAO_ALUMINIO_CRITICA": "saturação por alumínio crítica",
        "SATURACAO_ALUMINIO_ALTA": "saturação por alumínio alta",
        "SOJA_EM_SUCESSAO": "soja em sucessão",
        "LEGUMINOSAS_EM_SUCESSAO": "leguminosas em sucessão",
        "DECLIVIDADE_ACENTUADA": "declividade acentuada",
        "TETO_AMBIENTAL": "teto ambiental",
    }
    return nomes.get(regra, str(regra or "—"))


def imprimir_racional(r: dict) -> None:
    indicadores = r.get("indicadores", []) or []
    completa = any("scoreParcial" in ind for ind in indicadores)

    print()
    print(SEP)
    print("  RACIONAL DO CÁLCULO DO NÍVEL DE MANEJO")
    print(SEP)
    print(f"  Autenticado: {IDENTIDADE}")
    print(f"  Grant      : {GRANT_TYPE}")
    print(f"  Ambiente   : {AMBIENTE.upper()}")
    print(f"  Código     : {r.get('chaveClassificacaoNM', CODIGO)}")
    print(f"  Projeção   : {'COMPLETA' if completa else 'COMPACTA'}")
    print()
    print(f"  Nível de manejo : NM{r.get('scoreFinal')}")
    if r.get("scoreMedio") is not None:
        print(f"  Score médio     : {r.get('scoreMedio')}")
    if r.get("dataCalculo"):
        print(f"  Data do cálculo : {r.get('dataCalculo')}")

    # -- Por que essa nota (v6.2026) ---------------------------------------
    if r.get("regraDeterminante"):
        print()
        print(f"  Regra determinante : {r['regraDeterminante']}")
        print(f"    → {_regra_legivel(r['regraDeterminante'])}")
    limitantes = r.get("limitantesPrincipais") or []
    if limitantes:
        print(f"  Limitantes         : {', '.join(limitantes)}")
    elif r.get("regraDeterminante"):
        print("  Limitantes         : (nenhum)")

    # -- Indicadores -------------------------------------------------------
    print()
    print(SEP_)
    print("  Indicadores")
    print(SEP_)
    for ind in indicadores:
        nome = ind.get("nome", "?")
        origem = ind.get("origem", "")
        papel = _papel_legivel(ind.get("papelNaNota"))
        marca = "!" if ind.get("papelNaNota") == "LIMITANTE_PRINCIPAL" else "*"
        if completa:
            valor = ind.get("valor")
            unidade = ind.get("unidade") or ""
            faixa = ind.get("faixa")
            score = ind.get("scoreParcial")
            contribuicao = _contribuicao_legivel(ind.get("contribuicao"))
            valor_str = f"{valor} {unidade}".strip() if valor is not None else "—"
            print(f"  {marca} {nome} ({origem})")
            print(f"      valor: {valor_str} | faixa: {faixa} | score: {score}/4")
            print(f"      papel: {papel} | contribuição: {contribuicao}")
        else:
            print(f"  {marca} {nome} ({origem}) — {papel}")

    # -- Fatores restritivos ----------------------------------------------
    print()
    print(SEP_)
    print("  Fatores restritivos")
    print(SEP_)
    fatores = r.get("fatoresRestritivos", []) or []
    if fatores:
        for f in fatores:
            print(f"  ! {f.get('fator')} — {f.get('descricao')}")
            print(f"      NM{f.get('scoreAntes')} → NM{f.get('scoreDepois')}")
    else:
        print("  (nenhum fator restritivo ativado)")

    # -- Narrativa ---------------------------------------------------------
    if r.get("memoriaCalculo"):
        print()
        print(SEP_)
        print("  Memória de cálculo")
        print(SEP_)
        print(r["memoriaCalculo"])

    print()
    print(SEP)
    print()


# --------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------
def main() -> None:
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
        proxies=PROXIES,
    )

    try:
        racional = client.consultar_racional(CODIGO)
    except NotFoundError as exc:
        # Um 404 tem duas causas distintas: o endpoint não existe (URL/base errada,
        # ex.: prefixo de contexto a mais) ou a classificação não é COMPLETA. O
        # primeiro caso vem como "No static resource ..." no corpo do erro do Spring.
        detalhe = str((exc.body or {}).get("detail", ""))
        if "static resource" in detalhe.lower():
            raise SystemExit(
                f"Falha ao consultar o racional (404): endpoint não encontrado em "
                f"{BACKEND_URL or AMBIENTE}.\n"
                f"Verifique a SINM_BACKEND_URL no .env — o caminho da API parece incorreto.\n"
                f"Detalhe do servidor: {detalhe}"
            )
        raise SystemExit(
            "Racional não disponível: só existe para a classificação COMPLETA "
            "(o código pode ser preliminar ou ainda estar em processamento)."
        )
    except PermissaoError as exc:
        raise SystemExit(f"Sem permissão para consultar o racional: {exc}")
    except AuthenticationError as exc:
        raise SystemExit(f"Falha de autenticação no Keycloak: {exc}")
    except (APIError, SINMError) as exc:
        raise SystemExit(f"Falha ao consultar o racional: {exc}")

    if args.json:
        print(json.dumps(racional, ensure_ascii=False, indent=4))
    else:
        imprimir_racional(racional)


if __name__ == "__main__":
    main()
