"""
Exemplo 05 — Racional do cálculo (por que aquele NM?)

Autentica o usuário humano no Keycloak via ROPC (grant_type=password) com
usuário / senha / client, consulta o racional do cálculo de uma classificação
(pela chaveClassificacaoNM) e imprime de forma legível.

O racional explica *por que* a gleba recebeu aquele nível de manejo: a regra
que determinou a nota, os indicadores limitantes, os fatores restritivos
ativados e a narrativa do cálculo. Só existe para a classificação COMPLETA —
preliminar/sem cálculo responde "não disponível" (404).

Desde a v6.2026 a leitura é causal: `regraDeterminante` e `limitantesPrincipais`
na classificação, `papelNaNota` e `contribuicao` por indicador. O antigo
`efeitoNaNota` continua na resposta, mas está depreciado (ele compara com a nota
final, então some quando um teto trava a nota).

A projeção depende dos papéis do usuário na empresa operadora da gleba:
  - com OPERADOR_ANALISE_SOLO  → completa (valor, faixa, score e contribuição)
  - sem OPERADOR_ANALISE_SOLO  → compacta (nome, origem e papel na nota)

Uso:
    python exemplo.py --chave SUA_CHAVE
    python exemplo.py --chave SUA_CHAVE --json     # imprime o JSON cru
    python exemplo.py                              # pergunta a chave no terminal

Credenciais: lidas do .env (cp ../env.example .env) ou perguntadas no terminal.
"""

import argparse
import getpass
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
    description="Autentica (ROPC) e imprime o racional do cálculo de uma classificação.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--chave", default=None, help="chaveClassificacaoNM a consultar.")
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
# Credenciais: .env com fallback interativo
# --------------------------------------------------------------------------
def _pedir(nome: str, env_var: str, secreto: bool = False) -> str:
    valor = os.getenv(env_var)
    if valor:
        return valor
    if secreto:
        return getpass.getpass(f"{nome}: ")
    return input(f"{nome}: ").strip()


USUARIO       = _pedir("Usuário", "SINM_USERNAME")
SENHA         = _pedir("Senha", "SINM_PASSWORD", secreto=True)
CLIENT_ID     = _pedir("Client ID (CNPJ)", "SINM_CLIENT_ID")
CLIENT_SECRET = _pedir("Client secret", "SINM_CLIENT_SECRET", secreto=True)

AMBIENTE       = os.getenv("SINM_AMBIENTE", "hml")
BACKEND_URL    = os.getenv("SINM_BACKEND_URL")
KEYCLOAK_URL   = os.getenv("SINM_KEYCLOAK")
KEYCLOAK_REALM = os.getenv("SINM_KEYCLOAK_REALM")
# Racional é, por natureza, autenticação do usuário humano (ROPC). Default password.
GRANT_TYPE     = os.getenv("SINM_GRANT_TYPE") or "password"

CHAVE = args.chave or input("chaveClassificacaoNM: ").strip()
if not CHAVE:
    raise SystemExit("Informe a chaveClassificacaoNM (--chave ou no prompt).")


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
    print(f"  Usuário : {USUARIO}")
    print(f"  Ambiente: {AMBIENTE.upper()}")
    print(f"  Chave   : {r.get('chaveClassificacaoNM', CHAVE)}")
    print(f"  Projeção: {'COMPLETA' if completa else 'COMPACTA'}")
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
        grant_type=GRANT_TYPE,  # ROPC (password) por padrão: o humano é o autenticado
    )

    try:
        racional = client.consultar_racional(CHAVE)
    except NotFoundError:
        raise SystemExit(
            "Racional não disponível: só existe para a classificação COMPLETA "
            "(a chave pode ser preliminar ou ainda estar em processamento)."
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
