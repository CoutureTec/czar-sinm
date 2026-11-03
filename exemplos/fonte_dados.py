"""
Fonte de dados dos exemplos.

Os exemplos (exemplo_v1.py e exemplo_v2.py) não sabem de onde vêm os dados.
Eles recebem uma lista de *registros* — um dict por gleba, no formato de
dados/glebas.json — e usam `montar()` para convertê-los nos modelos do SDK.

Há duas fontes prontas, escolhidas pela configuração SINM_FONTE:

  json → dados/glebas.json    um arquivo com todos os dados de cada gleba
  csv  → dados/csv/           uma tabela por assunto, ligadas por idExterno

Para ler de outro lugar (banco de dados, planilha, ERP), escreva uma função
que receba um caminho/conexão e devolva registros nesse mesmo formato, e
registre-a em FONTES. Exemplo com um banco de dados:

    def carregar_banco(dsn: str) -> list:
        with psycopg.connect(dsn) as conn:
            registros = []
            for linha in conn.execute("SELECT ... FROM talhoes"):
                registros.append({"idExterno": linha.id, "produtor": {...}, ...})
            return registros

    FONTES["banco"] = carregar_banco
"""

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from czarsinm import (
    AmostraFisica,
    AmostraQuimica,
    AnaliseSolo,
    CoberturaSolo,
    Cultura,
    CulturaAlvo,
    DadoGleba,
    Indice,
    InterpretacaoCoberturaSolo,
    InterpretacaoCultura,
    InterpretacaoManejo,
    Manejo,
    Operacao,
    Producao,
    Produtor,
    Propriedade,
    SensoriamentoRemoto,
    Talhao,
    TipoOperacao,
)


# --------------------------------------------------------------------------
# Fonte JSON — o arquivo já está no formato do registro
# --------------------------------------------------------------------------

def carregar_json(caminho: str) -> list:
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


# --------------------------------------------------------------------------
# Fonte CSV — uma tabela por assunto, como num banco de dados
# --------------------------------------------------------------------------

# O CSV só guarda texto: estas colunas são convertidas para número/booleano.
_INTEIROS = {"plantioContorno", "terraceamento", "declividadeMedia", "porcentualPalhada"}
_BOOLEANOS = {"ilp"}
_TEXTOS = {
    "idExterno", "cpfResponsavelColeta", "dataColeta", "camada", "codigoSatelite", "data",
    "dataAvaliacao", "tipoCultivo", "dataInicio", "dataFim", "operacao", "tipoOperacao",
    "codigoCultura", "dataPlantio", "dataColheita", "cultura",
}


def _valor(coluna: str, texto: str):
    if coluna in _BOOLEANOS:
        return texto.strip().lower() in ("true", "sim", "1")
    if coluna in _INTEIROS:
        return int(texto)
    if coluna in _TEXTOS:
        return texto
    try:
        return float(texto)
    except ValueError:
        return texto


