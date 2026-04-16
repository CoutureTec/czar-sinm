# Como fazer uma release

O pipeline de release é acionado automaticamente ao publicar uma tag `v*` no GitHub. Ele roda testes unitários e de integração antes de criar a release e publicar no PyPI — se qualquer etapa falhar, nada é publicado.

## Passo a passo

### 1. Atualize a versão

Em [`pyproject.toml`](pyproject.toml), incremente o campo `version` seguindo [Versionamento Semântico](https://semver.org/lang/pt-BR/):

```toml
[project]
version = "0.2.0"
```

| Tipo de mudança | O que incrementar | Exemplo |
|---|---|---|
| Correção de bug compatível | patch | `0.1.2` → `0.1.3` |
| Nova funcionalidade compatível | minor | `0.1.2` → `0.2.0` |
| Quebra de compatibilidade | major | `0.1.2` → `1.0.0` |

### 2. Atualize o CHANGELOG

Em [`CHANGELOG.md`](CHANGELOG.md), mova o conteúdo de `[Não lançado]` para uma nova seção com a versão e data:

```markdown
## [0.2.0] — 2026-04-16

### Alterado
- `Indice`: campo `coordenada` (WKT) substituído por `longitude` e `latitude` separados,
  alinhando com a nova interface do zarc-nm.
```

### 3. Commit, merge e tag

Faça o bump em `develop` e leve ao `main` pelo fluxo normal:

```bash
# em develop
git add pyproject.toml CHANGELOG.md
git commit -m "bump version to 0.2.0"
git push origin develop
```

Abra um PR de `develop` → `main`, aguarde os testes de CI passarem e faça o merge. Depois:

```bash
git checkout main && git pull origin main
git tag v0.2.0
git push origin v0.2.0
```

> A tag deve ter o prefixo `v` (ex: `v0.2.0`) — é isso que aciona o workflow `.github/workflows/release.yml`.

### 4. Acompanhe o pipeline

Acesse **Actions → Release** no GitHub. O pipeline executa em sequência:

```
Testes unitários ──┐
                   ├──► Criar release no GitHub ──► Publicar no PyPI
Testes integração ─┘
```

Se os testes de integração falharem, a release **não** é criada e o PyPI **não** é atualizado.

---

## Publicação no PyPI (configuração única)

O pacote é publicado via **Trusted Publisher** (OIDC) — sem API token armazenado. Configuração necessária apenas uma vez:

1. Acesse [pypi.org](https://pypi.org) → sua conta → **Publishing**
2. Adicione um trusted publisher com:
   - **Owner:** `CoutureTec`
   - **Repository:** `czar-sinm`
   - **Workflow:** `release.yml`
   - **Environment:** `pypi`

## Secrets necessários para integração

Configure em **Settings → Secrets and variables → Actions**:

| Secret | Descrição |
|---|---|
| `SINM_USERNAME` | Usuário de homologação |
| `SINM_PASSWORD` | Senha de homologação |
| `SINM_CLIENT_ID` | Client ID do Keycloak |
| `SINM_CLIENT_SECRET` | Client Secret do Keycloak |
