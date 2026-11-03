"""
Exemplo de integração com a API SiNM — contrato /api/v2.

Para cada gleba da fonte de dados:

  1. cadastra a gleba (talhão, produtor, propriedade, manejo, histórico e
     cultura-alvo) → recebe a chaveClassificacaoNM
  2. cadastra a análise de solo química
  3. cadastra a análise de solo física
  4. cadastra o sensoriamento remoto
  5. consulta a classificação (ONM) e o racional do cálculo

Uso:
    python exemplo_v2.py                    # fluxo completo, fonte do .env
    python exemplo_v2.py --fonte csv        # lê dados/csv/ em vez do JSON
    python exemplo_v2.py --chave CHAVE      # só consulta ONM e racional
    python exemplo_v2.py --autenticar       # só testa as credenciais

No v2 a gleba leva a cultura-alvo em campo próprio, a análise química e a
física vão em rotas separadas e o cnpjLaboratorio é obrigatório.
"""

import comum

args = comum.argumentos("Exemplo de integração com a API SiNM (/api/v2).")
client = comum.criar_cliente(api_version="v2")

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

        # A análise vem da fonte com as duas metades; no v2 cada uma tem sua rota.
        quimica, fisica = envio.analise_solo.separar()

        with comum.etapa("Análise de solo química"):
            resposta = client.cadastrar_analise_solo_quimica(quimica, chave_classificacao_nm=chave)
            print(f"    uuidAnaliseSolo: {resposta.get('uuidAnaliseSolo')}")

        if fisica:
            with comum.etapa("Análise de solo física"):
                resposta = client.cadastrar_analise_solo_fisica(fisica, chave_classificacao_nm=chave)
                print(f"    uuidAnaliseSolo: {resposta.get('uuidAnaliseSolo')}")

        with comum.etapa("Sensoriamento remoto"):
            resposta = client.cadastrar_sensoriamento_remoto(envio.sensoriamento, chave_classificacao_nm=chave)
            print(f"    uuidSensoriamentoRemoto: {resposta.get('uuidSensoriamentoRemoto')}")

        comum.consultar_resultado(client, chave)

comum.encerrar()
