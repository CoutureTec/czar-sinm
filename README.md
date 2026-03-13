# czarnm — Cliente Python para o ZARC Nível de Manejo

Biblioteca Python para integração com a API **ZARC-NM** (Zoneamento Agrícola de Risco Climático — Nível de Manejo), desenvolvida pela Embrapa.

## Pré-requisitos

- Python 3.8+
- Credenciais de acesso ao ZARC-NM (usuário, senha, client ID e client secret fornecidos pela equipe ZARC-NM)

## Instalação

**Via GitHub (recomendado):**

```bash
pip install git+https://github.com/CoutureTec/czar-nm.git
```

Versão específica (tag):

```bash
pip install git+https://github.com/CoutureTec/czar-nm.git@v0.1.0
```

## Estrutura da biblioteca

```
src/czarnm/
├── client.py       # ZarcNMClient — métodos principais + diagnóstico de 403
├── auth.py         # Autenticação Keycloak com cache e renovação de token
├── models.py       # Dataclasses para os payloads da API
└── exceptions.py   # ZarcNMError, ValidationError, NotFoundError, PermissaoError, ...
```

## Referência rápida da API

```python
from czarnm import ZarcNMClient

client = ZarcNMClient(
    username="...", password="...",
    client_id="...", client_secret="...",
    ambiente="hml",
)

# Roles do usuário autenticado (extraídos do token JWT)
client.roles                                     # list[str]

# Talhão / Gleba
client.cadastrar_gleba(dado_gleba)               # POST /api/v1/glebas
client.buscar_gleba(uuid)                        # GET  /api/v1/glebas/{uuid}
client.listar_glebas()                           # GET  /api/v1/glebas

# Análise de Solo
client.cadastrar_analise_solo(analise, chave_classificacao_nm=chave)
client.buscar_analise_solo(uuid)
client.listar_analises_solo()

# Sensoriamento Remoto  (chave_classificacao_nm obrigatória)
client.cadastrar_sensoriamento_remoto(sensoriamento, chave_classificacao_nm=chave)
client.buscar_sensoriamento_remoto(uuid)
client.listar_sensoriamentos_remotos()

# Classificação Nível de Manejo
client.consultar_classificacao(chave)            # GET  /api/v1/classificacoes/{chave}
client.listar_classificacoes()                   # GET  /api/v1/classificacoes

# Operação combinada (referencia recursos já cadastrados pelos UUIDs)
client.cadastrar_operacao(dados_input)           # POST /api/v1/operacoes
```

## Tratamento de erros

```python
from czarnm.exceptions import (
    AuthenticationError,
    PermissaoError,
    ValidationError,
    NotFoundError,
    APIError,
)

try:
    resposta = client.cadastrar_gleba(dado_gleba)
except AuthenticationError as e:
    # Falha no login ou credenciais inválidas
    print(f"Falha na autenticação: {e}")
except PermissaoError as e:
    # HTTP 403 — exibe roles do usuário vs. roles exigidos pelo endpoint
    print(e.format_report())
except ValidationError as e:
    # HTTP 400/422 — payload com campos inválidos
    print(e.format_report())
except NotFoundError as e:
    # HTTP 404
    print(f"Recurso não encontrado: {e}")
except APIError as e:
    # Outros erros HTTP
    print(e.format_report())
```

### Exemplo de relatório de erro 403

```
╔════════════════════════════════════════════════════════════╗
║  ACESSO NEGADO — ZARC-NM (HTTP 403)                        ║
╠════════════════════════════════════════════════════════════╣
║  Endpoint : /api/v1/analises-solo/MINHA_CHAVE              ║
╠════════════════════════════════════════════════════════════╣
║  Roles do usuário:                                         ║
║    • OPERADOR_CONTRATOS                                     ║
╠════════════════════════════════════════════════════════════╣
║  Roles aceitos por '/api/v1/analises-solo/MINHA_CHAVE':    ║
║    ✗ ADMINISTRADOR                                         ║
║    ✗ BETA_USER                                             ║
║    ✗ OPERADOR_ANALISE_SOLO                                 ║
╠════════════════════════════════════════════════════════════╣
║  Solicite à equipe ZARC-NM um dos roles acima              ║
║  marcados com ✗ para seu usuário no Keycloak.              ║
╚════════════════════════════════════════════════════════════╝
```

### Exemplo de relatório de erro de validação

```
╔════════════════════════════════════════════════════════════╗
║  ERRO NA API ZARC-NM                                       ║
╠════════════════════════════════════════════════════════════╣
║  Status   : 422                                            ║
║  Título   : Erro de validação                              ║
╠════════════════════════════════════════════════════════════╣
║  Campos com erro:                                          ║
║    • talhao.area                  → deve ser positivo      ║
╚════════════════════════════════════════════════════════════╝
```

## Licença

Distribuído sob a [MIT License](LICENSE).

Direitos autorais (c) 2025 CoutureTec — Alfaiataria de Software - www.couturetec.com.br
