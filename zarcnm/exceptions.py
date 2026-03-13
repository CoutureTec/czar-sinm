"""Exceções customizadas do cliente ZARC-NM."""

from __future__ import annotations
from typing import Optional


class ZarcNMError(Exception):
    """Classe base para erros do cliente ZARC-NM."""


class AuthenticationError(ZarcNMError):
    """Erro de autenticação no Keycloak."""


class APIError(ZarcNMError):
    """Erro retornado pela API ZARC-NM."""

    def __init__(self, status_code: int, message: str, body: Optional[dict] = None):
        self.status_code = status_code
        self.body = body or {}
        super().__init__(f"HTTP {status_code}: {message}")

    def format_report(self) -> str:
        """Formata o erro da API como um relatório legível."""
        W = 62
        lines = []

        def row(text: str = "") -> str:
            return f"║  {text:<{W - 4}}║"

        def divider(left: str = "╠", right: str = "╣") -> str:
            return f"{left}{'═' * (W - 2)}{right}"

        lines.append(f"╔{'═' * (W - 2)}╗")
        lines.append(row("ERRO NA API ZARC-NM"))
        lines.append(divider())
        lines.append(row(f"Status   : {self.status_code}"))

        b = self.body
        if b.get("codigoErro"):
            lines.append(row(f"Código   : {b['codigoErro']}"))
        if b.get("title"):
            lines.append(row(f"Título   : {b['title']}"))
        if b.get("instance"):
            lines.append(row(f"Endpoint : {b['instance']}"))

        # Campos com erro (validação)
        fields = b.get("fields") or b.get("errors") or {}
        if fields:
            lines.append(divider())
            lines.append(row("Campos com erro:"))
            for field, msg in fields.items():
                entry = f"  • {field}"
                entry_fmt = f"{entry:<42} → {msg}"
                # quebra linha se muito longo
                if len(entry_fmt) > W - 4:
                    lines.append(row(f"  • {field}"))
                    lines.append(row(f"    → {msg}"))
                else:
                    lines.append(row(entry_fmt))
        elif not b.get("title"):
            # sem estrutura conhecida — mostra mensagem bruta
            raw = b.get("raw") or str(self)
            lines.append(divider())
            lines.append(row("Detalhe:"))
            for chunk in [raw[i:i + W - 6] for i in range(0, len(raw), W - 6)]:
                lines.append(row(f"  {chunk}"))

        lines.append(f"╚{'═' * (W - 2)}╝")
        return "\n".join(lines)


class NotFoundError(APIError):
    """Recurso não encontrado (HTTP 404)."""


class ValidationError(APIError):
    """Erro de validação dos dados enviados (HTTP 400/422)."""


class PermissaoError(APIError):
    """Acesso negado (HTTP 403) — roles insuficientes."""

    def __init__(
        self,
        status_code: int,
        message: str,
        body: Optional[dict] = None,
        endpoint: str = "",
        roles_usuario: Optional[list] = None,
        roles_necessarios: Optional[list] = None,
    ):
        self.endpoint = endpoint
        self.roles_usuario = roles_usuario or []
        self.roles_necessarios = roles_necessarios or []
        super().__init__(status_code, message, body)

    def format_report(self) -> str:
        W = 62

        def row(text: str = "") -> str:
            return f"║  {text:<{W - 4}}║"

        def divider(left: str = "╠", right: str = "╣") -> str:
            return f"{left}{'═' * (W - 2)}{right}"

        lines = [
            f"╔{'═' * (W - 2)}╗",
            row("ACESSO NEGADO — ZARC-NM (HTTP 403)"),
            divider(),
        ]

        if self.endpoint:
            lines.append(row(f"Endpoint : {self.endpoint}"))
            lines.append(divider())

        # Roles que o usuário possui
        lines.append(row("Roles do usuário:"))
        if self.roles_usuario:
            for r in sorted(self.roles_usuario):
                lines.append(row(f"  • {r}"))
        else:
            lines.append(row("  (nenhum role encontrado no token)"))

        lines.append(divider())

        # Roles exigidos por este endpoint, marcando quais faltam
        if self.roles_necessarios:
            lines.append(row(f"Roles aceitos por '{self.endpoint}':"))
            faltam = []
            for r in sorted(self.roles_necessarios):
                if r in self.roles_usuario:
                    lines.append(row(f"  ✓ {r}  ← você possui este role"))
                else:
                    lines.append(row(f"  ✗ {r}"))
                    faltam.append(r)

            if faltam:
                lines.append(divider())
                lines.append(row("Solicite à equipe ZARC-NM um dos roles acima"))
                lines.append(row("marcados com ✗ para seu usuário no Keycloak."))
        else:
            lines.append(row("Roles necessários não identificados."))
            lines.append(row("Verifique as permissões com a equipe ZARC-NM."))

        lines.append(f"╚{'═' * (W - 2)}╝")
        return "\n".join(lines)
