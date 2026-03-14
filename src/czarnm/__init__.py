"""
czarnm — Cliente SiNM: Cliente Python para a API SiNM (Sistema de Informações de Níveis de Manejo)
"""

from .client import SINMClient
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
    SINMError,
    AuthenticationError,
    APIError,
    NotFoundError,
    ValidationError,
    PermissaoError,
)

__all__ = [
    "SINMClient",
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
    "SINMError",
    "AuthenticationError",
    "APIError",
    "NotFoundError",
    "ValidationError",
    "PermissaoError",
]
