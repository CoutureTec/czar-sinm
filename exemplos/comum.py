"""
Partes comuns aos exemplos: configuração (.env), linha de comando, criação do
cliente, consulta da classificação e do racional, e apresentação na tela.
"""

import argparse
import logging
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import date, timedelta

from dotenv import load_dotenv

from czarsinm import SINMClient
from czarsinm.exceptions import APIError, NotFoundError, SINMError

import fonte_dados

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "").lower() == "true" else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# --------------------------------------------------------------------------
# Configuração (.env — veja env.example)
# --------------------------------------------------------------------------
CLIENT_ID = os.getenv("SINM_CLIENT_ID")
CLIENT_SECRET = os.getenv("SINM_CLIENT_SECRET")
GRANT_TYPE = os.getenv("SINM_GRANT_TYPE") or "client_credentials"
USUARIO = os.getenv("SINM_USERNAME")
SENHA = os.getenv("SINM_PASSWORD")
AMBIENTE = os.getenv("SINM_AMBIENTE", "hml")
PROXY = os.getenv("SINM_PROXY")

FONTE = os.getenv("SINM_FONTE", "json")
CAMINHO_DADOS = os.getenv("SINM_DADOS")
# CNPJs que o registro pode deixar em branco; por padrão, a empresa autenticada.
CNPJ_OPERADOR = os.getenv("SINM_CNPJ_OPERADOR") or CLIENT_ID
CNPJ_LABORATORIO = os.getenv("SINM_CNPJ_LABORATORIO") or CLIENT_ID
AJUSTAR_DATAS = os.getenv("SINM_AJUSTAR_DATAS", "nao").lower() in ("sim", "true", "1")


def argumentos(descricao: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=descricao)
    parser.add_argument("--fonte", choices=sorted(fonte_dados.FONTES), default=FONTE,
                        help="de onde ler os dados (padrão: SINM_FONTE ou json)")
    parser.add_argument("--dados", default=CAMINHO_DADOS,
                        help="arquivo/pasta dos dados (padrão: SINM_DADOS ou o da fonte)")
    parser.add_argument("--chave", metavar="CHAVE",
                        help="só consulta a classificação e o racional de uma chave já existente")
    parser.add_argument("--autenticar", action="store_true",
                        help="só autentica e mostra os papéis de acesso")
    return parser.parse_args()


def criar_cliente(api_version: str) -> SINMClient:
    if not CLIENT_ID or not CLIENT_SECRET:
        sys.exit("Defina SINM_CLIENT_ID e SINM_CLIENT_SECRET no .env (veja env.example).")
    if GRANT_TYPE == "password" and not (USUARIO and SENHA):
        sys.exit("SINM_GRANT_TYPE=password exige SINM_USERNAME e SINM_PASSWORD no .env.")
    return SINMClient(
        username=USUARIO,
        password=SENHA,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        ambiente=AMBIENTE,
        base_url=os.getenv("SINM_BACKEND_URL"),
        keycloak_url=os.getenv("SINM_KEYCLOAK"),
        keycloak_realm=os.getenv("SINM_KEYCLOAK_REALM"),
        grant_type=GRANT_TYPE,
        proxies={"http": PROXY, "https": PROXY} if PROXY else None,
        api_version=api_version,
    )


def carregar_envios(fonte: str, caminho: str) -> list:
    """Lê os registros da fonte escolhida e os converte nos modelos do SDK."""
    caminho = caminho or fonte_dados.CAMINHOS_PADRAO[fonte]
    registros = fonte_dados.FONTES[fonte](caminho)
    if AJUSTAR_DATAS:
        registros = [ajustar_datas_do_exemplo(r) for r in registros]
    print(f"Fonte de dados: {fonte} ({caminho}) — {len(registros)} gleba(s)")
    return [fonte_dados.montar(r, CNPJ_OPERADOR, CNPJ_LABORATORIO) for r in registros]


# --------------------------------------------------------------------------
# Datas dos dados de exemplo
# --------------------------------------------------------------------------
_DATA = re.compile(r"\d{4}-\d{2}-\d{2}")


