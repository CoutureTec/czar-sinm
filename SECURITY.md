# Política de Segurança

## Reportando uma Vulnerabilidade

**Não abra uma issue pública** para reportar vulnerabilidades de segurança.

Envie um e-mail para **contato@couturetec.com.br** com:

- Descrição da vulnerabilidade
- Passos para reproduzir
- Impacto potencial
- Versão afetada da biblioteca

Você receberá uma resposta em até **5 dias úteis**. Após a correção ser publicada, o crédito pela descoberta será atribuído ao reportante (salvo solicitação de anonimato).

## Versões suportadas

| Versão | Suporte de segurança |
|--------|----------------------|
| 0.1.x  | ✓ ativa              |

## Escopo

Esta biblioteca é um cliente HTTP — ela não armazena credenciais, não persiste dados e não expõe servidores. Os principais vetores de risco são:

- Vazamento de credenciais via logs ou arquivos `.env` versionados
- Dependências com vulnerabilidades conhecidas (`requests`, `python-dotenv`)

Mantenha sempre as dependências atualizadas e nunca versione arquivos `.env`.
