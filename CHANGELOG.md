# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.4.0] — 2026-11-03

### Adicionado
- `tipoAmostragem` em `AnaliseSolo`, `AnaliseSoloQuimica` e `AnaliseSoloFisica`
  (`TIPO_AMOSTRAGEM_GRADE_REGULAR` — 1 amostra a cada 25 ha, assumido pela API quando
  omitido — ou `TIPO_AMOSTRAGEM_ZONA_HOMOGENEA` — 1 a cada 1000 ha). `separar()` propaga o
  campo. ([#38](https://github.com/CoutureTec/czar-sinm/issues/38))
- `Talhao.idExterno` (até 100 caracteres) e filtro `id_externo` em `listar_glebas` e
  `listar_classificacoes`. ([#39](https://github.com/CoutureTec/czar-sinm/issues/39))
- `InterpretacaoCultura.cultura`: nome da cultura identificada, opcional.
  ([#40](https://github.com/CoutureTec/czar-sinm/issues/40))
- `listar_culturas()` e `listar_satelites()`: tabelas de domínio de `Cultura.codigo` e dos
  `codigoSatelite*`, sempre em `/api/v1`. ([#41](https://github.com/CoutureTec/czar-sinm/issues/41))
- Exceções específicas, todas subclasses de `APIError`
  ([#42](https://github.com/CoutureTec/czar-sinm/issues/42)):
  - `ConflitoConcorrenciaError` (409): nada foi gravado; reenviar após `retry_after` segundos.
  - `TempoEsgotadoError` (408).
  - `NaoAutorizadoError` (401): token recusado pela API, com `erro` e `descricao` lidos de
    `WWW-Authenticate`; `UsuarioNaoCadastradoError` quando o usuário ou service account não
    está cadastrado no SiNM.
- Ações sugeridas para 401, 408, 409 e para as regras RN03, RN04, RN15, RN18 e RN20.

### Alterado
- Campos opcionais na API deixam de ser obrigatórios no SDK
  ([#43](https://github.com/CoutureTec/czar-sinm/issues/43)): `Propriedade.nome`,
  `.codigoIbge` e `.poligono`; `Talhao.plantioContorno`; `Manejo.tipoOperacao`;
  `AmostraQuimica.cpfResponsavelColeta`; `SensoriamentoRemoto.declividadeMedia`,
  `.plantioContorno` e `.terraceamento`. A ordem dos campos não mudou: construção por
  posição continua válida, e os obrigatórios que vêm depois de um opcional são conferidos na
  construção (`TypeError` com o que falta).

## [0.3.0] — 2026-11-03

### Adicionado
- `InterpretacaoManejo`: campo opcional `tipoOperacao` (ex.: 'ARAÇÃO', 'GRADAGEM',
  'SUBSOLAGEM', 'ESCARIFICAÇÃO'), alinhado ao `InterpretacaoManejoInput` da API.
- Documentação do comportamento de inconsistência em `InterpretacaoManejo.operacao` e
  `.tipoOperacao`: valores fora do domínio são aceitos (envio não é rejeitado), mas geram
  inconsistência na API e são ignorados no cálculo de nível de manejo. Consulte os valores
  possíveis na documentação (tabelas `operacao` / `tipo_operacao`).
- Documentação do comportamento de domínio do campo `camada` em `AmostraQuimica`/`AmostraFisica`:
  qualquer código é aceito; um código fora do domínio é preservado mas gera inconsistência
  ("Camada não prevista") e não entra no cálculo; '40_060'/'60_100' geram o aviso "Camada não
  utilizada na classificação". Não enviar o sentinela '00_000'.
- **Suporte à v6.2026 (HML 04/08/2026).**
- `consultar_analises_disponiveis(cpf, data_referencia=None)`: lista as análises de solo
  disponíveis para um CPF. Traz `uuidAnaliseSolo`, que permite buscar a análise completa
  sem depender da chave de classificação. Sempre em `/api/v1`.
- Endpoints por tipo de análise, com os modelos `AnaliseSoloQuimica` e `AnaliseSoloFisica`:
  `cadastrar/atualizar/buscar/listar_analise(s)_solo_quimica(s)` e `..._fisica(s)`.
- `AnaliseSolo.separar()`: divide o payload combinado em `(química, física)` para uso com
  os endpoints por tipo.
- `atualizar_sensoriamento_remoto(uuid, sensoriamento)` e
  `remover_sensoriamento_remoto(uuid)`.
- Parâmetro `api_version` em `SINMClient` (`'v1'` default, `'v2'` opt-in) e propriedade
  `client.api_version`. Em `v2` o `cnpjLaboratorio` é obrigatório — o SDK valida antes de
  enviar — e o payload combinado não existe (`cadastrar_analise_solo` levanta `ValueError`).
  Classificação e `analises-solo/disponiveis` seguem em `/api/v1` nos dois modos.
- `AmostraQuimica.betaGlicosidase`: grafia canônica do indicador.
- `consultar_racional`: documentação dos campos causais da v6.2026
  (`regraDeterminante`, `limitantesPrincipais`, `papelNaNota`, `contribuicao`), com os
  valores possíveis de cada enum.

- **Gleba no contrato v2.** `cadastrar_gleba`, `buscar_gleba` e `listar_glebas` seguem
  `api_version` (`/api/v2/glebas` no v2); novo `atualizar_gleba(uuid, dado)` (PUT).
- `CulturaAlvo` (`soja`, `milho`, `de_nome`) e as constantes `CULTURA_SOJA`/`CULTURA_MILHO`;
  campo `DadoGleba.culturaAlvo`. No v1 o alvo vai como última produção; no v2 vai em
  `culturaAlvo`, obrigatório. Sem `culturaAlvo`, a produção com as duas previsões em
  `producoes` é promovida a alvo — desde que sobre ao menos um cultivo no histórico.
- Exemplos 01, 02 e 04: escolha da versão da API (`--api-version` / `SINM_API_VERSION`) e
  da cultura-alvo soja ou milho (`--cultura` / `SINM_CULTURA_ALVO`; no 02 e no 04 também
  `talhao/cultura_alvo.csv`). Novo conjunto `processo_002_milho` no exemplo 02.

- `SINMClient(tamanho_pagina=100)`: itens por página nas listagens.
- `PermissaoError.roles_por_client` e `PermissaoError.escopo` (`'client'`, `'realm'` ou `None`).

### Corrigido
- `listar_*` devolviam só a primeira página (20 itens) das listagens paginadas da API.
  Agora percorrem todas as páginas e devolvem a lista completa
  ([#30](https://github.com/CoutureTec/czar-sinm/issues/30)).
- `DadoGleba.to_dict('v2')` gerava `producoes: []` quando a única produção era a
  cultura-alvo, e a API respondia 400. Agora recusa antes da chamada com `ValueError`
  explicando que o v2 exige ao menos um cultivo no histórico
  ([#28](https://github.com/CoutureTec/czar-sinm/issues/28)).
- `AnaliseSolo` (payload combinado do v1) aceitava envio sem amostras físicas, que a API
  recusa com 400. Agora recusa antes da chamada; para enviar só a química, use
  `AnaliseSoloQuimica` ([#29](https://github.com/CoutureTec/czar-sinm/issues/29)).
- Relatório do 403 (`PermissaoError`) comparava os realm roles do token com os roles
  `OPERADOR_*`, que são client roles (um client por CNPJ). Agora lista os client roles por
  empresa e indica em quais o role exigido está
  ([#31](https://github.com/CoutureTec/czar-sinm/issues/31)).
- `/classificacoes` não exige role (a chave dá acesso à consulta); o relatório do 403 deixou
  de pedir `OPERADOR_CONTRATOS` ali ([#32](https://github.com/CoutureTec/czar-sinm/issues/32)).
- O `DELETE` de sensoriamento remoto é restrito ao realm role `ADMINISTRADOR`; o relatório do
  403 deixou de indicar `OPERADOR_SENSORIAMENTO_REMOTO`
  ([#33](https://github.com/CoutureTec/czar-sinm/issues/33)).

### Alterado
- Docstring de `Cultura`: os códigos de exemplo estavam errados ('018' não é milho). Agora:
  '001' soja grão, '002' milho grão, '072' milho silagem, '085' trigo grão.
- Payloads passam a enviar `cnpjPropriedade` (nome canônico) em vez da chave legada `cnpj`,
  em análise de solo e sensoriamento remoto. Todos os ambientes já aceitam a canônica.
- Em `v1`, `betaGlicosidase` é enviado junto com o nome legado `betaGlicosidade`, porque os
  ambientes em produção ainda só conhecem a grafia antiga. Em `v2` só a canônica é enviada.
- Exemplos `05_racional` e `06_racional_por_codigo`: passam a exibir a leitura causal
  (regra determinante, limitantes, papel e contribuição de cada indicador). O mapa de
  `efeitoNaNota` estava desatualizado — usava valores que a API nunca retornou.

### Depreciado
- `AmostraQuimica.betaGlicosidade` (erro de grafia): use `betaGlicosidase`. Informar as duas
  com valores diferentes é erro; informar só a antiga emite `DeprecationWarning`.
- `buscar_analise_solo(uuid)`: a rota `/api/v1/analises-solo/{uuid}` não existe em nenhum
  ambiente — o método sempre falhou. Agora emite `DeprecationWarning` e delega para
  `buscar_analise_solo_quimica`.
- `remover_sensoriamento_remoto`: a remoção é restrita a administradores na API e responde
  403 para integradores. Emite `DeprecationWarning`; para corrigir um sensoriamento, use
  `atualizar_sensoriamento_remoto` ([#33](https://github.com/CoutureTec/czar-sinm/issues/33)).
- Campo `efeitoNaNota` do racional: continua na resposta, mas compara o indicador com a
  nota *final*, então indicadores que causaram um teto saem como `NEUTRO`. Prefira
  `papelNaNota` + `contribuicao`.

### Removido
- `cadastrar_operacao` e o modelo `DadosInput`: a API não tem mais o fluxo combinado por
  UUIDs. A classificação de nível de manejo sai do envio da gleba, da análise de solo e do
  sensoriamento, e é consultada com `consultar_classificacao(chave)`.

## [0.3.0.rc2] — 2026-06-16

## [0.3.0.rc1] — 2026-06-16

## [0.2.1] — 2025-04-01

### Adicionado
- Exemplos de uso com dados auto-contidos (`exemplos/01_dados_auto_contidos/`)
- Exemplos de uso com dados em arquivos CSV (`exemplos/dados_externos/`)
- Suíte de testes unitários (`tests/`)
- Workflow de CI com GitHub Actions (`.github/workflows/ci.yml`)
- `CONTRIBUTING.md` com guia de contribuição
- Parâmetro opcional `grant_type` em `SINMClient` e `KeycloakAuth`. Default
  permanece `'client_credentials'` (compatibilidade com chamadas existentes).
  Passar `grant_type='password'` ativa o fluxo ROPC (`username` + `password`
  obrigatórios).

### Alterado
- `Indice`: campo `coordenada` (string WKT) substituído por `longitude: float` e `latitude: float` separados, alinhando com a nova interface do zarc-nm
- Autorização entre clients (empresas) e não entre usuários e clients.
- Autenticação default migrada de ROPC (`grant_type=password`) para Client
  Credentials (`grant_type=client_credentials`). Motivo: o backend zarc-nm
  passou a autorizar por empresa (client) usando service-account roles, fluxo
  que só funciona com Client Credentials. Os parâmetros `username`/`password`
  no construtor permanecem (não quebra código existente), mas são ignorados
  no default. Para manter o comportamento antigo (ex.: integrações com auth
  por usuário humano), passe `grant_type='password'` explicitamente.


---

## [0.1.0] — 2025-04-01

### Adicionado
- `SINMClient` com suporte aos ambientes `hml` e `prd`
- Autenticação via Keycloak (OAuth2 Resource Owner Password Credentials) com cache e renovação automática de token
- `cadastrar_gleba` / `buscar_gleba` / `listar_glebas`
- `cadastrar_analise_solo` / `buscar_analise_solo` / `listar_analises_solo`
- `cadastrar_sensoriamento_remoto` / `buscar_sensoriamento_remoto` / `listar_sensoriamentos_remotos`
- `consultar_classificacao` / `listar_classificacoes`
- `cadastrar_operacao` (fluxo combinado por UUIDs)
- Modelos de dados: `DadoGleba`, `AnaliseSolo`, `SensoriamentoRemoto`, `DadosInput` e todos os tipos auxiliares
- Hierarquia de exceções: `SINMError`, `AuthenticationError`, `APIError`, `ValidationError`, `NotFoundError`, `PermissaoError`
- Diagnóstico automático de HTTP 403 com diff de roles do usuário vs. roles exigidos pelo endpoint
- Relatórios formatados em `APIError.format_report()` e `PermissaoError.format_report()`