def ajustar_datas_do_exemplo(registro: dict) -> dict:
    """Atualiza as datas dos dados de exemplo (SINM_AJUSTAR_DATAS=sim).

    Os dados de exemplo foram escritos para um plantio em 01/10/2026, mas a API
    valida datas contra o dia de hoje (coberturas recentes, coleta próxima do
    plantio). Para que eles continuem válidos, todas as datas avançam o mesmo
    número de anos até o plantio cair no próximo 1º de outubro, e a coleta das
    amostras passa a ser de dois dias atrás. Não use com dados reais.
    """
    hoje = date.today()
    plantio = date(hoje.year, 10, 1)
    if plantio <= hoje:
        plantio = date(hoje.year + 1, 10, 1)
    anos = plantio.year - 2026
    coleta = (hoje - timedelta(days=2)).isoformat()

    def ajustar(valor, chave=None):
        if isinstance(valor, dict):
            return {k: ajustar(v, k) for k, v in valor.items()}
        if isinstance(valor, list):
            return [ajustar(v, chave) for v in valor]
        if isinstance(valor, str) and _DATA.fullmatch(valor):
            return coleta if chave == "dataColeta" else f"{int(valor[:4]) + anos}{valor[4:]}"
        return valor

    return ajustar(registro)


# --------------------------------------------------------------------------
# Etapas e apresentação
# --------------------------------------------------------------------------
falhas = 0


@contextmanager
def etapa(titulo: str):
    """Imprime a etapa e o tempo gasto; um erro da API é mostrado e contado."""
    global falhas
    print(f"\n--- {titulo}")
    inicio = time.perf_counter()
    try:
        yield
        print(f"    ok ({time.perf_counter() - inicio:.2f}s)")
    except APIError as exc:
        falhas += 1
        print(exc.format_report(), file=sys.stderr)
    except SINMError as exc:
        falhas += 1
        print(f"    ERRO: {exc}", file=sys.stderr)


def autenticar(client: SINMClient) -> None:
    with etapa("Autenticação"):
        identidade = USUARIO if GRANT_TYPE == "password" else f"service account {CLIENT_ID}"
        print(f"    {identidade} em {AMBIENTE} ({GRANT_TYPE}, API {client.api_version})")
        for empresa, papeis in client.client_roles.items():
            print(f"    papéis na empresa {empresa}: {', '.join(papeis)}")
    if falhas:
        encerrar()


def consultar_resultado(client: SINMClient, chave: str) -> None:
    """Consulta a classificação (ONM) e o racional do cálculo de uma chave."""
    with etapa("Consulta da classificação (ONM)"):
        onm = client.consultar_classificacao(chave)
        print(f"    chave        : {chave}")
        print(f"    nível manejo : NM{onm.get('scoreFinal')}")
        print(f"    calculado em : {onm.get('dataCalculo')}")
        for inc in onm.get("inconsistencias") or []:
            print(f"    inconsistência: {inc.get('tipo')} — {inc.get('descricao')}")

    with etapa("Racional do cálculo"):
        try:
            imprimir_racional(client.consultar_racional(chave))
        except NotFoundError:
            print("    indisponível: o racional só existe para a classificação completa")


def imprimir_racional(r: dict) -> None:
    print(f"    nível manejo        : NM{r.get('scoreFinal')}")
    print(f"    regra determinante  : {r.get('regraDeterminante') or '—'}")
    print(f"    limitantes          : {', '.join(r.get('limitantesPrincipais') or []) or '—'}")
    print("    indicadores:")
    for ind in r.get("indicadores") or []:
        valor = ind.get("valor")
        detalhe = f" = {valor} {ind.get('unidade') or ''}".rstrip() if valor is not None else ""
        print(f"      - {ind.get('nome')} ({ind.get('origem')}){detalhe}: {ind.get('papelNaNota')}")
    for f in r.get("fatoresRestritivos") or []:
        print(f"    fator restritivo: {f.get('fator')} NM{f.get('scoreAntes')} → NM{f.get('scoreDepois')}")


def encerrar() -> None:
    """Sai com código 1 se alguma etapa falhou (útil em CI)."""
    if falhas:
        print(f"\n{falhas} etapa(s) com erro.", file=sys.stderr)
        sys.exit(1)
    print("\nConcluído sem erros.")
