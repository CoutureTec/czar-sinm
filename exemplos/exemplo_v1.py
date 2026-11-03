"""
Exemplo de integração com a API SiNM — contrato /api/v1.

Para cada gleba da fonte de dados:

  1. cadastra a gleba (talhão, produtor, propriedade, manejo, histórico)
     → recebe a chaveClassificacaoNM
  2. cadastra a análise de solo química e física num único envio
  3. cadastra o sensoriamento remoto
  4. consulta a classificação (ONM) e o racional do cálculo

Uso:
    python exemplo_v1.py                    # fluxo completo, fonte do .env
    python exemplo_v1.py --fonte csv        # lê dados/csv/ em vez do JSON
    python exemplo_v1.py --chave CHAVE      # só consulta ONM e racional
    python exemplo_v1.py --autenticar       # só testa as credenciais

No v1 a cultura-alvo segue como a produção com previsão de plantio e
colheita (o SDK faz a conversão) e a análise química e física pode ir junta.
"""

import comum

args = comum.argumentos("Exemplo de integração com a API SiNM (/api/v1).")
client = comum.criar_cliente(api_version="v1")

comum.autenticar(client)

if args.chave:
    comum.consultar_resultado(client, args.chave)
elif not args.autenticar:
    for envio in comum.carregar_envios(args.fonte, args.dados):
        print(f"\n===== Gleba {envio.id_externo} =====")

        chave = None
        with comum.etapa("Cadastro da gleba"):
            resposta = client.cadastrar_gleba(envio.gleba)
            chave = resposta["chaveClassificacaoNM"]
            print(f"    uuidGleba: {resposta.get('uuidGleba')}")
            print(f"    chave    : {chave}")
        if not chave:
            continue

        with comum.etapa("Análise de solo química e física"):
            resposta = client.cadastrar_analise_solo(envio.analise_solo, chave_classificacao_nm=chave)
            print(f"    resposta: {resposta}")

        with comum.etapa("Sensoriamento remoto"):
            resposta = client.cadastrar_sensoriamento_remoto(envio.sensoriamento, chave_classificacao_nm=chave)
            print(f"    uuidSensoriamentoRemoto: {resposta.get('uuidSensoriamentoRemoto')}")

        comum.consultar_resultado(client, chave)

comum.encerrar()
