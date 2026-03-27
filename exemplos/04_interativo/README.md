# Exemplo 04 — Interface Interativa

Interface de linha de comando interativa para explorar e operar a API SINM
diretamente no terminal, sem precisar editar arquivos ou montar chamadas
manualmente.

---

## Pré-requisitos

- Python 3.9+
- Pacote `czarsinm` instalado (veja o README raiz do projeto)
- Credenciais de acesso ao SINM (usuário, senha, client ID e client secret)

---

## Execução

```bash
cd exemplos/04_interativo
python exemplo.py
```

Não há argumentos de linha de comando. Tudo é feito de forma interativa.

---

## Credenciais

### Opção 1 — arquivo `.env` (recomendado)

Copie o template e preencha com suas credenciais:

```bash
cp ../env.example .env
```

Conteúdo mínimo do `.env`:

```
SINM_AMBIENTE=hml
SINM_USERNAME=seu.usuario@dominio.br
SINM_PASSWORD=sua_senha
SINM_CLIENT_ID=seu-client-id
SINM_CLIENT_SECRET=seu-client-secret
```

Para ambientes customizados (diferentes de `hml` e `prd`), adicione também:

```
SINM_BACKEND_URL=https://endereco-da-api
SINM_KEYCLOAK=https://endereco-do-keycloak/realms
SINM_KEYCLOAK_REALM=nome-do-realm
```

### Opção 2 — entrada interativa

Se o `.env` não existir ou estiver incompleto, o script solicita as
credenciais no terminal ao iniciar. A senha e o client secret não são
exibidos durante a digitação.

Após autenticar com sucesso, o script pergunta se você deseja salvar as
credenciais em `.env` para as próximas execuções:

```
  Salvar credenciais em .env para a próxima vez? [s/N]:
```

---

## Fluxo de inicialização

```
================================================================
  SINM — Autenticando...
================================================================
  Usuário : joao.silva@empresa.com.br
  Ambiente: HML

  Autenticado com sucesso!
================================================================
```

---

## Menu principal

O menu é exibido após cada ação, mostrando sempre o usuário logado e,
quando definido, o CNPJ do operador ativo com seus roles:

```
================================================================
  SINM — Interface Interativa  |  HML
  Usuário : joao.silva@empresa.com.br
  CNPJ    : 54.194.116/0001-38  [OPERADOR_CONTRATOS, OPERADOR_ANALISE_SOLO]
================================================================

  GLEBAS
  [ 1] Listar Glebas
  [ 2] Cadastrar Gleba
  [ 3] Buscar Gleba por UUID

  ANÁLISE DE SOLO
  [ 4] Listar Análises de Solo
  [ 5] Cadastrar Análise de Solo
  [ 6] Buscar Análise de Solo por UUID

  SENSORIAMENTO
  [ 7] Listar Sensoriamentos Remotos
  [ 8] Cadastrar Sensoriamento Remoto
  [ 9] Buscar Sensoriamento por UUID

  CLASSIFICAÇÃO
  [10] Listar Classificações NM
  [11] Consultar Classificação por Chave

  CONTA
  [12] Definir CNPJ Operador Ativo
  [13] Ver Autorizações Completas

  [ 0] Sair
================================================================
  Opção:
```

---

## Operações de listagem e busca

Opções **1, 4, 7, 10** não requerem nenhuma entrada — chamam a API e
exibem o resultado em JSON diretamente.

Opções **3, 6, 9** solicitam o UUID do recurso:

```
  UUID da gleba:
```

A opção **11** solicita a chave de classificação NM:

```
  Chave de Classificação NM (chaveClassificacaoNM):
```

---

## Operações de cadastro (opções 2, 5, 8)

Solicitam o caminho para o diretório de dados no formato do
[exemplo 02](../02_dados_externos/), que contém os CSVs de entrada:

```
  Diretório de dados (ex: ../02_dados_externos/dados/processo_001):
```

### Estrutura esperada do diretório

```
processo_001/
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
└── sensoriamento_remoto/
    ├── sensoriamento_remoto.csv
    ├── indices_sensoriamento_remoto.csv
    ├── interpretacao_cobertura_solo.csv
    ├── interpretacao_cultura.csv
    └── interpretacao_manejo.csv
```

Consulte os arquivos de dados de exemplo em
[`../02_dados_externos/dados/processo_001/`](../02_dados_externos/dados/processo_001/)
para referência de formato.

As opções **5** (Análise de Solo) e **8** (Sensoriamento Remoto) solicitam
também a chave de classificação NM obtida no cadastro da gleba:

```
  Chave de Classificação NM (chaveClassificacaoNM):
```

---

## Opção 12 — Definir CNPJ Operador Ativo

Lista todas as empresas (CNPJs) presentes no token JWT do usuário e permite
selecionar uma como operador ativo:

```
  * [1] 54.194.116/0001-38  (OPERADOR_CONTRATOS, OPERADOR_ANALISE_SOLO)
    [2] 12.345.678/0001-99  (OPERADOR_SENSORIAMENTO_REMOTO)

  Número da empresa (Enter para cancelar):
```

Após selecionar, exibe os roles e as capacidades habilitadas para aquele
CNPJ. O CNPJ ativo fica visível no cabeçalho do menu em todas as
iterações subsequentes.

---

## Opção 13 — Ver Autorizações Completas

Exibe um resumo completo das autorizações do token: roles de realm e roles
por empresa (CNPJ), marcando o CNPJ ativo quando houver um definido.
