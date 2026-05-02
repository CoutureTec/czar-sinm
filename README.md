# czarsinm — Cliente da API do SiNM

[![CI](https://github.com/CoutureTec/czar-sinm/actions/workflows/ci.yml/badge.svg)](https://github.com/CoutureTec/czar-sinm/actions/workflows/ci.yml)
[![Release](https://github.com/CoutureTec/czar-sinm/actions/workflows/release.yml/badge.svg)](https://github.com/CoutureTec/czar-sinm/actions/workflows/release.yml)

Biblioteca Python para integração com a **SiNM** (Sistema de Informações de Níveis de Manejo).

Esta biblioteca visa compartilhar um mesmo cliente robusto em python que facilite a integração com o sistema SiNM.

Há exemplos de uso com fonte de dados interna e arquivos. → [Veja os exemplos de uso](exemplos/README.md)


# Motivação de manter uma biblioteca pública 

Integrar com o SiNM envolve **autenticação OAuth2** com renovação automática de token, serialização de **payloads complexos**, tratamento diferenciado de erros por tipo (validação, permissão, recurso não encontrado) e um **fluxo de múltiplas etapas** com dependências entre si. Implementar tudo isso do zero em cada projeto **consome dias de desenvolvimento** e gera código duplicado, frágil e difícil de manter.

O `czarsinm` encapsula toda essa complexidade em uma interface de alto nível: **com poucas linhas de código** seu time já está enviando glebas, análises de solo e sensoriamentos, sem precisar conhecer os detalhes do protocolo Keycloak nem a estrutura interna da API.

Por ser **open-source**, a biblioteca se beneficia de múltiplos olhares: bugs são identificados mais cedo, edge cases reportados por outros integradores viram correções que todos aproveitam, e o código passa por revisão pública contínua — o que resulta em uma base mais confiável do que qualquer implementação proprietária isolada.

Há exemplos de uso com dados embutidos no código e com dados em arquivos CSV.
→ [Veja os exemplos](exemplos/README.md)

## Pré-requisitos

- Python 3.8+

## Instalação

**Via PyPI (recomendado):**

```bash
pip install czar-sinm
```

**Via GitHub com tag:**

```bash
pip install git+https://github.com/CoutureTec/czar-sinm.git@v0.1.0
```


## Início rápido

### Exploração interativa (sem configuração prévia)

A forma mais rápida de testar a biblioteca é usando a interface interativa,
que **não exige configuração prévia**: se não houver um arquivo `.env`, ela
solicita as credenciais diretamente no terminal e oferece salvar para as
próximas execuções.

```bash
cd exemplos/04_interativo
python exemplo.py
```

Na primeira execução sem `.env`, você verá:

```
================================================================
  SINM — Credenciais
================================================================
  Arquivo .env não encontrado.
  Preencha as credenciais abaixo (senha não será exibida):

  Usuário       (SINM_USERNAME)    :
  Senha         (SINM_PASSWORD)    :
  Client ID     (SINM_CLIENT_ID)   :
  Client Secret (SINM_CLIENT_SECRET):
  Ambiente      [hml/prd, Enter=hml]:
```

Após autenticar, um menu completo é exibido com todas as operações
disponíveis — listar, cadastrar, buscar e consultar recursos — organizado
por domínio:

```
================================================================
  SINM — Interface Interativa  |  HML
  Usuário : joao.silva@empresa.com.br
================================================================

  GLEBAS
  [ 1] Listar Glebas
  [ 2] Cadastrar Gleba
  [ 3] Buscar Gleba por UUID

  ANÁLISE DE SOLO
  [ 4] Listar Análises de Solo
  ...

  CONTA
  [12] Definir CNPJ Operador Ativo
  [13] Ver Autorizações Completas

  [ 0] Sair
================================================================
  Opção:
```

Consulte o [README do exemplo interativo](exemplos/04_interativo/README.md)
para detalhes sobre todas as opções do menu.

### Uso via código

```python
from czarsinm import SINMClient
from czarsinm.exceptions import PermissaoError, APIError

# Default: autenticação por Client Credentials (M2M).
# username/password são aceitos no construtor mas ignorados neste fluxo.
client = SINMClient(
    username="usuario@exemplo.com",  # ignorado em client_credentials
    password="senha",                # ignorado em client_credentials
    client_id="meu-client-id",
    client_secret="meu-client-secret",
    ambiente="hml",
)

# Verifica autenticação
print("Roles:", client.roles)

# Lista glebas cadastradas
try:
    glebas = client.listar_glebas()
    print(f"{len(glebas)} gleba(s) encontrada(s)")
except PermissaoError as e:
    print(e.format_report())
except APIError as e:
    print(e.format_report())
```

#### Fluxo de autenticação

Desde a versão 0.3.x, o **default** é OAuth2 **Client Credentials** —
o backend zarc-nm autoriza por empresa (client) usando service-account roles,
e esse modelo só funciona com Client Credentials.

Para manter o fluxo antigo (ROPC, autenticação por usuário humano), passe
`grant_type="password"` explicitamente:

```python
client = SINMClient(
    username="usuario@exemplo.com",
    password="senha",
    client_id="meu-client-id",
    client_secret="meu-client-secret",
    ambiente="hml",
    grant_type="password",   # opcional, default é "client_credentials"
)
```

| Modo | Quando usar | O que precisa |
|------|-------------|---------------|
| `client_credentials` (default) | Integração M2M; backend usa SA roles cross-empresa | `client_id` + `client_secret` |
| `password` (ROPC) | Usuário humano com role direta atribuída no Keycloak | `username` + `password` + `client_id` + `client_secret` |

`grant_type` é o último parâmetro do construtor (posicional ou por nome) —
isso preserva compatibilidade com qualquer chamada existente.

Para exemplos completos com cadastro de gleba, análise de solo e sensoriamento remoto → [exemplos/README.md](exemplos/README.md)

## Estrutura da biblioteca

```
src/czarsinm/
├── client.py       # SINMClient — métodos principais + diagnóstico de 403
├── auth.py         # Autenticação Keycloak com cache e renovação de token
├── models.py       # Dataclasses para os payloads da API
└── exceptions.py   # SINMError, ValidationError, NotFoundError, PermissaoError, ...
```

## Referência rápida da API

```python
from czarsinm import SINMClient

client = SINMClient(
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

Os erros retornados pelas chamadas à api são logados de forma a tornar mais claro o possível a sua causa, baseado na documentação da API do SiNM.

```python
from czarsinm.exceptions import (
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
║  ACESSO NEGADO — SiNM (HTTP 403)                           ║
╠════════════════════════════════════════════════════════════╣
║  Endpoint : /api/v1/analises-solo/MINHA_CHAVE              ║
╠════════════════════════════════════════════════════════════╣
║  Roles do usuário:                                         ║
║    • OPERADOR_CONTRATOS                                     ║
╠════════════════════════════════════════════════════════════╣
║  Roles aceitos por '/api/v1/analises-solo/MINHA_CHAVE':    ║
║    ✗ OPERADOR_ANALISE_SOLO                                 ║
╠════════════════════════════════════════════════════════════╣
║  Solicite à equipe SiNM um dos roles acima                 ║
║  marcados com ✗ para seu usuário no Keycloak.              ║
╚════════════════════════════════════════════════════════════╝
```

### Exemplo de relatório de erro de validação

```
╔════════════════════════════════════════════════════════════╗
║  ERRO NA API SiNM                                          ║
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
