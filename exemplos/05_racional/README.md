# Racional do cálculo

Autentica o usuário humano via **ROPC** (`grant_type=password`) com
usuário / senha / client e imprime o **racional do cálculo** de uma
classificação — *por que* a gleba recebeu aquele nível de manejo: indicadores
avaliados, fatores restritivos e a narrativa do cálculo.

O racional só existe para a classificação **COMPLETA** (preliminar ou em
processamento responde "não disponível"). A projeção depende dos papéis do
usuário na empresa operadora da gleba:

- com `OPERADOR_ANALISE_SOLO` → **completa** (valor, faixa e score de cada indicador)
- sem `OPERADOR_ANALISE_SOLO` → **compacta** (só nome, origem e efeito na nota)

---

## Pré-requisitos

- Python 3.9+
- Pacote `czarsinm` instalado (veja o README raiz do projeto)
- Credenciais de acesso ao SINM (usuário, senha, client ID e client secret)
- Uma `chaveClassificacaoNM` de uma classificação completa

---

## Execução

```bash
cd exemplos/05_racional
python exemplo.py --chave SUA_CHAVE
```

As credenciais são lidas do `.env` (use o `env.example` como referência) ou,
se faltarem, perguntadas no terminal. A chave pode vir em `--chave` ou no prompt.

Opções:

```bash
python exemplo.py --chave SUA_CHAVE --json   # imprime o JSON cru
python exemplo.py                            # pergunta tudo no terminal
```
