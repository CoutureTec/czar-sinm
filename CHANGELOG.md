# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

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
  Gleba, operação, classificação e `analises-solo/disponiveis` seguem em `/api/v1` nos dois
  modos.
- `AmostraQuimica.betaGlicosidase`: grafia canônica do indicador.
- `consultar_racional`: documentação dos campos causais da v6.2026
  (`regraDeterminante`, `limitantesPrincipais`, `papelNaNota`, `contribuicao`), com os
  valores possíveis de cada enum.

### Alterado
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
- Campo `efeitoNaNota` do racional: continua na resposta, mas compara o indicador com a
  nota *final*, então indicadores que causaram um teto saem como `NEUTRO`. Prefira
  `papelNaNota` + `contribuicao`.

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
