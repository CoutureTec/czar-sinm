# Exemplos

Fluxo completo de integração com a API SiNM, do envio dos dados à consulta do
resultado:

1. autenticação
2. cadastro da gleba (talhão, produtor, propriedade, manejo e histórico de cultivos)
3. análise de solo química e física
4. sensoriamento remoto
5. consulta da classificação de nível de manejo (ONM)
6. racional do cálculo — por que a gleba recebeu aquele nível

Há um script por versão do contrato da API:

| Script | Contrato | Diferenças |
|---|---|---|
| [`exemplo_v1.py`](exemplo_v1.py) | `/api/v1` | análise química e física num único envio |
| [`exemplo_v2.py`](exemplo_v2.py) | `/api/v2` | análise química e física em rotas separadas; `cnpjLaboratorio` obrigatório |

## Como rodar

```bash
pip install czar-sinm python-dotenv
cd exemplos
cp env.example .env          # preencha SINM_CLIENT_ID e SINM_CLIENT_SECRET
python exemplo_v2.py
```

Outras formas:

```bash
python exemplo_v2.py --fonte csv        # lê os CSVs em vez do JSON
python exemplo_v2.py --chave CHAVE      # só consulta a ONM e o racional de uma chave
python exemplo_v2.py --autenticar       # só testa as credenciais e mostra os papéis
```

O script sai com código 1 se alguma etapa falhar, então serve também como teste
em pipelines de CI.

## Fonte de dados

Os scripts não sabem de onde vêm os dados: eles recebem um **registro por gleba**
e o convertem nos modelos do SDK. A fonte é escolhida em `SINM_FONTE` (ou `--fonte`):

| Fonte | Onde | Formato |
|---|---|---|
| `json` | [`dados/glebas.json`](dados/glebas.json) | uma lista com todos os dados de cada gleba — é o formato do registro |
| `csv` | [`dados/csv/`](dados/csv/) | uma tabela por assunto, ligadas pela coluna `idExterno`, como num banco de dados |

As duas fontes trazem os mesmos dados e geram os mesmos envios.

### Tabelas do CSV

| Arquivo | Uma linha por |
|---|---|
| `glebas.csv` | gleba: produtor, propriedade, talhão, cultura-alvo, laboratório |
| `manejos.csv` | operação de manejo do solo |
| `coberturas.csv` | avaliação de cobertura (palhada) |
| `producoes.csv` | cultivo do histórico |
| `amostras_quimicas.csv` | amostra da análise química |
| `amostras_fisicas.csv` | amostra da análise física |
| `sensoriamento.csv` | gleba: período e satélites do sensoriamento |
| `indices.csv` | índice (NDVI/NDTI) do sensoriamento |
| `interpretacoes_cobertura.csv`, `interpretacoes_cultura.csv`, `interpretacoes_manejo.csv` | interpretação do sensoriamento |

Os nomes das colunas são os nomes dos campos da API.

### Usando os seus dados

- **Arquivos no mesmo formato:** aponte `SINM_DADOS` para o seu arquivo JSON ou
  pasta de CSVs.
- **Banco de dados ou outro sistema:** escreva em [`fonte_dados.py`](fonte_dados.py)
  uma função que devolva os registros no formato de `dados/glebas.json` e
  registre-a em `FONTES`. O restante do fluxo não muda. O início do arquivo
  tem um esboço com banco de dados.

O `idExterno` é o identificador da gleba no **seu** sistema. Ele é gravado na
gleba e permite localizá-la depois com `client.listar_glebas(id_externo=...)` e
`client.listar_classificacoes(id_externo=...)`.

### Datas dos dados de exemplo

A API valida as datas contra o dia de hoje (coberturas recentes, coleta próxima
do plantio). Com `SINM_AJUSTAR_DATAS=sim`, as datas dos dados de exemplo são
atualizadas na leitura para continuarem válidas. **Use `nao` com dados reais.**

## Arquivos

```
exemplos/
├── exemplo_v1.py     # fluxo no /api/v1
├── exemplo_v2.py     # fluxo no /api/v2
├── fonte_dados.py    # fontes JSON e CSV + conversão para os modelos do SDK
├── comum.py          # configuração, cliente, consulta da ONM/racional e saída
├── env.example
└── dados/
    ├── glebas.json
    └── csv/
```
