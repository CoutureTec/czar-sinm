# Contribuindo com o czarnm

Obrigado pelo interesse em contribuir! Este documento descreve o processo para reportar problemas, propor melhorias e enviar código.

## Reportando bugs e sugestões

Abra uma issue no GitHub descrevendo:

- O que você esperava que acontecesse
- O que aconteceu de fato (mensagem de erro, resposta da API, etc.)
- Versão da biblioteca e do Python
- Trecho mínimo de código que reproduz o problema

## Configurando o ambiente de desenvolvimento

```bash
git clone https://github.com/CoutureTec/czar-nm.git czar-client
cd czar-client
pip install -e ".[dev]"
```

As dependências de desenvolvimento (`pytest`, `pytest-mock`, `responses`) são instaladas automaticamente com `[dev]`.

## Rodando os testes

```bash
pytest
```

## Enviando um Pull Request

1. Crie um branch a partir de `main` com um nome descritivo:
   ```bash
   git checkout -b fix/auth-token-expiry
   git checkout -b feat/listar-classificacoes
   ```
2. Faça suas alterações e adicione testes quando aplicável
3. Certifique-se de que todos os testes passam: `pytest`
4. Abra o PR contra `main` com uma descrição clara do que foi alterado e por quê

## Estrutura do projeto

```
src/czarnm/
├── client.py       # ZarcNMClient — métodos públicos da API
├── auth.py         # Autenticação Keycloak com cache de token
├── models.py       # Dataclasses dos payloads
└── exceptions.py   # Hierarquia de erros
exemplos/
├── dados_auto_contidos/   # Exemplo com dados embutidos no script
└── dados_externos/        # Exemplo com dados lidos de CSVs
```

## Convenções

- **Python 3.8+** — não use sintaxe exclusiva de versões mais novas (ex: `str | None` requer 3.10; use `Optional[str]`)
- Mensagens de commit em português ou inglês, no imperativo: `Adiciona suporte a ambiente dev`, `Fix token refresh on 401`
- Sem dependências novas em `[project.dependencies]` sem discussão prévia em issue

## Licença

Ao contribuir, você concorda que seu código será distribuído sob a [MIT License](LICENSE).
