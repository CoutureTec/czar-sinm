"""
czarnm — Cliente ZARC-NM: Cliente Python para a API ZARC Nível de Manejo
"""

from .client import ZarcNMClient
from .models import (
    Produtor,
    Propriedade,
    Talhao,
    Manejo,
    Operacao,
    TipoOperacao,
    CoberturaSolo,
    Producao,
    Cultura,
    DadoGleba,
    DadosInput,
    Amostra,
    AnaliseSolo,
    Indice,
    InterpretacaoCoberturaSolo,
    InterpretacaoCultura,
    InterpretacaoManejo,
    SensoriamentoRemoto,
)
from .exceptions import (
    ZarcNMError,
    AuthenticationError,
    APIError,
    NotFoundError,
    ValidationError,
    PermissaoError,
)

__all__ = [
    "ZarcNMClient",
    "Produtor",
    "Propriedade",
    "Talhao",
    "Manejo",
    "Operacao",
    "TipoOperacao",
    "CoberturaSolo",
    "Producao",
    "Cultura",
    "DadoGleba",
    "DadosInput",
    "Amostra",
    "AnaliseSolo",
    "Indice",
    "InterpretacaoCoberturaSolo",
    "InterpretacaoCultura",
    "InterpretacaoManejo",
    "SensoriamentoRemoto",
    "ZarcNMError",
    "AuthenticationError",
    "APIError",
    "NotFoundError",
    "ValidationError",
    "PermissaoError",
]
