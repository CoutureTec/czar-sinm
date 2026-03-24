"""Testes unitários do módulo de autenticação Keycloak."""

import base64
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from czarsinm.auth import KeycloakAuth, KEYCLOAK_BASE, REALMS
from czarsinm.exceptions import AuthenticationError


def _make_token_response(roles=None, client_id="client-id", expires_in=300, refresh_expires_in=1800):
    """Constrói uma resposta de token Keycloak fake com roles como client roles."""
    payload = {"resource_access": {client_id: {"roles": roles or []}}, "sub": "user-123"}
    b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    access_token = f"header.{b64}.sig"
    return {
        "access_token": access_token,
        "refresh_token": "refresh-token-fake",
        "expires_in": expires_in,
        "refresh_expires_in": refresh_expires_in,
    }


def _make_auth(**kwargs) -> KeycloakAuth:
    defaults = dict(
        username="user@test.br",
        password="senha",
        client_id="client-id",
        client_secret="client-secret",
        ambiente="hml",
    )
    defaults.update(kwargs)
    return KeycloakAuth(**defaults)


# ---------------------------------------------------------------------------
# _decode_client_roles
# ---------------------------------------------------------------------------

class TestDecodeClientRoles:
    def test_extrai_roles_do_jwt(self):
        roles = ["OPERADOR_CONTRATOS", "BETA_USER"]
        payload = {"resource_access": {"client-id": {"roles": roles}}}
        b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"header.{b64}.sig"
        assert KeycloakAuth._decode_client_roles(token) == {"client-id": roles}

    def test_multiplos_clients(self):
        payload = {
            "resource_access": {
                "client-a": {"roles": ["ROLE_A"]},
                "client-b": {"roles": ["ROLE_B1", "ROLE_B2"]},
            }
        }
        b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"header.{b64}.sig"
        result = KeycloakAuth._decode_client_roles(token)
        assert result == {"client-a": ["ROLE_A"], "client-b": ["ROLE_B1", "ROLE_B2"]}

    def test_token_invalido_retorna_dict_vazio(self):
        assert KeycloakAuth._decode_client_roles("nao.e.um.jwt") == {}

    def test_token_vazio_retorna_dict_vazio(self):
        assert KeycloakAuth._decode_client_roles("") == {}

    def test_sem_resource_access_retorna_dict_vazio(self):
        payload = {"sub": "user"}
        b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"header.{b64}.sig"
        assert KeycloakAuth._decode_client_roles(token) == {}

    def test_padding_jwt_irregular(self):
        """Tokens JWT com payload de tamanho variável precisam de padding extra."""
        roles = ["ADMIN"]
        payload = {"resource_access": {"my-client": {"roles": roles}}, "extra": "x" * 5}
        b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"h.{b64}.s"
        assert KeycloakAuth._decode_client_roles(token) == {"my-client": roles}


# ---------------------------------------------------------------------------
# __init__ — construção da token_url
# ---------------------------------------------------------------------------

class TestInit:
    def test_token_url_hml(self):
        auth = _make_auth(ambiente="hml")
        assert f"{KEYCLOAK_BASE}/{REALMS['hml']}/protocol/openid-connect/token" == auth._token_url

    def test_token_url_prd(self):
        auth = _make_auth(ambiente="prd")
        assert REALMS["prd"] in auth._token_url

    def test_token_url_customizada(self):
        auth = _make_auth(keycloak_url="http://keycloak.local/realms")
        assert auth._token_url.startswith("http://keycloak.local/realms")

    def test_credenciais_armazenadas(self):
        auth = _make_auth()
        assert auth._credentials["username"] == "user@test.br"
        assert auth._credentials["grant_type"] == "password"


# ---------------------------------------------------------------------------
# _authenticate
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_sucesso(self):
        auth = _make_auth()
        token_resp = _make_token_response(roles=["OPERADOR_CONTRATOS"])
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = token_resp

        with patch("czarsinm.auth.requests.post", return_value=mock_resp) as mock_post:
            auth._authenticate()

        mock_post.assert_called_once()
        assert auth._access_token == token_resp["access_token"]
        assert auth._refresh_token == "refresh-token-fake"
        assert auth._expires_at > time.time()

    def test_falha_http_levanta_authentication_error(self):
        auth = _make_auth()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        with patch("czarsinm.auth.requests.post", return_value=mock_resp):
            with pytest.raises(AuthenticationError, match="401"):
                auth._authenticate()

    def test_erro_conexao_levanta_authentication_error(self):
        import requests as req
        auth = _make_auth()
        with patch("czarsinm.auth.requests.post", side_effect=req.ConnectionError("timeout")):
            with pytest.raises(AuthenticationError, match="Keycloak"):
                auth._authenticate()


# ---------------------------------------------------------------------------
# _parse_token_response
# ---------------------------------------------------------------------------

class TestParseTokenResponse:
    def test_seta_token_e_expiracao(self):
        auth = _make_auth()
        now = time.time()
        data = _make_token_response(expires_in=300, refresh_expires_in=1800)
        auth._parse_token_response(data)

        assert auth._access_token == data["access_token"]
        assert auth._refresh_token == "refresh-token-fake"
        assert auth._expires_at >= now + 299
        assert auth._refresh_expires_at >= now + 1799


# ---------------------------------------------------------------------------
# token (property) — cache
# ---------------------------------------------------------------------------

class TestTokenProperty:
    def test_usa_token_em_cache(self):
        auth = _make_auth()
        token_data = _make_token_response()
        auth._access_token = token_data["access_token"]
        auth._expires_at = time.time() + 600  # válido por mais 10 min

        with patch.object(auth, "_authenticate") as mock_auth:
            _ = auth.token
            mock_auth.assert_not_called()

    def test_autentica_quando_sem_token(self):
        auth = _make_auth()
        token_data = _make_token_response()

        with patch.object(auth, "_authenticate", side_effect=lambda: auth._parse_token_response(token_data)):
            tok = auth.token
            assert tok == token_data["access_token"]

    def test_usa_refresh_quando_disponivel(self):
        auth = _make_auth()
        token_data = _make_token_response()
        auth._access_token = None
        auth._expires_at = 0
        auth._refresh_token = "valid-refresh"
        auth._refresh_expires_at = time.time() + 600

        with patch.object(auth, "_refresh", side_effect=lambda: auth._parse_token_response(token_data)) as mock_ref:
            _ = auth.token
            mock_ref.assert_called_once()


# ---------------------------------------------------------------------------
# auth_header e roles
# ---------------------------------------------------------------------------

class TestAuthHeaderERoles:
    def test_auth_header_formato(self):
        auth = _make_auth()
        token_data = _make_token_response(roles=["OPERADOR_CONTRATOS"])
        with patch.object(auth, "_authenticate", side_effect=lambda: auth._parse_token_response(token_data)):
            header = auth.auth_header
        assert header["Authorization"].startswith("Bearer ")

    def test_client_roles_extraidos_do_token(self):
        auth = _make_auth()
        token_data = _make_token_response(roles=["BETA_USER", "OPERADOR_CONTRATOS"], client_id="client-id")
        with patch.object(auth, "_authenticate", side_effect=lambda: auth._parse_token_response(token_data)):
            client_roles = auth.client_roles
        assert "client-id" in client_roles
        assert "BETA_USER" in client_roles["client-id"]
        assert "OPERADOR_CONTRATOS" in client_roles["client-id"]
