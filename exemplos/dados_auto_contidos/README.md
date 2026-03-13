# Exemplo: dados auto-contidos

Este exemplo demonstra o uso completo da biblioteca `czarnm` sem nenhuma dependência de arquivos externos. Todos os dados de talhão, amostras de solo, índices de sensoriamento remoto, produtor e propriedade estão **codificados diretamente no script Python** — ideal para testar a integração rapidamente ou entender o fluxo da API sem precisar preparar arquivos de entrada.

## Pré-requisitos

- Python 3.8+
- Credenciais de acesso ao ZARC-NM (usuário, senha, client ID e client secret)

Instale a biblioteca e as dependências do exemplo:

```bash
pip install git+https://github.com/CoutureTec/czar-nm.git
pip install python-dotenv
```

Ou, se estiver trabalhando a partir do código-fonte:

```bash
# Na raiz do repositório
pip install -e .
pip install python-dotenv
```

## Configuração das credenciais

O script lê as credenciais de um arquivo `.env` no mesmo diretório. Copie o template da pasta `exemplos/` e preencha com seus dados:

```bash
cp ../env.example .env
```

Edite o `.env`:

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

> **Atenção:** nunca versione o `.env`. Ele está listado no `.gitignore`.

Para forçar um ambiente específico sem editar o arquivo, passe a variável diretamente:

```bash
ZARCNM_AMBIENTE=prd python example.py
```

## Como executar

### Fluxo completo (recomendado para um primeiro teste)

```bash
python example.py
```

Executa as seguintes etapas em sequência:

1. Autentica e exibe os roles do usuário
2. Cadastra a gleba (talhão + produtor + propriedade + manejos + coberturas + produções)
3. Cadastra a análise de solo (amostras com dados químicos e físicos)
4. Cadastra o sensoriamento remoto (índices NDVI/NDTI + interpretações)
5. Consulta a classificação de nível de manejo gerada pela API
6. Lista todas as glebas cadastradas

A `chaveClassificacaoNM` retornada no passo 2 é usada automaticamente nos passos seguintes.

### Ações individuais

Use `--acao` para executar apenas uma etapa de cada vez:

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

Também é possível rodar o fluxo completo a partir de uma chave já existente — o cadastro de gleba é pulado:

```bash
python example.py --chave_nm MINHA_CHAVE
```

## O que está codificado no exemplo

| Dado | Descrição |
|------|-----------|
| `Produtor` | Nome e CPF fictícios válidos |
| `Propriedade` | Nome, CNPJ, código CAR, código IBGE e polígono WKT |
| `Talhao` | Polígono WKT, área (32 ha), tipo de produtor |
| `Manejo` | 1 operação de revolvimento de solo |
| `CoberturaSolo` | 3 avaliações anuais de percentual de palhada |
| `Producao` | 3 safras passadas + 1 safra futura (obrigatória) |
| `AnaliseSolo` | 3 amostras com granulometria, macronutrientes e pH |
| `SensoriamentoRemoto` | 8 índices NDVI/NDTI + interpretações de cobertura, cultura e manejo |

Para adaptar ao seu caso de uso, edite as funções `_dado_gleba()`, `_analise_solo()` e `_sensoriamento_remoto()` diretamente no `example.py`.

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

> Se a classificação ainda estiver sendo processada, a consulta retorna `"Classificação ainda não disponível (processamento em andamento)."` — aguarde alguns instantes e rode `--acao consultaClassificacaoNM` novamente.
