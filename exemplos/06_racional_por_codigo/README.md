# Racional do cálculo a partir do código (ambiente do `.env`)

Variante do [exemplo 05](../05_racional/) dirigida inteiramente pelo `.env`.
Monta o `SINMClient` com as credenciais e o **ambiente configurados** e
respeita o `SINM_GRANT_TYPE`:

- `client_credentials` (service account — **padrão**)
- `password` (ROPC — usuário humano autenticado)

Recebe um `--codigo` (a `chaveClassificacaoNM`) e imprime o **racional do
cálculo**: *por que* a gleba recebeu aquele nível de manejo — indicadores
avaliados, fatores restritivos e narrativa.

O racional só existe para a classificação **COMPLETA** (preliminar ou em
processamento responde "não disponível"). A projeção depende dos papéis do
autenticado na empresa operadora da gleba:

- com `OPERADOR_ANALISE_SOLO` → **completa** (valor, faixa e score de cada indicador)
- sem `OPERADOR_ANALISE_SOLO` → **compacta** (só nome, origem e efeito na nota)

> A chave (`chaveClassificacaoNM`) é a capability: quem a possui consulta o
> racional. A projeção completa/compacta é o que muda conforme os papéis.

---

## Pré-requisitos

- Python 3.9+
- Pacote `czarsinm` instalado (veja o README raiz do projeto)
- Um `.env` configurado (use `../env.example` como base)
- Um `código` (`chaveClassificacaoNM`) de uma classificação completa

---

## Configuração (`.env`)

```bash
cd exemplos/06_racional_por_codigo
cp ../env.example .env
# edite o .env
```

Variáveis lidas:

| Variável | Uso |
|---|---|
| `SINM_AMBIENTE` | `hml`, `prd` ou customizado |
| `SINM_BACKEND_URL`, `SINM_KEYCLOAK`, `SINM_KEYCLOAK_REALM` | obrigatórias se ambiente customizado |
| `SINM_CLIENT_ID`, `SINM_CLIENT_SECRET` | client Keycloak (sempre) |
| `SINM_USERNAME`, `SINM_PASSWORD` | só se `SINM_GRANT_TYPE=password` |
| `SINM_GRANT_TYPE` | `client_credentials` (padrão) ou `password` |

---

## Execução

```bash
python exemplo.py --codigo SEU_CODIGO
python exemplo.py --codigo SEU_CODIGO --json   # imprime o JSON cru
python exemplo.py                              # pergunta o código no terminal
```

`--chave` é aceito como alias de `--codigo`.
