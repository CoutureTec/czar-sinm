# zarcnm — Cliente Python para o ZARC Nível de Manejo

Biblioteca Python para integração com a API **ZARC-NM** (Zoneamento Agrícola de Risco Climático — Nível de Manejo), desenvolvida pela Embrapa.

## Pré-requisitos

- Python 3.8+
- Credenciais de acesso ao ZARC-NM (usuário, senha, client ID e client secret fornecidos pela equipe ZARC-NM)

## Instalação

```bash
cd czar-client
pip install -e .
```

## Ambientes disponíveis

| `ambiente` | URL da API |
|------------|-----------|
| `hml`      | `https://www.zarcnm-h.cnptia.embrapa.br/zarcnm` |
| `prd`      | `https://www.zarcnm.cnptia.embrapa.br/zarcnm`   |

> O Swagger UI pode ser usado para explorar endpoints, schemas e testar chamadas diretamente no browser.
> [Abrir Swagger UI](https://www.zarcnm.cnptia.embrapa.br/zarcnm/swagger-ui/index.html)

## Configuração das credenciais

Copie o template e preencha com seus dados:

```bash
cp .env.example .env
```

```ini
# Ambiente: hml | prd
ZARCNM_AMBIENTE=hml

# Credenciais do usuário
ZARCNM_USERNAME=seu.usuario@embrapa.br
ZARCNM_PASSWORD=sua_senha

# Credenciais do client Keycloak (fornecidas pela equipe ZARC-NM)
ZARCNM_CLIENT_ID=seu-client-id
ZARCNM_CLIENT_SECRET=seu-client-secret
```

> **Atenção:** nunca versione o arquivo `.env`. Ele está listado no `.gitignore`.

## Permissões necessárias (roles Keycloak)

Cada endpoint exige que o usuário possua ao menos um dos roles abaixo:

| Endpoint | Roles aceitos |
|---|---|
| `POST /api/v1/glebas` | `OPERADOR_CONTRATOS` |
| `POST /api/v1/analises-solo/{chave}` | `OPERADOR_ANALISE_SOLO` |
| `POST /api/v1/sensoriamentos-remotos/{chave}` | `OPERADOR_SENSORIAMENTO_REMOTO` |
| `POST /api/v1/operacoes` | `OPERADOR_CONTRATOS` |
| `GET  /api/v1/classificacoes/{chave}` | `OPERADOR_CONTRATOS` |

Em caso de 403, o cliente exibe automaticamente os roles do usuário e quais estão faltando. Solicite a atribuição do role adequado à equipe ZARC-NM.

Para verificar os roles do usuário autenticado:

```python
print(client.roles)
```

## Executando o exemplo

```bash
pip install -e .
cp .env.example .env   # edite com suas credenciais
python example.py
```

### Fluxo completo

```bash
python example.py
```

Executa as cinco etapas em sequência: autenticação, cadastro de gleba, análise de solo, sensoriamento remoto e consulta da classificação.

### Ações individuais

Use `--acao` para executar apenas uma etapa:

```bash
# Cadastra somente a gleba e imprime a chaveClassificacaoNM
python example.py --acao cadastraGleba

# Cadastra análise de solo para uma chave já existente
python example.py --acao cadastraAnaliseSolo --chave_nm MINHA_CHAVE

# Cadastra sensoriamento remoto para uma chave já existente
python example.py --acao cadastraSensoriamentoRemoto --chave_nm MINHA_CHAVE

# Consulta o resultado da classificação
python example.py --acao consultaClassificacaoNM --chave_nm MINHA_CHAVE
```

Também é possível rodar o fluxo completo fornecendo uma chave já existente — nesse caso o cadastro de gleba é pulado:

```bash
python example.py --chave_nm MINHA_CHAVE
```

### Configurações por ambiente

**Homologação**
```ini
ZARCNM_AMBIENTE=hml
```

**Produção**
```ini
ZARCNM_AMBIENTE=prd
```

## Saída esperada

```
=== Autenticação ===
Usuário : seu.usuario@embrapa.br
Roles   : ['OPERADOR_CONTRATOS', 'BETA_USER', ...]

=== Cadastrando talhão/gleba ===
Gleba cadastrada com sucesso!
  UUID              : xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Chave Classificação NM: XXXXXXXXXXXXXX

=== Cadastrando análise de solo ===
Análise de solo cadastrada com sucesso!
  UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

=== Cadastrando sensoriamento remoto ===
Sensoriamento remoto cadastrado com sucesso!
  UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

=== Consultando classificação de nível de manejo ===
Classificação obtida para chave: XXXXXXXXXXXXXX
  Resultado: {...}

=== Listando glebas cadastradas ===
Total de glebas: 1
```

## Estrutura da biblioteca

```
zarcnm/
├── client.py       # ZarcNMClient — métodos principais + diagnóstico de 403
├── auth.py         # Autenticação Keycloak com cache e renovação de token
├── models.py       # Dataclasses para os payloads da API
└── exceptions.py   # ZarcNMError, ValidationError, NotFoundError, PermissaoError, ...
```

## Referência rápida da API

```python
from zarcnm import ZarcNMClient

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
from zarcnm.exceptions import (
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
