"""Testes unitários do SINMClient com HTTP mockado via `responses`."""

import json

import pytest
import responses as rsps_lib

from czarsinm import SINMClient
from czarsinm.client import API_URLS, _extrair_lista, _roles_para_endpoint
from czarsinm.exceptions import APIError, NotFoundError, PermissaoError, ValidationError

BASE = API_URLS["hml"]


# ---------------------------------------------------------------------------
# _extrair_lista
# ---------------------------------------------------------------------------

class TestExtrairLista:
    def test_lista_direta(self):
        assert _extrair_lista([1, 2, 3]) == [1, 2, 3]

    def test_lista_vazia(self):
        assert _extrair_lista([]) == []

    def test_hateoas_paged_model(self):
        resp = {
            "_embedded": {"glebaListagemModelList": [{"uuid": "a"}, {"uuid": "b"}]},
            "_links": {},
            "page": {"size": 20, "totalElements": 2},
        }
        result = _extrair_lista(resp)
        assert result == [{"uuid": "a"}, {"uuid": "b"}]

    def test_hateoas_embedded_vazio(self):
        resp = {"_embedded": {}, "_links": {}, "page": {}}
        assert _extrair_lista(resp) == []

    def test_dict_sem_embedded_retorna_dict(self):
        resp = {"uuid": "x"}
        assert _extrair_lista(resp) == {"uuid": "x"}


# ---------------------------------------------------------------------------
# _roles_para_endpoint
# ---------------------------------------------------------------------------

class TestRolesParaEndpoint:
    def test_glebas(self):
        roles = _roles_para_endpoint("/api/v1/glebas")
        assert "OPERADOR_CONTRATOS" in roles

    def test_analises_solo(self):
        roles = _roles_para_endpoint("/api/v1/analises-solo/CHAVE")
        assert "OPERADOR_ANALISE_SOLO" in roles

    def test_sensoriamentos_remotos(self):
        roles = _roles_para_endpoint("/api/v1/sensoriamentos-remotos/CHAVE")
        assert "OPERADOR_SENSORIAMENTO_REMOTO" in roles

    def test_classificacoes(self):
        roles = _roles_para_endpoint("/api/v1/classificacoes/CHAVE")
        assert "OPERADOR_CONTRATOS" in roles

    def test_endpoint_desconhecido(self):
        assert _roles_para_endpoint("/api/v1/desconhecido") == []

    def test_v2_tem_os_mesmos_roles_do_v1(self):
        """Autorização é idêntica nos dois contratos — só o payload muda."""
        assert _roles_para_endpoint("/api/v2/analises-solo/quimica") == \
            _roles_para_endpoint("/api/v1/analises-solo/quimica")
        assert "OPERADOR_SENSORIAMENTO_REMOTO" in _roles_para_endpoint(
            "/api/v2/sensoriamentos-remotos/CHAVE"
        )

    def test_disponiveis_aceita_analise_solo_ou_contratos(self):
        roles = _roles_para_endpoint("/api/v1/analises-solo/disponiveis")
        assert "OPERADOR_ANALISE_SOLO" in roles
        assert "OPERADOR_CONTRATOS" in roles


# ---------------------------------------------------------------------------
# __init__ — base_url por ambiente
# ---------------------------------------------------------------------------

class TestInit:
    def test_base_url_hml(self, client):
        assert client._base_url == BASE

    def test_base_url_prd(self, fake_token):
        from unittest.mock import MagicMock
        from czarsinm.auth import KeycloakAuth
        c = SINMClient(
            username="u", password="p", client_id="c", client_secret="s",
            ambiente="prd",
        )
        assert c._base_url == API_URLS["prd"]

    def test_base_url_customizada(self):
        c = SINMClient(
            username="u", password="p", client_id="c", client_secret="s",
            base_url="http://api.local",
        )
        assert c._base_url == "http://api.local"

    def test_base_url_strip_trailing_slash(self):
        c = SINMClient(
            username="u", password="p", client_id="c", client_secret="s",
            base_url="http://api.local/",
        )
        assert not c._base_url.endswith("/")


# ---------------------------------------------------------------------------
# Gleba
# ---------------------------------------------------------------------------

