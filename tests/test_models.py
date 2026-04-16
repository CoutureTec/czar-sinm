"""Testes unitários dos modelos (dataclasses e to_dict)."""

import pytest

from czarsinm import (
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
from czarsinm.models import _remove_none


# ---------------------------------------------------------------------------
# _remove_none
# ---------------------------------------------------------------------------

class TestRemoveNone:
    def test_remove_top_level_none(self):
        assert _remove_none({"a": 1, "b": None}) == {"a": 1}

    def test_preserve_falsy_non_none(self):
        result = _remove_none({"zero": 0, "vazio": "", "falso": False, "nulo": None})
        assert result == {"zero": 0, "vazio": "", "falso": False}

    def test_recursive_dict(self):
        d = {"outer": {"inner": None, "val": 42}}
        assert _remove_none(d) == {"outer": {"val": 42}}

    def test_list_with_dicts(self):
        d = {"items": [{"a": 1, "b": None}, {"a": 2}]}
        assert _remove_none(d) == {"items": [{"a": 1}, {"a": 2}]}

    def test_empty_dict(self):
        assert _remove_none({}) == {}


# ---------------------------------------------------------------------------
# Produtor
# ---------------------------------------------------------------------------

class TestProdutor:
    def test_to_dict(self, produtor):
        d = produtor.to_dict()
        assert d == {"nome": "Produtor Teste", "cpf": "68122528082"}


# ---------------------------------------------------------------------------
# Propriedade
# ---------------------------------------------------------------------------

class TestPropriedade:
    def test_to_dict_com_cnpj(self, propriedade):
        d = propriedade.to_dict()
        assert d["nome"] == "Fazenda Teste"
        assert d["cnpj"] == "54194116000138"
        assert "codigoCar" in d
        assert "codigoIbge" in d
        assert "poligono" in d

    def test_to_dict_sem_cnpj(self):
        p = Propriedade(
            nome="Fazenda",
            codigoCar="MT-0000000-AAA",
            codigoIbge="1234567",
            poligono="POLYGON ((0 0, 1 0, 0 0))",
        )
        d = p.to_dict()
        assert "cnpj" not in d


# ---------------------------------------------------------------------------
# Talhao
# ---------------------------------------------------------------------------

class TestTalhao:
    def test_to_dict(self, talhao):
        d = talhao.to_dict()
        assert d["area"] == 32.0
        assert d["tipoProdutor"] == "Proprietário"
        assert d["plantioContorno"] == 1
        assert "poligono" in d


# ---------------------------------------------------------------------------
# Manejo
# ---------------------------------------------------------------------------

class TestManejo:
    def test_to_dict_estrutura(self, manejo):
        d = manejo.to_dict()
        assert d["data"] == "2022-09-01"
        assert d["operacao"] == {"nomeOperacao": "Revolvimento do solo"}
        assert d["tipoOperacao"] == {"tipo": "ARAÇÃO"}


# ---------------------------------------------------------------------------
# CoberturaSolo
# ---------------------------------------------------------------------------

class TestCoberturaSolo:
    def test_to_dict(self):
        c = CoberturaSolo(dataAvaliacao="2023-01-01", porcentualPalhada=50)
        assert c.to_dict() == {"dataAvaliacao": "2023-01-01", "porcentualPalhada": 50}


# ---------------------------------------------------------------------------
# Producao
# ---------------------------------------------------------------------------

class TestProducao:
    def test_producao_passada_inclui_datas(self, producao_passada):
        d = producao_passada.to_dict()
        assert d["cultura"] == {"codigo": "001"}
        assert d["ilp"] is False
        assert d["dataPlantio"] == "2022-10-01"
        assert d["dataColheita"] == "2023-01-10"
        assert "dataPrevisaoPlantio" not in d
        assert "dataPrevisaoColheita" not in d

    def test_producao_futura_omite_datas_passadas(self, producao_futura):
        d = producao_futura.to_dict()
        assert d["dataPrevisaoPlantio"] == "2026-10-01"
        assert d["dataPrevisaoColheita"] == "2027-01-10"
        assert "dataPlantio" not in d
        assert "dataColheita" not in d

    def test_ilp_default_false(self):
        p = Producao(cultura=Cultura(codigo="001"))
        assert p.to_dict()["ilp"] is False


# ---------------------------------------------------------------------------
# DadoGleba
# ---------------------------------------------------------------------------

class TestDadoGleba:
    def test_to_dict_chaves_presentes(self, dado_gleba):
        d = dado_gleba.to_dict()
        assert set(d.keys()) == {"produtor", "propriedade", "talhao", "manejos", "coberturas", "producoes"}

    def test_manejos_e_producoes_sao_listas(self, dado_gleba):
        d = dado_gleba.to_dict()
        assert isinstance(d["manejos"], list)
        assert isinstance(d["producoes"], list)
        assert len(d["manejos"]) == 1
        assert len(d["producoes"]) == 2


# ---------------------------------------------------------------------------
# Amostra
# ---------------------------------------------------------------------------

class TestAmostra:
    def test_to_dict_sem_campos_opcionais(self, amostra):
        d = amostra.to_dict()
        assert "phcacl2" not in d
        assert "fosforoResina" not in d
        assert "areia" not in d
        assert "silte" not in d
        assert "argila" not in d
        assert "pontoColeta" not in d
        assert d["longitude"] == -47.108493
        assert d["latitude"] == -22.811532
        assert d["camada"] == "00_020"

    def test_to_dict_com_campos_opcionais(self, amostra):
        amostra.phcacl2 = 5.1
        amostra.fosforoResina = 2.3
        amostra.arilsulfatase = 100.0
        amostra.betaGlicosidade = 50.0
        amostra.densidadeSolo = 1.2
        d = amostra.to_dict()
        assert d["phcacl2"] == 5.1
        assert d["fosforoResina"] == 2.3
        assert d["arilsulfatase"] == 100.0
        assert d["betaGlicosidade"] == 50.0
        assert d["densidadeSolo"] == 1.2


# ---------------------------------------------------------------------------
# AnaliseSolo
# ---------------------------------------------------------------------------

class TestAnaliseSolo:
    def test_to_dict_com_cpf_e_cnpj(self, analise_solo):
        d = analise_solo.to_dict()
        assert d["cpfProdutor"] == "68122528082"
        assert d["cnpj"] == "54194116000138"
        assert isinstance(d["amostrasQuimicas"], list)
        assert len(d["amostrasQuimicas"]) == 1
        assert "amostrasFisicas" not in d

    def test_to_dict_sem_cpf_e_cnpj(self, amostra):
        a = AnaliseSolo(amostrasQuimicas=[amostra])
        d = a.to_dict()
        assert "cpfProdutor" not in d
        assert "cnpj" not in d


# ---------------------------------------------------------------------------
# Indice
# ---------------------------------------------------------------------------

class TestIndice:
    def test_to_dict(self):
        i = Indice(
            codigoSatelite="S01",
            longitude=-47.1,
            latitude=-22.8,
            data="2021-01-17",
            ndvi=0.5363,
            ndti=0.3363,
        )
        d = i.to_dict()
        assert d["codigoSatelite"] == "S01"
        assert d["longitude"] == -47.1
        assert d["latitude"] == -22.8
        assert d["ndvi"] == 0.5363
        assert d["ndti"] == 0.3363


# ---------------------------------------------------------------------------
# SensoriamentoRemoto
# ---------------------------------------------------------------------------

class TestSensoriamentoRemoto:
    def test_to_dict_chaves_obrigatorias(self, sensoriamento_remoto):
        d = sensoriamento_remoto.to_dict()
        for chave in ("dataInicial", "dataFinal", "declividadeMedia",
                      "plantioContorno", "terraceamento",
                      "codigoSateliteDeclividadeMedia", "indices"):
            assert chave in d

    def test_to_dict_campos_opcionais_presentes(self, sensoriamento_remoto):
        d = sensoriamento_remoto.to_dict()
        assert d["cpfProdutor"] == "68122528082"
        assert d["cnpj"] == "54194116000138"
        assert d["codigoSatelitePlantioContorno"] == "S08"
        assert d["codigoSateliteTerraceamento"] == "S07"

    def test_to_dict_sem_opcionais(self):
        sr = SensoriamentoRemoto(
            dataInicial="2021-01-01",
            dataFinal="2024-01-01",
            declividadeMedia=30,
            plantioContorno=0,
            terraceamento=0,
            codigoSateliteDeclividadeMedia="S09",
            indices=[
                Indice(
                    codigoSatelite="S01",
                    longitude=-47.1,
                    latitude=-22.8,
                    data="2021-01-17",
                    ndvi=0.5,
                    ndti=0.3,
                )
            ],
        )
        d = sr.to_dict()
        assert "cpfProdutor" not in d
        assert "cnpj" not in d
        assert "codigoSatelitePlantioContorno" not in d
        assert "codigoSateliteTerraceamento" not in d

    def test_interpretacoes_vazias_por_padrao(self):
        sr = SensoriamentoRemoto(
            dataInicial="2021-01-01",
            dataFinal="2024-01-01",
            declividadeMedia=30,
            plantioContorno=0,
            terraceamento=0,
            codigoSateliteDeclividadeMedia="S09",
            indices=[
                Indice("S01", 0.0, 0.0, "2021-01-01", 0.5, 0.3)
            ],
        )
        d = sr.to_dict()
        assert d["interpretacoesCoberturaSolo"] == []
        assert d["interpretacoesCultura"] == []
        assert d["interpretacoesManejo"] == []
