# Como fazer uma release

Todo o processo de release é executado por um único workflow do GitHub Actions, disparado manualmente. O workflow faz, em ordem:

1. valida o formato da versão e que a tag ainda não existe;
2. roda os testes unitários e de integração;
3. atualiza `pyproject.toml` e `CHANGELOG.md` direto em `main`;
4. cria a tag `vX.Y.Z` e a publica no GitHub;
5. cria a release no GitHub;
6. publica no PyPI via Trusted Publisher (OIDC).

Se qualquer etapa falhar, **nada** é commitado, tagueado ou publicado.

## Passo a passo

1. Garanta que `develop` foi mergeada em `main` pelo fluxo normal de PR.
2. No GitHub, vá em **Actions → Release → Run workflow**.
3. Em "Nova versão", informe a versão sem o prefixo `v` (ex: `0.3.0`, `0.3.0-rc1`), seguindo [Versionamento Semântico](https://semver.org/lang/pt-BR/):
```bash
git checkout main && git pull origin main
git tag v0.2.0
git push origin v0.2.0
```

   | Tipo de mudança | O que incrementar | Exemplo |
   |---|---|---|
   | Correção de bug compatível | patch | `0.2.1` → `0.2.2` |
   | Nova funcionalidade compatível | minor | `0.2.1` → `0.3.0` |
   | Quebra de compatibilidade | major | `0.2.1` → `1.0.0` |

4. Clique em **Run workflow** e acompanhe o pipeline. O fluxo é:

   ```
   validate ─┬─► unit ────────┐
             └─► integration ─┴─► bump ─► release ─► pypi
   ```

5. Ao final, o pacote estará disponível em `pip install czar-sinm==X.Y.Z`.

> O workflow também faz o bump no `CHANGELOG.md`, inserindo `## [X.Y.Z] — YYYY-MM-DD` logo abaixo de `## [Não lançado]`. Mantenha a seção `[Não lançado]` populada com as mudanças desde a última release antes de disparar o workflow.

---

## Configuração inicial (uma vez só)

### Trusted Publisher no PyPI

O pacote é publicado via **Trusted Publisher** (OIDC) — sem API token armazenado.

1. [pypi.org](https://pypi.org) → sua conta → **Publishing**
2. Adicione um trusted publisher com:
   - **Owner:** `CoutureTec`
   - **Repository:** `czar-sinm`
   - **Workflow:** `release.yml`
   - **Environment:** `pypi`

### Secrets para os testes de integração

Em **Settings → Secrets and variables → Actions**:

| Secret | Descrição |
|---|---|
| `SINM_USERNAME` | Usuário de homologação |
| `SINM_PASSWORD` | Senha de homologação |
| `SINM_CLIENT_ID` | Client ID do Keycloak |
| `SINM_CLIENT_SECRET` | Client Secret do Keycloak |

### Permissão de push em `main`

O job `bump` usa o `GITHUB_TOKEN` para empurrar o commit de bump e a tag em `main`. Se a branch `main` tiver regra de proteção exigindo PR/review, o token padrão será bloqueado. Soluções:

- adicionar `github-actions[bot]` à allowlist de "bypass" da regra; **ou**
- criar um PAT (fine-grained, escopo `Contents: write` no repositório), salvar como secret `RELEASE_PAT` e trocar `token: ${{ secrets.GITHUB_TOKEN }}` por `token: ${{ secrets.RELEASE_PAT }}` no workflow.
