# czarsinm — Cliente da API do SiNM

[![CI](https://github.com/CoutureTec/czar-sinm/actions/workflows/ci.yml/badge.svg)](https://github.com/CoutureTec/czar-sinm/actions/workflows/ci.yml)
[![Release](https://github.com/CoutureTec/czar-sinm/actions/workflows/release.yml/badge.svg?event=push)](https://github.com/CoutureTec/czar-sinm/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/czar-sinm)](https://pypi.org/project/czar-sinm/)

Biblioteca Python para integração com o **SiNM** (Sistema de Informações de Níveis de Manejo).

Integrar com o SiNM envolve **autenticação OAuth2** com renovação de token, **payloads extensos**,
erros com tratamento próprio (validação, permissão, regra de negócio) e um **fluxo em etapas**
que dependem umas das outras. O `czarsinm` cuida disso numa interface de alto nível: com poucas
linhas, seu sistema envia glebas, análises de solo e sensoriamentos e consulta o nível de manejo,
sem lidar com o Keycloak nem com a estrutura interna da API.

A biblioteca é open-source: correções que um integrador reporta passam a valer para todos.

## Instalação

Requer Python 3.8+.

```bash
pip install czar-sinm            # versão mais recente
pip install czar-sinm==0.4.0     # versão fixa (recomendado em produção)
```

As versões e o que muda em cada uma estão no [CHANGELOG](CHANGELOG.md).

## Início rápido

O diretório [`exemplos/`](exemplos/README.md) tem o fluxo completo pronto para rodar: autenticação,
gleba, análise de solo química e física, sensoriamento remoto, classificação (ONM) e racional
do cálculo. Há um script para o `/api/v1` e outro para o `/api/v2`, e os dados vêm de uma fonte
configurável (JSON ou CSV) que você troca pelo seu banco de dados ou ERP.

```bash
cd exemplos
cp env.example .env        # preencha as credenciais
python exemplo_v2.py       # ou exemplo_v1.py
```

## Fluxo de integração

Cada gleba passa por quatro etapas. O cadastro da gleba devolve a `chaveClassificacaoNM`,
que liga as demais:

| Etapa | Método | Resultado |
|---|---|---|
| 1. Gleba (talhão, produtor, propriedade, manejo, histórico, cultura-alvo) | `cadastrar_gleba` | `chaveClassificacaoNM` |
| 2. Análise de solo química e física | `cadastrar_analise_solo_quimica` / `_fisica` | vínculo com a chave |
| 3. Sensoriamento remoto | `cadastrar_sensoriamento_remoto` | vínculo com a chave |
| 4. Classificação e racional | `consultar_classificacao` / `consultar_racional` | nível de manejo (NM1–NM4) e indicadores |

```python
from czarsinm import AnaliseSoloFisica, AnaliseSoloQuimica, DadoGleba, SensoriamentoRemoto, SINMClient

client = SINMClient(
    username=None, password=None,          # só usados com grant_type="password"
    client_id="00000000000000",            # CNPJ da empresa, sem máscara
    client_secret="chave-secreta-do-client",
    ambiente="hml",
    api_version="v2",
)

gleba = DadoGleba(...)                     # um exemplo preenchido de cada
quimica = AnaliseSoloQuimica(...)          # modelo está em
fisica = AnaliseSoloFisica(...)            # exemplos/dados/glebas.json e
sensoriamento = SensoriamentoRemoto(...)   # exemplos/fonte_dados.py

chave = client.cadastrar_gleba(gleba)["chaveClassificacaoNM"]
client.cadastrar_analise_solo_quimica(quimica, chave_classificacao_nm=chave)
client.cadastrar_analise_solo_fisica(fisica, chave_classificacao_nm=chave)
client.cadastrar_sensoriamento_remoto(sensoriamento, chave_classificacao_nm=chave)

classificacao = client.consultar_classificacao(chave)
print(f"NM{classificacao['scoreFinal']}", classificacao.get("inconsistencias"))
racional = client.consultar_racional(chave)  # disponível quando a classificação está completa
```

Guarde a chave no seu sistema junto do talhão (o `Talhao.idExterno` ajuda a localizar a gleba
depois): é com ela que você consulta o resultado mais tarde.

## Autenticação

O padrão é OAuth2 **Client Credentials**: a API autoriza por empresa (client do Keycloak,
identificado pelo CNPJ), usando os papéis do service account.

| `grant_type` | Quando usar | O que precisa |
|---|---|---|
| `client_credentials` (padrão) | Integração sistema a sistema | `client_id` + `client_secret` |
| `password` | Usuário humano com papel atribuído no Keycloak | `username` + `password` + `client_id` + `client_secret` |

```python
client = SINMClient("usuario@empresa.com.br", "senha", client_id, client_secret,
                    ambiente="hml", grant_type="password")

client.client_roles    # papéis do token por empresa (CNPJ) — útil para conferir o acesso
```

O token é obtido no primeiro uso e renovado automaticamente.

## Ambientes

| Parâmetro | Uso |
|---|---|
| `ambiente="hml"` / `"prd"` | Homologação (padrão) e produção — URLs já configuradas |
| `ambiente="<outro>"` + `base_url`, `keycloak_url`, `keycloak_realm` | Ambiente customizado |
| `proxies={"https": "http://proxy:3128"}` | Rede que exige proxy HTTP(S) |
| `timeout=60` | Tempo limite por requisição, em segundos |
| `api_version="v1"` / `"v2"` | Contrato da API — ver [Contrato v2](#contrato-v2-opt-in) |
| `tamanho_pagina=100` | Itens por requisição nos `listar_*` |

## Referência rápida da API

```python
from czarsinm import SINMClient

client = SINMClient(
    username="...", password="...",
    client_id="...", client_secret="...",
    ambiente="hml",
)

# Roles do token JWT
client.roles                                     # list[str] — realm roles
client.client_roles                              # dict[str, list[str]] — client roles por client (CNPJ)

# Talhão / Gleba  (/api/v1 ou /api/v2, conforme api_version)
client.cadastrar_gleba(dado_gleba)               # POST /api/{v}/glebas
client.atualizar_gleba(uuid, dado_gleba)         # PUT  /api/{v}/glebas/{uuid}
client.buscar_gleba(uuid)                        # GET  /api/{v}/glebas/{uuid}
client.listar_glebas()                           # GET  /api/{v}/glebas
client.listar_glebas(id_externo="TALHAO-7")      # filtra pelo Talhao.idExterno

# Análise de Solo — química
client.cadastrar_analise_solo_quimica(analise, chave_classificacao_nm=chave)
client.atualizar_analise_solo_quimica(uuid, analise)
client.buscar_analise_solo_quimica(uuid)
client.listar_analises_solo_quimicas()

# Análise de Solo — física
client.cadastrar_analise_solo_fisica(analise, chave_classificacao_nm=chave)
client.atualizar_analise_solo_fisica(uuid, analise)
client.buscar_analise_solo_fisica(uuid)
client.listar_analises_solo_fisicas()

# Análise de Solo — payload combinado (só /api/v1; química + física juntas)
client.cadastrar_analise_solo(analise, chave_classificacao_nm=chave)
client.listar_analises_solo()
client.buscar_analise_solo(uuid)                 # depreciado → use ..._quimica(uuid)

# Análises disponíveis para um CPF (sempre /api/v1; traz uuidAnaliseSolo)
client.consultar_analises_disponiveis(cpf)
client.consultar_analises_disponiveis(cpf, data_referencia="2026-08-04")

# Sensoriamento Remoto  (chave_classificacao_nm obrigatória)
client.cadastrar_sensoriamento_remoto(sensoriamento, chave_classificacao_nm=chave)
client.atualizar_sensoriamento_remoto(uuid, sensoriamento)
client.buscar_sensoriamento_remoto(uuid)
client.listar_sensoriamentos_remotos()
client.remover_sensoriamento_remoto(uuid)        # depreciado: só ADMINISTRADOR (403 p/ integradores)

# Classificação Nível de Manejo
client.consultar_classificacao(chave)            # GET  /api/v1/classificacoes/{chave}
client.consultar_racional(chave)                 # GET  .../{chave}/racional
client.listar_classificacoes()                   # GET  /api/v1/classificacoes (mais recente primeiro)
client.listar_classificacoes(id_externo="TALHAO-7")

# Tabelas de domínio (sempre /api/v1; qualquer usuário autenticado)
client.listar_culturas()                         # códigos de Cultura.codigo
client.listar_satelites()                        # códigos dos codigoSatelite*
```

Os `listar_*` percorrem todas as páginas da API e devolvem a lista completa.
`SINMClient(tamanho_pagina=...)` muda quantos itens vêm por requisição (padrão 100).

## Contrato v2 (opt-in)

Por padrão o cliente fala `/api/v1`, o contrato estável — ele aceita os nomes
canônicos **e** os legados, e nunca ganha campo obrigatório novo. Quem quiser o
contrato limpo pede explicitamente:

```python
client = SINMClient(..., api_version="v2")
client.api_version                               # "v2"
```

O que muda no `v2`:

| | `v1` (default) | `v2` |
|---|---|---|
| Análise de solo | química, física **e** o payload combinado | só química e física — `cadastrar_analise_solo` levanta `ValueError` |
| `cnpjLaboratorio` | opcional | **obrigatório** — o SDK valida antes de enviar (a API responde 400) |
| Nomes legados (`cnpj`, `betaGlicosidade`) | aceitos e enviados junto | não enviados; se chegarem, a API os descarta em silêncio |
| Gleba | safra a classificar como uma produção de `producoes` com as duas previsões | `culturaAlvo` obrigatório; `producoes` leva só o histórico |

O roteamento por versão vale para gleba, análise de solo e sensoriamento remoto.
Classificação, `analises-solo/disponiveis`, culturas e satélites seguem em `/api/v1`
nos dois modos — não existe `v2` desses recursos.

### Cultura-alvo (soja ou milho)

A safra que será classificada é declarada com `CulturaAlvo` — só soja (`001`)
e milho (`002`) são cultura-alvo. A safra é definida pela data de plantio (agosto a
julho) e leva o nome do ano em que termina: um plantio em outubro de 2026 é da
safra 2027 (2026/27).

```python
from czarsinm import CulturaAlvo, DadoGleba

alvo = CulturaAlvo.soja("2026-10-01", "2027-01-10")          # ou CulturaAlvo.milho(...)
alvo = CulturaAlvo.de_nome("milho", "2026-10-01", "2027-02-20", ilp=False)

dado = DadoGleba(..., producoes=historico, culturaAlvo=alvo)
client.cadastrar_gleba(dado)               # v1 ou v2
client.atualizar_gleba(uuid_gleba, dado)   # PUT
```

O mesmo `DadoGleba` serve aos dois contratos: no `v1` o SDK envia o alvo como
a última produção de `producoes`; no `v2` envia `culturaAlvo` e só o histórico.
Código antigo que põe a safra futura em `producoes` (sem `culturaAlvo`) continua
funcionando nos dois — essa produção é promovida a alvo. No `v2`, porém,
`producoes` precisa de ao menos um cultivo além do alvo: uma gleba cuja única
produção é a safra futura serializa no `v1`, mas no `v2` levanta `ValueError`.
Declarar `culturaAlvo` **e** uma produção com as duas previsões é erro.

### Campos novos e opcionais

```python
from czarsinm import TIPO_AMOSTRAGEM_ZONA_HOMOGENEA

Talhao(..., idExterno="TALHAO-7")                 # id do seu sistema, até 100 caracteres
AnaliseSoloQuimica(..., tipoAmostragem=TIPO_AMOSTRAGEM_ZONA_HOMOGENEA)
InterpretacaoCultura("Cultivo de 1ª safra", "2025-10-01", "2026-02-01", cultura="Soja")
Propriedade(codigoCar="MT-5107248-1025F299474640148FE845C7A0B62635")  # só o CAR é obrigatório
```

- `idExterno` não precisa ser único e não deve conter dado pessoal (é gravado sem
  criptografia). No `atualizar_gleba`, `None` mantém o valor gravado e `""` o remove.
- `tipoAmostragem` define a densidade amostral exigida: `GRADE_REGULAR` (1 amostra a
  cada 25 ha, assumido quando omitido) ou `ZONA_HOMOGENEA` (1 a cada 1000 ha).
- São opcionais, como na API: `Propriedade.nome`/`codigoIbge`/`poligono`,
  `Talhao.plantioContorno`, `Manejo.tipoOperacao`, `AmostraQuimica.cpfResponsavelColeta`
  e `SensoriamentoRemoto.declividadeMedia`/`plantioContorno`/`terraceamento`.

`betaGlicosidase` é a grafia canônica. A antiga `betaGlicosidade` (erro de
grafia) ainda é aceita pelo dataclass, mas emite `DeprecationWarning`; informar
as duas com valores diferentes é erro.

## Tratamento de erros

Os erros retornados pelas chamadas à api são logados de forma a tornar mais claro o possível a sua causa, baseado na documentação da API do SiNM.

```python
import time

from czarsinm.exceptions import (
    AuthenticationError,
    UsuarioNaoCadastradoError,
    NaoAutorizadoError,
    PermissaoError,
    ValidationError,
    NotFoundError,
    ConflitoConcorrenciaError,
    TempoEsgotadoError,
    APIError,
)

try:
    resposta = client.cadastrar_gleba(dado_gleba)
except AuthenticationError as e:
    # Falha no login no Keycloak (credenciais inválidas)
    print(f"Falha na autenticação: {e}")
except UsuarioNaoCadastradoError as e:
    # HTTP 401 — token válido, mas usuário/service account não cadastrado no SiNM
    print(e.format_report())
except NaoAutorizadoError as e:
    # HTTP 401 — token recusado pela API (expirado, inválido); motivo em e.descricao
    print(e.format_report())
except PermissaoError as e:
    # HTTP 403 — exibe os client roles do usuário (por CNPJ) vs. roles exigidos
    print(e.format_report())
except ValidationError as e:
    # HTTP 400/422 — payload com campos inválidos
    print(e.format_report())
except NotFoundError as e:
    # HTTP 404
    print(f"Recurso não encontrado: {e}")
except ConflitoConcorrenciaError as e:
    # HTTP 409 — nada foi gravado; reenvie após e.retry_after segundos
    time.sleep(e.retry_after or 1)
    resposta = client.cadastrar_gleba(dado_gleba)
except TempoEsgotadoError as e:
    # HTTP 408 — reenvie mais tarde
    print(e.format_report())
except APIError as e:
    # Outros erros HTTP
    print(e.format_report())
```

Todas as exceções da API herdam de `APIError`. O relatório (`format_report()`)
inclui uma ação sugerida para os erros mais comuns — 401, 408, 409 e as regras de
negócio de cobertura do solo (RN03, RN04) e de validade e escolha da análise de
solo (RN15, RN18, RN20).

### Exemplo de relatório de erro 403

Os roles `OPERADOR_*` são **client roles**: cada empresa é um client (o CNPJ), e o
role precisa estar no client da empresa dona do dado. O relatório lista os roles
por client e, quando o role exigido existe em algum, indica em qual.

```
╔════════════════════════════════════════════════════════════╗
║  ACESSO NEGADO — SiNM (HTTP 403)                           ║
╠════════════════════════════════════════════════════════════╣
║  Endpoint : /api/v1/analises-solo/MINHA_CHAVE              ║
╠════════════════════════════════════════════════════════════╣
║  Client roles do usuário (por empresa/CNPJ):               ║
║    12345678000190:                                         ║
║      • OPERADOR_CONTRATOS                                  ║
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

## Estrutura da biblioteca

```
src/czarsinm/
├── client.py       # SINMClient — métodos da API + diagnóstico de 403
├── auth.py         # Autenticação Keycloak com cache e renovação de token
├── models.py       # Dataclasses dos payloads da API
└── exceptions.py   # SINMError, ValidationError, PermissaoError, ConflitoConcorrenciaError, ...
```

## Contribuindo

- [CONTRIBUTING.md](CONTRIBUTING.md) — ambiente de desenvolvimento, testes e fluxo de PR
- [SECURITY.md](SECURITY.md) — como reportar vulnerabilidades
- [Issues](https://github.com/CoutureTec/czar-sinm/issues) — bugs e sugestões

## Licença

Distribuído sob a [MIT License](LICENSE).

Direitos autorais (c) 2025 CoutureTec — Alfaiataria de Software - www.couturetec.com.br
