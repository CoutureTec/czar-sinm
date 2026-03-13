# zarcnm — Cliente Python para o ZARC Nível de Manejo

Biblioteca Python para integração com a API **ZARC-NM** (Zoneamento Agrícola de Risco Climático — Nível de Manejo), desenvolvida pela Embrapa.

## Pré-requisitos

- Python 3.10+
- Credenciais de acesso ao ZARC-NM (usuário e senha cadastrados no Keycloak da Embrapa)

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


> O Swagger UI pode ser usado para explorar os endpoints, schemas de request/response e testar chamadas diretamente no browser.
[Abrir](https://www.zarcnm.cnptia.embrapa.br/zarcnm/swagger-ui/index.html)     

## Configuração das credenciais

As credenciais e o ambiente são lidos de um arquivo `.env`. Copie o template e edite:

```bash
cp .env.example .env
```

Edite o `.env` com seus dados:

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

## Executando o exemplo

```bash
pip install -e .
cp .env.example .env   # edite com suas credenciais
python example.py
```

O script executa o fluxo completo:

1. **Autenticação** no Keycloak (token JWT obtido automaticamente)
2. **Cadastro de talhão/gleba** — retorna a `chaveClassificacaoNM`
3. **Cadastro de análise de solo** — vinculada ao talhão pela chave
4. **Cadastro de sensoriamento remoto** — vinculado ao talhão pela chave
5. **Consulta da classificação de nível de manejo** — resultado final

### Homologação

```ini
ZARCNM_AMBIENTE=hml
ZARCNM_USERNAME=seu.usuario@embrapa.br
ZARCNM_PASSWORD=sua_senha
ZARCNM_CLIENT_ID=seu-client-id
ZARCNM_CLIENT_SECRET=seu-client-secret
```

### Produção

```ini
ZARCNM_AMBIENTE=prd
ZARCNM_USERNAME=seu.usuario@embrapa.br
ZARCNM_PASSWORD=sua_senha
ZARCNM_CLIENT_ID=seu-client-id
ZARCNM_CLIENT_SECRET=seu-client-secret
```

## Saída esperada

```
=== Cadastrando talhão/gleba ===
Gleba cadastrada com sucesso!
  UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
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
├── client.py       # ZarcNMClient — métodos principais
├── auth.py         # Autenticação Keycloak com cache de token
├── models.py       # Dataclasses para os payloads da API
└── exceptions.py   # ZarcNMError, ValidationError, NotFoundError, ...
```

## Referência rápida da API

```python
from zarcnm import ZarcNMClient

client = ZarcNMClient(
    username="...", password="...",
    client_id="...", client_secret="...",
    ambiente="hml",
)

# Talhão / Gleba
client.cadastrar_gleba(dado_gleba)               # POST /api/v1/glebas
client.buscar_gleba(uuid)                        # GET  /api/v1/glebas/{uuid}
client.listar_glebas()                           # GET  /api/v1/glebas

# Análise de Solo
client.cadastrar_analise_solo(analise, chave_classificacao_nm=chave)
client.buscar_analise_solo(uuid)
client.listar_analises_solo()

# Sensoriamento Remoto
client.cadastrar_sensoriamento_remoto(sensoriamento, chave_classificacao_nm=chave)
client.buscar_sensoriamento_remoto(uuid)
client.listar_sensoriamentos_remotos()

# Classificação Nível de Manejo
client.consultar_classificacao(chave)            # GET  /api/v1/classificacoes/{chave}
client.listar_classificacoes()                   # GET  /api/v1/classificacoes
```

## Tratamento de erros

```python
from zarcnm.exceptions import ValidationError, NotFoundError, AuthenticationError, APIError

try:
    resposta = client.cadastrar_gleba(dado_gleba)
except AuthenticationError as e:
    print(f"Falha na autenticação: {e}")
except ValidationError as e:
    print(f"Dados inválidos (HTTP {e.status_code}): {e}")
    print(f"Detalhes: {e.body}")
except NotFoundError as e:
    print(f"Recurso não encontrado: {e}")
except APIError as e:
    print(f"Erro na API (HTTP {e.status_code}): {e}")
```
