import json
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_BRUTOS = RAIZ_PROJETO / "brutos"
CENTAVO = Decimal("0.01")


def _decimal_monetario(valor):
    texto = str(valor).strip().replace(",", ".") if isinstance(valor, str) else str(valor)
    try:
        numero = Decimal(texto)
        if not numero.is_finite():
            raise ValueError("Valor monetario deve ser finito")
        return numero.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except InvalidOperation as erro:
        raise ValueError(f"Valor monetario invalido: {valor!r}") from erro


def limpar_email(email):
    """A1: se o e-mail for vazio ou nulo, retorna None e True (para contar)."""
    if email is None:
        return None, True

    texto = str(email).strip()
    if texto == "":
        return None, True

    return texto, False


def padronizar_estado(estado):
    """A2: deixa a sigla em maiúsculas e retorna (estado_limpo, mudou)."""
    original = str(estado).strip()
    padronizado = original.upper()
    mudou = padronizado != original
    return padronizado, mudou


def converter_data(data_texto):
    """A3: aceita AAAA-MM-DD ou DD/MM/AAAA e devolve (data_iso, True)."""
    texto = str(data_texto).strip()

    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            data_obj = datetime.strptime(texto, formato)
            return data_obj.strftime("%Y-%m-%d"), True
        except ValueError:
            pass

    raise ValueError(f"Data invalida: {data_texto}")


def converter_valor(valor):
    """A4: normaliza valores monetários a duas casas com aritmética decimal."""
    numero = _decimal_monetario(valor)
    return float(numero), isinstance(valor, str)


def remover_pedidos_duplicados(pedidos):
    """A5: mantém a primeira ocorrência de cada id e conta os repetidos."""
    ids_vistos = set()
    pedidos_unicos = []
    repetidos_descartados = 0

    for pedido in pedidos:
        pedido_id = pedido["id"]
        if pedido_id in ids_vistos:
            repetidos_descartados += 1
        else:
            ids_vistos.add(pedido_id)
            pedidos_unicos.append(pedido)

    return pedidos_unicos, repetidos_descartados


def calcular_divergencia_pedido(valor_total, itens):
    """A6: soma os itens e marca divergente se diferença > 0.01."""
    soma_itens = Decimal("0.00")

    for item in itens:
        quantidade = int(item["quantidade"])
        preco_unitario = _decimal_monetario(item["preco_unitario"])
        soma_itens += Decimal(quantidade) * preco_unitario

    soma_itens = soma_itens.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    total_decimal = _decimal_monetario(valor_total)
    diferenca = abs(total_decimal - soma_itens)
    divergente = diferenca > CENTAVO

    return float(soma_itens), divergente


def transformar_clientes(clientes):
    clientes_tratados = []
    emails_nulos = 0
    estados_padronizados = 0

    for cliente in clientes:
        email_limpo, eh_nulo = limpar_email(cliente.get("email"))
        estado_limpo, mudou_estado = padronizar_estado(cliente.get("estado", ""))

        if eh_nulo:
            emails_nulos += 1
        if mudou_estado:
            estados_padronizados += 1

        novo_cliente = {
            "id": int(cliente["id"]),
            "nome": str(cliente["nome"]).strip(),
            "email": email_limpo,
            "cidade": str(cliente["cidade"]).strip(),
            "estado": estado_limpo,
            "cadastro_em": str(cliente["cadastro_em"]).strip(),
        }
        clientes_tratados.append(novo_cliente)

    return clientes_tratados, emails_nulos, estados_padronizados


def transformar_produtos(produtos):
    produtos_tratados = []
    valores_convertidos = 0

    for produto in produtos:
        preco_base, converteu = converter_valor(produto["preco_base"])
        if converteu:
            valores_convertidos += 1

        novo_produto = {
            "produto_id": int(produto["produto_id"]),
            "nome": str(produto["nome"]).strip(),
            "categoria": str(produto["categoria"]).strip(),
            "preco_base": preco_base,
        }
        produtos_tratados.append(novo_produto)

    return produtos_tratados, valores_convertidos


