"""Exceções customizadas do cliente SiNM."""

from __future__ import annotations
import csv
import os
from typing import Optional

_ACOES_CSV = os.path.join(os.path.dirname(__file__), "acoes_sugeridas.csv")


def _carregar_acoes() -> list:
    try:
        with open(_ACOES_CSV, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


_ACOES = _carregar_acoes()


def _buscar_acao_sugerida(status_code: int, path: str = "", codigo: str = "") -> str:
    """Retorna a ação sugerida mais específica para o erro."""
    melhor: str = ""
    melhor_especificidade = -1
    for row in _ACOES:
        r_status = row.get("status", "").strip()
        r_path   = row.get("path",   "").strip()
        r_codigo = row.get("codigo", "").strip()
        r_acao   = row.get("acao",   "").strip()
        if not r_acao:
            continue
        if r_status and str(status_code) != r_status:
            continue
        if r_path and not path.startswith(r_path):
            continue
        if r_codigo and codigo != r_codigo:
            continue
        especificidade = bool(r_status) + bool(r_path) * 2 + bool(r_codigo) * 4
        if especificidade > melhor_especificidade:
            melhor_especificidade = especificidade
            melhor = r_acao
    return melhor


class SINMError(Exception):
    """Classe base para erros do cliente SiNM."""


class AuthenticationError(SINMError):
    """Erro de autenticação no Keycloak."""


class APIError(SINMError):
    """Erro retornado pela API SiNM."""

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

        def row_kv(label: str, value) -> None:
            """Imprime chave: valor, quebrando linhas longas."""
            prefix = f"{label:<10}: "
            text = str(value) if not isinstance(value, (dict, list)) else ""
            if isinstance(value, list):
                lines.append(row(f"{prefix}"))
                for item in value:
                    for chunk in [str(item)[i:i + W - 8] for i in range(0, len(str(item)), W - 8)]:
                        lines.append(row(f"  • {chunk}"))
                return
            full = prefix + text
            if len(full) <= W - 4:
                lines.append(row(full))
            else:
                lines.append(row(prefix.rstrip()))
                for chunk in [text[i:i + W - 6] for i in range(0, len(text), W - 6)]:
                    lines.append(row(f"  {chunk}"))

        # Campos com tratamento especial (não repetir abaixo)
        _KNOWN = {"codigoErro", "title", "instance", "fields", "errors", "raw",
                  "status", "type", "detail", "message"}

        lines.append(f"╔{'═' * (W - 2)}╗")
        lines.append(row("ERRO NA API SiNM"))
        lines.append(divider())
        lines.append(row(f"Status   : {self.status_code}"))

        b = self.body
        if b.get("type"):
            row_kv("Tipo", b["type"])
        if b.get("codigoErro"):
            lines.append(row(f"Código   : {b['codigoErro']}"))
        if b.get("title"):
            lines.append(row(f"Título   : {b['title']}"))
        if b.get("detail") or b.get("message"):
            row_kv("Detalhe", b.get("detail") or b.get("message"))
        if b.get("instance"):
            lines.append(row(f"Endpoint : {b['instance']}"))

        # Demais atributos retornados pelo servidor
        extras = {k: v for k, v in b.items() if k not in _KNOWN and k != "raw"}
        if extras:
            lines.append(divider())
            lines.append(row("Atributos adicionais:"))
            for k, v in extras.items():
                row_kv(k, v)

        # Campos com erro (validação)
        fields = b.get("fields") or b.get("errors") or {}
        if fields:
            lines.append(divider())
            lines.append(row("Campos com erro:"))
            for field, msg in fields.items():
                entry_fmt = f"  • {field:<38} → {msg}"
                if len(entry_fmt) > W - 4:
                    lines.append(row(f"  • {field}"))
                    lines.append(row(f"    → {msg}"))
                else:
                    lines.append(row(entry_fmt))
        elif not b.get("title") and not extras:
            raw = b.get("raw") or str(self)
            lines.append(divider())
            lines.append(row("Detalhe:"))
            for chunk in [raw[i:i + W - 6] for i in range(0, len(raw), W - 6)]:
                lines.append(row(f"  {chunk}"))

        acao = _buscar_acao_sugerida(
            self.status_code,
            path=b.get("instance", ""),
            codigo=b.get("codigoErro", "") or "",
        )
        if acao:
            lines.append(divider())
            row_kv("Ação sugerida", acao)

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
            row("ACESSO NEGADO — SiNM (HTTP 403)"),
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
                lines.append(row("Solicite à equipe SiNM um dos roles acima"))
                lines.append(row("marcados com ✗ para seu usuário no Keycloak."))
        else:
            lines.append(row("Roles necessários não identificados."))
            lines.append(row("Verifique as permissões com a equipe SiNM."))

        acao = _buscar_acao_sugerida(
            self.status_code,
            path=self.endpoint,
            codigo=self.body.get("codigoErro", "") or "",
        )
        if acao:
            lines.append(divider())
            lines.append(row(f"Ação sugerida: {acao}"))

        lines.append(f"╚{'═' * (W - 2)}╝")
        return "\n".join(lines)
