# Exemplos

Aqui há exemplos de códigos python que usam a lib cliente.

## [dados_auto_contidos](dados_auto_contidos/)

Todos os dados de talhão, produtor, amostras de solo e sensoriamento remoto estão **codificados diretamente no script Python**. Ideal para um primeiro teste da integração sem precisar preparar nenhum arquivo externo.

→ [Ver README](dados_auto_contidos/README.md)

## [dados_externos](dados_externos/)

Os dados de entrada ficam em **arquivos CSV organizados por subdiretório** (`talhao/`, `analise_solo/`, `sensoriamento_remoto/`). Cada processo tem seu próprio diretório. Os resultados (UUIDs, chave NM, status da classificação) são gravados em `resultado.csv` ao final de cada etapa.

→ [Ver README](dados_externos/README.md)