class TestCadastrarGleba:
    @rsps_lib.activate
    def test_post_para_endpoint_correto(self, client, dado_gleba):
        rsps_lib.add(
            rsps_lib.POST,
            f"{BASE}/api/v1/glebas",
            json={"uuid": "uuid-gleba-1", "chaveClassificacaoNM": "CHAVE001"},
            status=201,
        )
        result = client.cadastrar_gleba(dado_gleba)
        assert result["uuid"] == "uuid-gleba-1"
        assert result["chaveClassificacaoNM"] == "CHAVE001"

    @rsps_lib.activate
    def test_buscar_gleba(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/glebas/uuid-1", json={"uuid": "uuid-1"}, status=200)
        result = client.buscar_gleba("uuid-1")
        assert result["uuid"] == "uuid-1"

    @rsps_lib.activate
    def test_listar_glebas_lista_simples(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/glebas", json=[{"uuid": "a"}, {"uuid": "b"}], status=200)
        result = client.listar_glebas()
        assert len(result) == 2

    @rsps_lib.activate
    def test_listar_glebas_paged_model(self, client):
        paged = {
            "_embedded": {"glebaListagemModelList": [{"uuid": "a"}, {"uuid": "b"}]},
            "_links": {},
            "page": {"size": 20, "totalElements": 2, "totalPages": 1, "number": 0},
        }
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/glebas", json=paged, status=200)
        result = client.listar_glebas()
        assert result == [{"uuid": "a"}, {"uuid": "b"}]


# ---------------------------------------------------------------------------
# Análise de Solo
# ---------------------------------------------------------------------------

class TestCadastrarAnaliseSolo:
    @rsps_lib.activate
    def test_com_chave_usa_path_correto(self, client, analise_solo):
        rsps_lib.add(
            rsps_lib.POST,
            f"{BASE}/api/v1/analises-solo/CHAVE001",
            json={"uuid": "uuid-analise-1"},
            status=201,
        )
        result = client.cadastrar_analise_solo(analise_solo, chave_classificacao_nm="CHAVE001")
        assert result["uuid"] == "uuid-analise-1"
        assert rsps_lib.calls[0].request.url.endswith("/analises-solo/CHAVE001")

    @rsps_lib.activate
    def test_sem_chave_usa_path_base(self, client, analise_solo):
        rsps_lib.add(
            rsps_lib.POST,
            f"{BASE}/api/v1/analises-solo",
            json={"uuid": "uuid-analise-2"},
            status=201,
        )
        result = client.cadastrar_analise_solo(analise_solo)
        assert result["uuid"] == "uuid-analise-2"

    @rsps_lib.activate
    def test_listar_analises_solo(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/analises-solo", json=[], status=200)
        result = client.listar_analises_solo()
        assert result == []

    @rsps_lib.activate
    def test_payload_leva_cnpj_propriedade_canonico(self, client, analise_solo):
        rsps_lib.add(rsps_lib.POST, f"{BASE}/api/v1/analises-solo", json={}, status=201)
        client.cadastrar_analise_solo(analise_solo)
        enviado = json.loads(rsps_lib.calls[0].request.body)
        assert enviado["cnpjPropriedade"] == "54194116000138"
        assert "cnpj" not in enviado

    def test_combinado_recusado_no_v2(self, client_v2, analise_solo):
        with pytest.raises(ValueError, match="apenas no /api/v1"):
            client_v2.cadastrar_analise_solo(analise_solo)


# ---------------------------------------------------------------------------
# Análise de Solo por tipo (química / física)
# ---------------------------------------------------------------------------

class TestAnaliseSoloPorTipo:
    @rsps_lib.activate
    def test_cadastrar_quimica_com_chave(self, client, analise_solo_quimica):
        rsps_lib.add(
            rsps_lib.POST,
            f"{BASE}/api/v1/analises-solo/quimica/CHAVE001",
            json={"uuidAnaliseSolo": "uuid-q"},
            status=201,
        )
        result = client.cadastrar_analise_solo_quimica(
            analise_solo_quimica, chave_classificacao_nm="CHAVE001"
        )
        assert result["uuidAnaliseSolo"] == "uuid-q"

    @rsps_lib.activate
    def test_cadastrar_quimica_sem_chave(self, client, analise_solo_quimica):
        rsps_lib.add(rsps_lib.POST, f"{BASE}/api/v1/analises-solo/quimica", json={}, status=201)
        client.cadastrar_analise_solo_quimica(analise_solo_quimica)
        assert rsps_lib.calls[0].request.url.endswith("/analises-solo/quimica")

    @rsps_lib.activate
    def test_cadastrar_fisica_com_chave(self, client, analise_solo_fisica):
        rsps_lib.add(
            rsps_lib.POST,
            f"{BASE}/api/v1/analises-solo/fisica/CHAVE001",
            json={"uuidAnaliseSolo": "uuid-f"},
            status=201,
        )
        result = client.cadastrar_analise_solo_fisica(
            analise_solo_fisica, chave_classificacao_nm="CHAVE001"
        )
        assert result["uuidAnaliseSolo"] == "uuid-f"

    @rsps_lib.activate
    def test_buscar_quimica_e_fisica(self, client):
        rsps_lib.add(
            rsps_lib.GET, f"{BASE}/api/v1/analises-solo/quimica/uuid-q",
            json={"uuidAnaliseSolo": "uuid-q"}, status=200,
        )
        rsps_lib.add(
            rsps_lib.GET, f"{BASE}/api/v1/analises-solo/fisica/uuid-f",
            json={"uuidAnaliseSolo": "uuid-f"}, status=200,
        )
        assert client.buscar_analise_solo_quimica("uuid-q")["uuidAnaliseSolo"] == "uuid-q"
        assert client.buscar_analise_solo_fisica("uuid-f")["uuidAnaliseSolo"] == "uuid-f"

    @rsps_lib.activate
    def test_atualizar_quimica_usa_put(self, client, analise_solo_quimica):
        rsps_lib.add(
            rsps_lib.PUT, f"{BASE}/api/v1/analises-solo/quimica/uuid-q", json={}, status=200
        )
        client.atualizar_analise_solo_quimica("uuid-q", analise_solo_quimica)
        assert rsps_lib.calls[0].request.method == "PUT"

    @rsps_lib.activate
    def test_listar_por_tipo(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/analises-solo/quimica", json=[], status=200)
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/analises-solo/fisica", json=[], status=200)
        assert client.listar_analises_solo_quimicas() == []
        assert client.listar_analises_solo_fisicas() == []

    @rsps_lib.activate
    def test_buscar_analise_solo_depreciado_delega_para_quimica(self, client):
        rsps_lib.add(
            rsps_lib.GET, f"{BASE}/api/v1/analises-solo/quimica/uuid-q",
            json={"uuidAnaliseSolo": "uuid-q"}, status=200,
        )
        with pytest.deprecated_call():
            result = client.buscar_analise_solo("uuid-q")
        assert result["uuidAnaliseSolo"] == "uuid-q"


# ---------------------------------------------------------------------------
# Contrato v2 (api_version='v2')
# ---------------------------------------------------------------------------

class TestApiVersionV2:
    def test_api_version_default_e_v1(self, client):
        assert client.api_version == "v1"

    def test_api_version_invalida(self):
        with pytest.raises(ValueError, match="api_version"):
            SINMClient(
                username="u", password="p", client_id="c", client_secret="s",
                api_version="v9",
            )

    @rsps_lib.activate
    def test_quimica_vai_para_a_rota_v2_com_payload_limpo(self, client_v2, analise_solo_quimica):
        rsps_lib.add(rsps_lib.POST, f"{BASE}/api/v2/analises-solo/quimica", json={}, status=201)
        client_v2.cadastrar_analise_solo_quimica(analise_solo_quimica)
        req = rsps_lib.calls[0].request
        assert "/api/v2/analises-solo/quimica" in req.url
        enviado = json.loads(req.body)
        assert enviado["cnpjLaboratorio"] == "13610724000107"
        assert "cnpj" not in enviado

    def test_quimica_sem_laboratorio_falha_antes_da_chamada(self, client_v2, amostra):
        from czarsinm import AnaliseSoloQuimica
        analise = AnaliseSoloQuimica(amostrasQuimicas=[amostra], cpfProdutor="68122528082")
        with pytest.raises(ValueError, match="cnpjLaboratorio"):
            client_v2.cadastrar_analise_solo_quimica(analise)

    @rsps_lib.activate
    def test_sensoriamento_vai_para_a_rota_v2(self, client_v2, sensoriamento_remoto):
        rsps_lib.add(
            rsps_lib.POST,
            f"{BASE}/api/v2/sensoriamentos-remotos/CHAVE001",
            json={},
            status=201,
        )
        client_v2.cadastrar_sensoriamento_remoto(
            sensoriamento_remoto, chave_classificacao_nm="CHAVE001"
        )
        assert "/api/v2/sensoriamentos-remotos/CHAVE001" in rsps_lib.calls[0].request.url

    @rsps_lib.activate
    def test_gleba_vai_para_a_rota_v2_com_cultura_alvo(self, client_v2, dado_gleba):
        rsps_lib.add(rsps_lib.POST, f"{BASE}/api/v2/glebas", json={}, status=201)
        client_v2.cadastrar_gleba(dado_gleba)
        assert rsps_lib.calls[0].request.url.endswith("/api/v2/glebas")
        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["culturaAlvo"]["cultura"]["codigo"] == "001"
        assert all("dataPrevisaoPlantio" not in p for p in body["producoes"])

    @rsps_lib.activate
    def test_atualizar_buscar_listar_gleba_no_v2(self, client_v2, dado_gleba):
        rsps_lib.add(rsps_lib.PUT, f"{BASE}/api/v2/glebas/U1", json={}, status=200)
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v2/glebas/U1", json={}, status=200)
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v2/glebas", json=[], status=200)
        client_v2.atualizar_gleba("U1", dado_gleba)
        client_v2.buscar_gleba("U1")
        client_v2.listar_glebas()
        assert [c.request.method for c in rsps_lib.calls] == ["PUT", "GET", "GET"]
        assert all("/api/v2/glebas" in c.request.url for c in rsps_lib.calls)

    @rsps_lib.activate
    def test_classificacao_permanece_no_v1(self, client_v2):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/classificacoes/CH", json={}, status=200)
        client_v2.consultar_classificacao("CH")
        assert "/api/v1/classificacoes/CH" in rsps_lib.calls[0].request.url

    @rsps_lib.activate
    def test_disponiveis_permanece_no_v1(self, client_v2):
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE}/api/v1/analises-solo/disponiveis",
            json={"analisesQuimicas": [], "analisesFisicas": []},
            status=200,
        )
        client_v2.consultar_analises_disponiveis("68122528082")
        assert "/api/v1/analises-solo/disponiveis" in rsps_lib.calls[0].request.url

    @rsps_lib.activate
    def test_listar_analises_solo_no_v2_cai_na_quimica(self, client_v2):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v2/analises-solo/quimica", json=[], status=200)
        assert client_v2.listar_analises_solo() == []


# ---------------------------------------------------------------------------
# Análises disponíveis por CPF (v6.2026: resposta com uuidAnaliseSolo)
# ---------------------------------------------------------------------------

class TestConsultarAnalisesDisponiveis:
    RESPOSTA = {
        "analisesQuimicas": [
            {
                "uuidAnaliseSolo": "4b2f8c1a-9e3d-4a77-8f10-2c5b6d7e8f90",
                "validaAte": "2028-01-01",
                "valida": True,
                "motivoInvalidade": None,
            }
        ],
        "analisesFisicas": [
            {
                "uuidAnaliseSolo": "7d1e4b0c-2a58-4f93-b6c4-1e9f3a8d5c27",
                "validaAte": "2036-01-01",
                "valida": True,
                "motivoInvalidade": None,
            }
        ],
    }

    @rsps_lib.activate
    def test_manda_o_cpf_como_query_param(self, client):
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE}/api/v1/analises-solo/disponiveis",
            json=self.RESPOSTA,
            status=200,
        )
        result = client.consultar_analises_disponiveis("68122528082")
        assert "cpf=68122528082" in rsps_lib.calls[0].request.url
        assert "dataReferencia" not in rsps_lib.calls[0].request.url
        assert result["analisesQuimicas"][0]["uuidAnaliseSolo"].startswith("4b2f8c1a")
        assert result["analisesFisicas"][0]["validaAte"] == "2036-01-01"

    @rsps_lib.activate
    def test_data_referencia_opcional(self, client):
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE}/api/v1/analises-solo/disponiveis",
            json=self.RESPOSTA,
            status=200,
        )
        client.consultar_analises_disponiveis("68122528082", data_referencia="2026-08-04")
        url = rsps_lib.calls[0].request.url
        assert "dataReferencia=2026-08-04" in url

    @rsps_lib.activate
    def test_uuid_da_listagem_serve_para_buscar_a_analise(self, client):
        """O uuid devolvido endereça a análise no endpoint do tipo correspondente."""
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE}/api/v1/analises-solo/disponiveis",
            json=self.RESPOSTA,
            status=200,
        )
        uuid_quimica = self.RESPOSTA["analisesQuimicas"][0]["uuidAnaliseSolo"]
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE}/api/v1/analises-solo/quimica/{uuid_quimica}",
            json={"uuidAnaliseSolo": uuid_quimica},
            status=200,
        )
        disponiveis = client.consultar_analises_disponiveis("68122528082")
        uuid = disponiveis["analisesQuimicas"][0]["uuidAnaliseSolo"]
        assert client.buscar_analise_solo_quimica(uuid)["uuidAnaliseSolo"] == uuid

    @rsps_lib.activate
    def test_403_reporta_os_dois_roles_aceitos(self, client):
        rsps_lib.add(
            rsps_lib.GET, f"{BASE}/api/v1/analises-solo/disponiveis", json={}, status=403
        )
        with pytest.raises(PermissaoError) as exc_info:
            client.consultar_analises_disponiveis("68122528082")
        assert "OPERADOR_ANALISE_SOLO" in exc_info.value.roles_necessarios
        assert "OPERADOR_CONTRATOS" in exc_info.value.roles_necessarios


