"""Testes unitários das exceções customizadas."""

import pytest

from czarnm.exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    PermissaoError,
    ValidationError,
    SINMError,
)


# ---------------------------------------------------------------------------
# Hierarquia de exceções
# ---------------------------------------------------------------------------

class TestHierarquia:
    def test_api_error_e_sinm_error(self):
        assert issubclass(APIError, SINMError)

    def test_authentication_error_e_sinm_error(self):
        assert issubclass(AuthenticationError, SINMError)

    def test_not_found_error_e_api_error(self):
        assert issubclass(NotFoundError, APIError)

    def test_validation_error_e_api_error(self):
        assert issubclass(ValidationError, APIError)

    def test_permissao_error_e_api_error(self):
        assert issubclass(PermissaoError, APIError)


# ---------------------------------------------------------------------------
# APIError
# ---------------------------------------------------------------------------

class TestAPIError:
    def test_atributos(self):
        err = APIError(500, "erro interno", {"detail": "falha"})
        assert err.status_code == 500
        assert err.body == {"detail": "falha"}
        assert "500" in str(err)

    def test_body_padrao_vazio(self):
        err = APIError(500, "erro")
        assert err.body == {}

    def test_format_report_contem_status(self):
        err = APIError(500, "erro interno")
        report = err.format_report()
        assert "500" in report
        assert "ERRO NA API SiNM" in report

    def test_format_report_com_title(self):
        err = APIError(422, "inválido", {"title": "Erro de validação"})
        report = err.format_report()
        assert "Erro de validação" in report

    def test_format_report_com_fields(self):
        err = APIError(422, "inválido", {
            "title": "Erro de validação",
            "fields": {"talhao.area": "deve ser positivo"},
        })
        report = err.format_report()
        assert "talhao.area" in report
        assert "deve ser positivo" in report

    def test_format_report_sem_estrutura_mostra_raw(self):
        err = APIError(503, "servico indisponivel", {"raw": "Service Unavailable"})
        report = err.format_report()
        assert "Service Unavailable" in report

    def test_format_report_tem_bordas(self):
        report = APIError(500, "x").format_report()
        assert report.startswith("╔")
        assert report.strip().endswith("╝")


# ---------------------------------------------------------------------------
# ValidationError
# ---------------------------------------------------------------------------

class TestValidationError:
    def test_herda_api_error(self):
        err = ValidationError(422, "inválido")
        assert isinstance(err, APIError)
        assert err.status_code == 422

    def test_format_report_com_errors(self):
        err = ValidationError(400, "campos inválidos", {
            "errors": {"produtor.cpf": "CPF inválido"}
        })
        report = err.format_report()
        assert "produtor.cpf" in report


# ---------------------------------------------------------------------------
# NotFoundError
# ---------------------------------------------------------------------------

class TestNotFoundError:
    def test_herda_api_error(self):
        err = NotFoundError(404, "não encontrado")
        assert isinstance(err, APIError)
        assert err.status_code == 404


# ---------------------------------------------------------------------------
# PermissaoError
# ---------------------------------------------------------------------------

class TestPermissaoError:
    def _make(self, roles_usuario=None, roles_necessarios=None, endpoint="/api/v1/glebas"):
        return PermissaoError(
            403,
            "Acesso negado",
            {},
            endpoint=endpoint,
            roles_usuario=roles_usuario or [],
            roles_necessarios=roles_necessarios or [],
        )

    def test_atributos(self):
        err = self._make(
            roles_usuario=["OPERADOR_CONTRATOS"],
            roles_necessarios=["ADMINISTRADOR", "OPERADOR_CONTRATOS"],
        )
        assert err.status_code == 403
        assert err.endpoint == "/api/v1/glebas"
        assert "OPERADOR_CONTRATOS" in err.roles_usuario
        assert "ADMINISTRADOR" in err.roles_necessarios

    def test_format_report_contem_cabecalho(self):
        report = self._make().format_report()
        assert "ACESSO NEGADO" in report
        assert "HTTP 403" in report

    def test_format_report_mostra_endpoint(self):
        report = self._make(endpoint="/api/v1/analises-solo/CHAVE").format_report()
        assert "/api/v1/analises-solo/CHAVE" in report

    def test_format_report_marca_role_faltando(self):
        err = self._make(
            roles_usuario=["OPERADOR_CONTRATOS"],
            roles_necessarios=["ADMINISTRADOR", "OPERADOR_CONTRATOS"],
        )
        report = err.format_report()
        assert "✗ ADMINISTRADOR" in report
        assert "✓" in report  # OPERADOR_CONTRATOS está presente

    def test_format_report_sem_roles_usuario(self):
        report = self._make(roles_usuario=[]).format_report()
        assert "nenhum role encontrado" in report

    def test_format_report_sem_roles_necessarios(self):
        report = self._make(roles_necessarios=[]).format_report()
        assert "não identificados" in report

    def test_format_report_solicita_role_quando_falta(self):
        err = self._make(
            roles_usuario=[],
            roles_necessarios=["OPERADOR_CONTRATOS"],
        )
        report = err.format_report()
        assert "Solicite" in report
