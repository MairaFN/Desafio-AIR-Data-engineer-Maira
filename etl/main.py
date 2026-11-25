import psycopg

from etl import carga, extracao, transformacao


def main() -> int:
    if not extracao.main():
        return 1

    resultado_transformacao = transformacao.main()
    if resultado_transformacao is None:
        return 1
    dados_tratados, _ = resultado_transformacao

    try:
        resultado_carga = carga.carregar_dados(dados_tratados)
    except (psycopg.Error, ValueError) as erro:
        print(f"erro: carga PostgreSQL nao concluida: {erro}")
        return 1

    carga.imprimir_resultado(resultado_carga)
    return 0 if resultado_carga["reconciliacao_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
