# Exemplo: dados externos em arquivos CSV

Este exemplo demonstra o uso da biblioteca `czarnm` lendo os dados de entrada a partir de **arquivos CSV organizados em diretórios**. Cada processo (talhão/gleba a ser classificado) tem seu próprio subdiretório com um CSV por entidade. Os resultados de cada etapa são gravados no arquivo `resultado.csv` dentro do mesmo diretório, permitindo retomar o fluxo em execuções separadas.

Diferente do exemplo `dados_auto_contidos`, aqui **nenhum dado está codificado no script** — tudo vem dos arquivos CSV, tornando o exemplo adequado para integrar com sistemas que exportam dados de talhões, análises e sensoriamento.

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

Copie o template da pasta `exemplos/` e preencha com seus dados:

```bash
cp ../env.example .env
```

Edite o `.env`:

```ini
# Ambiente: hml | prd
ZARCNM_AMBIENTE=hml

ZARCNM_USERNAME=seu.usuario@embrapa.br
ZARCNM_PASSWORD=sua_senha
ZARCNM_CLIENT_ID=seu-client-id
ZARCNM_CLIENT_SECRET=seu-client-secret
```

Para forçar um ambiente sem editar o arquivo:

```bash
ZARCNM_AMBIENTE=prd python example.py --dados dados/processo_001
```

## Estrutura de diretórios

```
dados_externos/
├── example.py
├── .env                              # credenciais (não versionado)
└── dados/
    └── processo_001/                 # um diretório por processo/talhão
        ├── talhao/
        │   ├── produtor.csv
        │   ├── propriedade.csv
        │   ├── talhao.csv
        │   ├── manejos.csv
        │   ├── coberturas_solo.csv
        │   └── producoes.csv
        ├── analise_solo/
        │   ├── analise_solo.csv
        │   └── amostras_solo.csv
        ├── sensoriamento_remoto/
        │   ├── sensoriamento_remoto.csv
        │   ├── indices_sensoriamento_remoto.csv
        │   ├── interpretacao_cobertura_solo.csv
        │   ├── interpretacao_cultura.csv
        │   └── interpretacao_manejo.csv
        └── resultado.csv             # gerado automaticamente pelo script
```

Cada subdiretório dentro de `dados/` representa um processo independente. Crie um novo diretório (ex: `processo_002/`) com a mesma estrutura de subdiretórios para processá-lo separadamente.

## Descrição dos arquivos CSV

**`talhao/`** — dados do talhão e da gleba

| Arquivo | Conteúdo | Linhas |
|---|---|---|
| `produtor.csv` | Nome e CPF do produtor | 1 |
| `propriedade.csv` | Nome, CNPJ, código CAR, código IBGE e polígono da propriedade | 1 |
| `talhao.csv` | Polígono WKT, área (ha), tipo de produtor e plantio em contorno | 1 |
| `manejos.csv` | Operações de manejo realizadas (data, tipo e nome) | N |
| `coberturas_solo.csv` | Avaliações de cobertura de solo (data e % palhada) | N |
| `producoes.csv` | Safras passadas e futura (cultura, datas, ILP) | N |

**`analise_solo/`** — dados da análise de solo

| Arquivo | Conteúdo | Linhas |
|---|---|---|
| `analise_solo.csv` | Cabeçalho da análise: CPF do produtor e CNPJ | 1 |
| `amostras_solo.csv` | Amostras com dados físico-químicos do solo | N |

**`sensoriamento_remoto/`** — dados de sensoriamento remoto

| Arquivo | Conteúdo | Linhas |
|---|---|---|
| `sensoriamento_remoto.csv` | Cabeçalho: datas, declividade, satélites utilizados | 1 |
| `indices_sensoriamento_remoto.csv` | Índices NDVI e NDTI por ponto e data | N |
| `interpretacao_cobertura_solo.csv` | Interpretação da cobertura de solo pelo satélite | N |
| `interpretacao_cultura.csv` | Interpretação do tipo de cultivo identificado | N |
| `interpretacao_manejo.csv` | Interpretação das operações de manejo identificadas | N |

> **Campos WKT** (polígono e ponto de coleta): devem ser delimitados por aspas duplas no CSV, pois contêm vírgulas. Ex: `"POLYGON ((-47.11 -22.80,...))"`.

> **Campo `ilp` em `producoes.csv`**: use `true`/`false`. Deixe em branco para a safra futura (previsão).

> **Safra futura em `producoes.csv`**: preencha apenas `data_previsao_plantio` e `data_previsao_colheita`; deixe `data_plantio` e `data_colheita` em branco. Ao menos uma safra futura é obrigatória.

## Como executar

### Fluxo completo

```bash
python example.py --dados dados/processo_001
```

Executa as etapas em sequência — autenticação, cadastro de gleba, análise de solo, sensoriamento remoto e consulta da classificação — gravando os resultados em `dados/processo_001/resultado.csv` ao final de cada etapa.

### Ações individuais

Use `--acao` para executar apenas uma etapa de cada vez:

```bash
# 1. Cadastra a gleba e salva uuid_gleba e chave_nm em resultado.csv
python example.py --dados dados/processo_001 --acao cadastraGleba

# 2. Cadastra análise de solo (lê chave_nm do resultado.csv automaticamente)
python example.py --dados dados/processo_001 --acao cadastraAnaliseSolo

# 3. Cadastra sensoriamento remoto
python example.py --dados dados/processo_001 --acao cadastraSensoriamentoRemoto

# 4. Consulta a classificação
python example.py --dados dados/processo_001 --acao consultaClassificacaoNM
```

Nas etapas 2, 3 e 4, a `chave_nm` é lida automaticamente do `resultado.csv` gerado na etapa 1. Também é possível passá-la explicitamente:

```bash
python example.py --dados dados/processo_001 --acao cadastraAnaliseSolo --chave_nm MINHA_CHAVE
```

Para retomar o fluxo completo a partir de uma chave já existente (pulando o cadastro de gleba):

```bash
python example.py --dados dados/processo_001 --chave_nm MINHA_CHAVE
```

## Arquivo de resultado

Após cada ação bem-sucedida, o script cria ou atualiza `resultado.csv` no diretório do processo:

| Campo | Descrição |
|---|---|
| `uuid_gleba` | UUID da gleba cadastrada |
| `chave_nm` | Chave de classificação NM retornada no cadastro da gleba |
| `uuid_analise_solo` | UUID da análise de solo cadastrada |
| `uuid_sensoriamento_remoto` | UUID do sensoriamento remoto cadastrado |
| `status_classificacao` | `disponivel` ou `em_processamento` |
| `valor_classificacao` | Resultado da classificação (quando disponível) |

O arquivo é mantido entre execuções parciais: cada ação atualiza apenas os campos de sua responsabilidade, preservando os demais.

## Adaptando para seus dados

1. Duplique o diretório `dados/processo_001/` e renomeie (ex: `processo_002/`)
2. Substitua o conteúdo de cada CSV pelos dados reais do seu talhão
3. Execute o script apontando para o novo diretório:

```bash
python example.py --dados dados/processo_002
```