# ---------------------------------------------------------------------------
# Sensoriamento Remoto
# ---------------------------------------------------------------------------

class TestCadastrarSensoriamentoRemoto:
    @rsps_lib.activate
    def test_post_para_endpoint_com_chave(self, client, sensoriamento_remoto):
        rsps_lib.add(
            rsps_lib.POST,
            f"{BASE}/api/v1/sensoriamentos-remotos/CHAVE001",
            json={"uuid": "uuid-sr-1"},
            status=201,
        )
        result = client.cadastrar_sensoriamento_remoto(sensoriamento_remoto, chave_classificacao_nm="CHAVE001")
        assert result["uuid"] == "uuid-sr-1"

    @rsps_lib.activate
    def test_listar_sensoriamentos(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/sensoriamentos-remotos", json=[], status=200)
        assert client.listar_sensoriamentos_remotos() == []

    @rsps_lib.activate
    def test_payload_leva_cnpj_propriedade_canonico(self, client, sensoriamento_remoto):
        rsps_lib.add(
            rsps_lib.POST, f"{BASE}/api/v1/sensoriamentos-remotos/CHAVE001", json={}, status=201
        )
        client.cadastrar_sensoriamento_remoto(sensoriamento_remoto, "CHAVE001")
        enviado = json.loads(rsps_lib.calls[0].request.body)
        assert enviado["cnpjPropriedade"] == "54194116000138"
        assert "cnpj" not in enviado

    @rsps_lib.activate
    def test_atualizar_usa_put(self, client, sensoriamento_remoto):
        rsps_lib.add(
            rsps_lib.PUT, f"{BASE}/api/v1/sensoriamentos-remotos/uuid-sr", json={}, status=200
        )
        client.atualizar_sensoriamento_remoto("uuid-sr", sensoriamento_remoto)
        assert rsps_lib.calls[0].request.method == "PUT"

    @rsps_lib.activate
    def test_remover_204_retorna_dict_vazio(self, client):
        rsps_lib.add(
            rsps_lib.DELETE, f"{BASE}/api/v1/sensoriamentos-remotos/uuid-sr", body=b"", status=204
        )
        assert client.remover_sensoriamento_remoto("uuid-sr") == {}


# ---------------------------------------------------------------------------
# Classificação
# ---------------------------------------------------------------------------

class TestConsultarClassificacao:
    @rsps_lib.activate
    def test_get_com_chave(self, client):
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE}/api/v1/classificacoes/CHAVE001",
            json={"nivelManejo": "B", "chave": "CHAVE001"},
            status=200,
        )
        result = client.consultar_classificacao("CHAVE001")
        assert result["nivelManejo"] == "B"

    @rsps_lib.activate
    def test_nao_encontrado_levanta_not_found_error(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/classificacoes/CHAVE999", status=404)
        with pytest.raises(NotFoundError):
            client.consultar_classificacao("CHAVE999")

    @rsps_lib.activate
    def test_listar_classificacoes(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/classificacoes", json=[], status=200)
        assert client.listar_classificacoes() == []


# ---------------------------------------------------------------------------
# _handle_response — tratamento de status HTTP
# ---------------------------------------------------------------------------

class TestHandleResponse:
    @rsps_lib.activate
    def test_200_retorna_json(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/glebas", json={"ok": True}, status=200)
        assert client.listar_glebas() == {"ok": True}

    @rsps_lib.activate
    def test_204_retorna_dict_vazio(self, client, dado_gleba):
        rsps_lib.add(rsps_lib.POST, f"{BASE}/api/v1/glebas", body=b"", status=204)
        result = client.cadastrar_gleba(dado_gleba)
        assert result == {}

    @rsps_lib.activate
    def test_400_levanta_validation_error(self, client, dado_gleba):
        rsps_lib.add(
            rsps_lib.POST,
            f"{BASE}/api/v1/glebas",
            json={"title": "Erro de validação", "fields": {"talhao.area": "deve ser positivo"}},
            status=400,
        )
        with pytest.raises(ValidationError) as exc_info:
            client.cadastrar_gleba(dado_gleba)
        assert exc_info.value.status_code == 400

    @rsps_lib.activate
    def test_422_levanta_validation_error(self, client, dado_gleba):
        rsps_lib.add(rsps_lib.POST, f"{BASE}/api/v1/glebas", json={}, status=422)
        with pytest.raises(ValidationError):
            client.cadastrar_gleba(dado_gleba)

    @rsps_lib.activate
    def test_403_levanta_permissao_error_com_roles(self, client, dado_gleba):
        rsps_lib.add(rsps_lib.POST, f"{BASE}/api/v1/glebas", json={}, status=403)
        with pytest.raises(PermissaoError) as exc_info:
            client.cadastrar_gleba(dado_gleba)
        err = exc_info.value
        assert err.status_code == 403
        assert "OPERADOR_CONTRATOS" in err.roles_necessarios
        # roles do usuário vêm do mock de auth
        assert "OPERADOR_CONTRATOS" in err.roles_usuario

    @rsps_lib.activate
    def test_404_levanta_not_found_error(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/glebas/inexistente", status=404)
        with pytest.raises(NotFoundError):
            client.buscar_gleba("inexistente")

    @rsps_lib.activate
    def test_500_levanta_api_error(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/glebas", status=500)
        with pytest.raises(APIError) as exc_info:
            client.listar_glebas()
        assert exc_info.value.status_code == 500

    @rsps_lib.activate
    def test_erro_conexao_levanta_api_error(self, client):
        import requests
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/glebas", body=requests.ConnectionError("timeout"))
        with pytest.raises(APIError, match="conexão"):
            client.listar_glebas()

    @rsps_lib.activate
    def test_corpo_erro_como_lista_levanta_api_error(self, client):
        """Corpo de erro em formato de lista (não dict) não deve causar AttributeError."""
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE}/api/v1/glebas",
            json=[{"campo": "gleba", "mensagem": "inválido"}],
            status=400,
        )
        with pytest.raises(APIError) as exc_info:
            client.listar_glebas()
        assert exc_info.value.status_code == 400
