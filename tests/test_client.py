"""Testes unitários do SINMClient com HTTP mockado via `responses`."""

import pytest
import responses as rsps_lib

from czarsinm import SINMClient
from czarsinm.client import API_URLS, _roles_para_endpoint
from czarsinm.exceptions import APIError, NotFoundError, PermissaoError, ValidationError

BASE = API_URLS["hml"]


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
    def test_listar_glebas(self, client):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/api/v1/glebas", json=[{"uuid": "a"}, {"uuid": "b"}], status=200)
        result = client.listar_glebas()
        assert len(result) == 2


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
