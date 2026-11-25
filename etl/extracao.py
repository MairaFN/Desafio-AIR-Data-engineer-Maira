import csv
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


URL_BASE = "http://127.0.0.1:8000"
PAGE_SIZE = 100
RAIZ_PROJETO = Path(__file__).resolve().parent.parent


def buscar_paginas(rota, page_size=PAGE_SIZE):
    registros = []
    pagina = 1
    total_paginas = 1

    while pagina <= total_paginas:
        url = f"{URL_BASE}{rota}?page={pagina}&page_size={page_size}"

        try:
            with urlopen(url, timeout=10) as resposta:
                if resposta.status != 200:
                    print(f"erro: status HTTP {resposta.status} em {url}")
                    return None
                conteudo = resposta.read().decode("utf-8")
                dados = json.loads(conteudo)
        except URLError as erro:
            print(f"erro: falha ao acessar {url} -> {erro}")
            return None
        except ConnectionError as erro:
            print(
                f"erro: conexao interrompida ao acessar {url} -> {erro}; "
                "confirme que a API continua em execucao"
            )
            return None
        except TimeoutError as erro:
            print(f"erro: tempo limite ao acessar {url} -> {erro}")
            return None
        except (json.JSONDecodeError, UnicodeDecodeError) as erro:
            print(f"erro: JSON invalido em {url} -> {erro}")
            return None

        if not isinstance(dados, dict):
            print(f"erro: resposta invalida em {url}; objeto JSON esperado")
            return None
        itens = dados.get("items")
        paginas_informadas = dados.get("total_pages")
        if (
            not isinstance(itens, list)
            or not isinstance(paginas_informadas, int)
            or isinstance(paginas_informadas, bool)
            or paginas_informadas < 1
        ):
            print(f"erro: resposta invalida em {url}; items/total_pages ausentes")
            return None
        if pagina == 1:
            total_paginas = paginas_informadas
        elif paginas_informadas != total_paginas:
            print(f"erro: total_pages mudou durante a extracao de {rota}")
            return None

        for item in itens:
            registros.append(item)

        pagina += 1

    return registros, total_paginas


def salvar_json(caminho_arquivo, dados):
    try:
        with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
    except OSError as erro:
        print(f"erro: nao foi possivel salvar {caminho_arquivo}: {erro}")
        return False
    return True


def ler_produtos_csv(caminho_csv):
    produtos = []
    with open(caminho_csv, "r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            produtos.append(linha)
    return produtos


def main() -> bool:
    pasta_brutos = RAIZ_PROJETO / "brutos"
    try:
        pasta_brutos.mkdir(parents=True, exist_ok=True)
    except OSError as erro:
        print(f"erro: nao foi possivel criar {pasta_brutos}: {erro}")
        return False

    resultado_clientes = buscar_paginas("/clientes", PAGE_SIZE)
    if resultado_clientes is None:
        return False
    clientes, paginas_clientes = resultado_clientes
    if not salvar_json(pasta_brutos / "clientes.json", clientes):
        return False
    print(f"extracao: clientes paginas={paginas_clientes} registros={len(clientes)}")

    resultado_pedidos = buscar_paginas("/pedidos", PAGE_SIZE)
    if resultado_pedidos is None:
        return False
    pedidos, paginas_pedidos = resultado_pedidos
    if not salvar_json(pasta_brutos / "pedidos.json", pedidos):
        return False
    print(f"extracao: pedidos paginas={paginas_pedidos} registros_brutos={len(pedidos)}")

    caminho_csv = RAIZ_PROJETO / "insumos_verdejar" / "dados" / "produtos.csv"
    try:
        produtos = ler_produtos_csv(caminho_csv)
    except (OSError, UnicodeError, csv.Error) as erro:
        print(f"erro: nao foi possivel ler o CSV de produtos: {erro}")
        return False
    if not salvar_json(pasta_brutos / "produtos.json", produtos):
        return False
    return True


if __name__ == "__main__":
    main()