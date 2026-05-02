# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

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