def _ler_tabela(pasta: Path, arquivo: str) -> dict:
    """Linhas do CSV agrupadas por idExterno; colunas vazias ficam de fora."""
    por_gleba = defaultdict(list)
    caminho = pasta / arquivo
    if not caminho.exists():
        return por_gleba
    with open(caminho, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            id_externo = linha.pop("idExterno")
            por_gleba[id_externo].append(
                {coluna: _valor(coluna, texto) for coluna, texto in linha.items() if texto != ""}
            )
    return por_gleba


def carregar_csv(pasta: str) -> list:
    pasta = Path(pasta)
    tabelas = {
        nome: _ler_tabela(pasta, f"{nome}.csv")
        for nome in (
            "manejos", "coberturas", "producoes", "amostras_quimicas", "amostras_fisicas",
            "sensoriamento", "indices", "interpretacoes_cobertura", "interpretacoes_cultura",
            "interpretacoes_manejo",
        )
    }

    registros = []
    with open(pasta / "glebas.csv", encoding="utf-8", newline="") as f:
        for g in csv.DictReader(f):
            id_externo = g["idExterno"]
            filhos = {nome: tabela.get(id_externo, []) for nome, tabela in tabelas.items()}
            sensoriamento = (filhos["sensoriamento"] or [{}])[0]
            registros.append({
                "idExterno": id_externo,
                "produtor": {"nome": g["produtorNome"], "cpf": g["produtorCpf"]},
                "propriedade": {
                    "nome": g["propriedadeNome"],
                    "cnpj": g["propriedadeCnpj"],
                    "codigoCar": g["codigoCar"],
                    "codigoIbge": g["codigoIbge"],
                    "poligono": g["propriedadePoligono"],
                },
                "talhao": {
                    "poligono": g["talhaoPoligono"],
                    "area": float(g["area"]),
                    "tipoProdutor": g["tipoProdutor"],
                    "plantioContorno": int(g["plantioContorno"]) if g["plantioContorno"] else None,
                    "cnpjOperador": g["cnpjOperador"] or None,
                },
                "culturaAlvo": {
                    "cultura": g["culturaAlvo"],
                    "dataPrevisaoPlantio": g["dataPrevisaoPlantio"],
                    "dataPrevisaoColheita": g["dataPrevisaoColheita"],
                },
                "manejos": filhos["manejos"],
                "coberturas": filhos["coberturas"],
                "producoes": filhos["producoes"],
                "analiseSolo": {
                    "cnpjLaboratorio": g["cnpjLaboratorio"] or None,
                    "tipoAmostragem": g["tipoAmostragem"] or None,
                    "amostrasQuimicas": filhos["amostras_quimicas"],
                    "amostrasFisicas": filhos["amostras_fisicas"],
                },
                "sensoriamentoRemoto": {
                    **sensoriamento,
                    "indices": filhos["indices"],
                    "interpretacoesCoberturaSolo": filhos["interpretacoes_cobertura"],
                    "interpretacoesCultura": filhos["interpretacoes_cultura"],
                    "interpretacoesManejo": filhos["interpretacoes_manejo"],
                },
            })
    return registros


# Fontes disponíveis (SINM_FONTE) e o caminho padrão de cada uma.
FONTES = {
    "json": carregar_json,
    "csv": carregar_csv,
}
CAMINHOS_PADRAO = {
    "json": "dados/glebas.json",
    "csv": "dados/csv",
}


# --------------------------------------------------------------------------
# Registro → modelos do SDK
# --------------------------------------------------------------------------

@dataclass
class Envio:
    """O que cada gleba envia à API, já nos modelos do SDK."""
    id_externo: str
    gleba: DadoGleba
    analise_solo: AnaliseSolo
    sensoriamento: SensoriamentoRemoto


def montar(registro: dict, cnpj_operador: str, cnpj_laboratorio: Optional[str]) -> Envio:
    """Converte um registro nos modelos do SDK.

    `cnpj_operador` e `cnpj_laboratorio` preenchem os campos que o registro
    deixar vazios (nos dados de exemplo, a própria empresa autenticada).
    """
    produtor = registro["produtor"]
    propriedade = registro["propriedade"]
    talhao = registro["talhao"]
    alvo = registro["culturaAlvo"]
    analise = registro["analiseSolo"]
    sr = dict(registro["sensoriamentoRemoto"])

    gleba = DadoGleba(
        produtor=Produtor(**produtor),
        propriedade=Propriedade(**propriedade),
        talhao=Talhao(
            **{**talhao, "cnpjOperador": talhao.get("cnpjOperador") or cnpj_operador},
            idExterno=registro["idExterno"],
        ),
        manejos=[
            Manejo(
                data=m["data"],
                operacao=Operacao(nomeOperacao=m["operacao"]),
                tipoOperacao=TipoOperacao(tipo=m["tipoOperacao"]) if m.get("tipoOperacao") else None,
            )
            for m in registro["manejos"]
        ],
        coberturas=[CoberturaSolo(**c) for c in registro["coberturas"]],
        producoes=[
            Producao(
                cultura=Cultura(codigo=p["codigoCultura"]),
                ilp=p.get("ilp", False),
                dataPlantio=p.get("dataPlantio"),
                dataColheita=p.get("dataColheita"),
            )
            for p in registro["producoes"]
        ],
        culturaAlvo=CulturaAlvo.de_nome(
            alvo["cultura"], alvo["dataPrevisaoPlantio"], alvo["dataPrevisaoColheita"]
        ),
    )

    analise_solo = AnaliseSolo(
        cpfProdutor=produtor["cpf"],
        cnpjPropriedade=propriedade["cnpj"],
        cnpjLaboratorio=analise.get("cnpjLaboratorio") or cnpj_laboratorio,
        tipoAmostragem=analise.get("tipoAmostragem"),
        amostrasQuimicas=[AmostraQuimica(**a) for a in analise["amostrasQuimicas"]],
        amostrasFisicas=[AmostraFisica(**a) for a in analise.get("amostrasFisicas", [])],
    )

    sensoriamento = SensoriamentoRemoto(
        cpfProdutor=produtor["cpf"],
        cnpjPropriedade=propriedade["cnpj"],
        indices=[Indice(**i) for i in sr.pop("indices")],
        interpretacoesCoberturaSolo=[
            InterpretacaoCoberturaSolo(**i) for i in sr.pop("interpretacoesCoberturaSolo", [])
        ],
        interpretacoesCultura=[InterpretacaoCultura(**i) for i in sr.pop("interpretacoesCultura", [])],
        interpretacoesManejo=[InterpretacaoManejo(**i) for i in sr.pop("interpretacoesManejo", [])],
        **sr,
    )

    return Envio(registro["idExterno"], gleba, analise_solo, sensoriamento)