def transformar_pedidos(pedidos):
    pedidos_unicos, repetidos_descartados = remover_pedidos_duplicados(pedidos)
    pedidos_tratados = []
    itens_tratados = []

    datas_convertidas = 0
    valores_convertidos = 0
    divergentes = 0

    for pedido in pedidos_unicos:
        pedido_id = int(pedido["id"])
        data_formatada, converteu_data = converter_data(pedido["data_pedido"])
        valor_total, converteu_valor = converter_valor(pedido["valor_total"])

        if converteu_data:
            datas_convertidas += 1
        if converteu_valor:
            valores_convertidos += 1

        itens_do_pedido = pedido.get("itens", [])
        valor_itens, eh_divergente = calcular_divergencia_pedido(
            valor_total, itens_do_pedido
        )

        if eh_divergente:
            divergentes += 1

        pedido_tratado = {
            "id": pedido_id,
            "cliente_id": int(pedido["cliente_id"]),
            "data_pedido": data_formatada,
            "status": str(pedido["status"]).strip(),
            "valor_total": valor_total,
            "valor_itens": valor_itens,
            "divergente": 1 if eh_divergente else 0,
        }
        pedidos_tratados.append(pedido_tratado)

        linha_numero = 1
        for item in itens_do_pedido:
            preco_unit, converteu_unit = converter_valor(item["preco_unitario"])
            if converteu_unit:
                valores_convertidos += 1

            item_tratado = {
                "pedido_id": pedido_id,
                "linha": linha_numero,
                "produto_id": int(item["produto_id"]),
                "quantidade": int(item["quantidade"]),
                "preco_unitario": preco_unit,
            }
            itens_tratados.append(item_tratado)
            linha_numero += 1

    contadores = {
        "pedidos_unicos": len(pedidos_unicos),
        "repetidos_descartados": repetidos_descartados,
        "datas_convertidas": datas_convertidas,
        "valores_convertidos": valores_convertidos,
        "divergentes": divergentes,
    }
    return pedidos_tratados, itens_tratados, contadores


def ler_json(caminho):
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def transformar_tudo(pasta_brutos=PASTA_BRUTOS):
    clientes_brutos = ler_json(pasta_brutos / "clientes.json")
    pedidos_brutos = ler_json(pasta_brutos / "pedidos.json")
    produtos_brutos = ler_json(pasta_brutos / "produtos.json")

    clientes, emails_nulos, estados_padronizados = transformar_clientes(clientes_brutos)
    produtos, valores_prod = transformar_produtos(produtos_brutos)
    pedidos, itens_pedido, cont_pedidos = transformar_pedidos(pedidos_brutos)

    dados = {
        "clientes": clientes,
        "produtos": produtos,
        "pedidos": pedidos,
        "itens_pedido": itens_pedido,
    }

    contadores = {
        "pedidos_unicos": cont_pedidos["pedidos_unicos"],
        "repetidos_descartados": cont_pedidos["repetidos_descartados"],
        "emails_nulos": emails_nulos,
        "estados_padronizados": estados_padronizados,
        "datas_convertidas": cont_pedidos["datas_convertidas"],
        "valores_convertidos": cont_pedidos["valores_convertidos"] + valores_prod,
        "divergentes": cont_pedidos["divergentes"],
    }
    return dados, contadores


def main():
    dados, contadores = transformar_tudo()

    print(
        f"transformacao: pedidos_unicos={contadores['pedidos_unicos']} "
        f"repetidos_descartados={contadores['repetidos_descartados']}"
    )
    print(
        f"transformacao: emails_nulos={contadores['emails_nulos']} "
        f"estados_padronizados={contadores['estados_padronizados']} "
        f"datas_convertidas={contadores['datas_convertidas']} "
        f"valores_convertidos={contadores['valores_convertidos']}"
    )
    print(
        f"divergentes: {contadores['divergentes']} pedidos com valor_total "
        "diferente da soma dos itens"
    )
    return dados, contadores


if __name__ == "__main__":
    main()