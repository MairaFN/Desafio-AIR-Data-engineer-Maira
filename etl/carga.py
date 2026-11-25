import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import psycopg


SQL_TRUNCATE = (
    "TRUNCATE TABLE itens_pedido, pedidos, clientes, produtos RESTART IDENTITY"
)
SQL_INSERIR_PRODUTOS = """
    INSERT INTO produtos (produto_id, nome, categoria, preco_base)
    VALUES (%s, %s, %s, %s)
"""
SQL_INSERIR_CLIENTES = """
    INSERT INTO clientes (id, nome, email, cidade, estado, cadastro_em)
    VALUES (%s, %s, %s, %s, %s, %s)
"""
SQL_INSERIR_PEDIDOS = """
    INSERT INTO pedidos (
        id, cliente_id, data_pedido, status, valor_total, valor_itens, divergente
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""
SQL_INSERIR_ITENS = """
    INSERT INTO itens_pedido (
        pedido_id, linha, produto_id, quantidade, preco_unitario
    )
    VALUES (%s, %s, %s, %s, %s)
"""
SQL_RECONCILIACAO = """
    SELECT
        (SELECT COUNT(*) FROM produtos),
        (SELECT COUNT(*) FROM clientes),
        (SELECT COUNT(*) FROM pedidos),
        (SELECT COUNT(*) FROM itens_pedido),
        (SELECT COALESCE(SUM(valor_itens), 0.00) FROM pedidos),
        (SELECT COUNT(*) FROM pedidos WHERE divergente IS TRUE)
"""
CENTAVO = Decimal("0.01")


def _decimal_para_carga(valor: Any) -> Decimal:
    if isinstance(valor, bool):
        raise ValueError("valor monetario nao pode ser booleano")
    try:
        texto = (
            valor.strip().replace(",", ".")
            if isinstance(valor, str)
            else str(valor)
        )
        numero = Decimal(texto)
        if not numero.is_finite():
            raise ValueError("valor monetario deve ser finito")
        return numero.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except InvalidOperation as erro:
        raise ValueError(f"valor monetario invalido: {valor!r}") from erro


def _data_para_carga(valor: Any) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return date.fromisoformat(valor.strip())
        except ValueError as erro:
            raise ValueError(f"data invalida para carga: {valor!r}") from erro
    raise ValueError(f"tipo de data invalido para carga: {type(valor).__name__}")


def _booleano_para_carga(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int) and valor in (0, 1):
        return bool(valor)
    raise ValueError(f"divergente deve ser bool ou 0/1: {valor!r}")


def configuracao_conexao() -> dict[str, Any]:
    """Lê a configuração do libpq do ambiente sem incluir senhas no código."""
    try:
        porta = int(os.getenv("PGPORT", "5432"))
    except ValueError as erro:
        raise ValueError("PGPORT deve ser um numero inteiro") from erro

    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": porta,
        "dbname": os.getenv("PGDATABASE", "verdejar"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD"),
        "connect_timeout": 5,
    }


def carregar_dados(dados: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Substitui o conteúdo das tabelas e reconcilia a carga na mesma transação."""
    produtos = dados["produtos"]
    clientes = dados["clientes"]
    pedidos = dados["pedidos"]
    itens_pedido = dados["itens_pedido"]

    soma_origem = sum(
        (_decimal_para_carga(pedido["valor_itens"]) for pedido in pedidos),
        start=Decimal("0.00"),
    )
    divergentes_origem = sum(
        _booleano_para_carga(pedido["divergente"]) for pedido in pedidos
    )
    linhas_produtos = [
        (
            produto["produto_id"],
            produto["nome"],
            produto["categoria"],
            _decimal_para_carga(produto["preco_base"]),
        )
        for produto in produtos
    ]
    linhas_clientes = [
        (
            cliente["id"],
            cliente["nome"],
            cliente["email"],
            cliente["cidade"],
            cliente["estado"],
            _data_para_carga(cliente["cadastro_em"]),
        )
        for cliente in clientes
    ]
    linhas_pedidos = [
        (
            pedido["id"],
            pedido["cliente_id"],
            _data_para_carga(pedido["data_pedido"]),
            pedido["status"],
            _decimal_para_carga(pedido["valor_total"]),
            _decimal_para_carga(pedido["valor_itens"]),
            _booleano_para_carga(pedido["divergente"]),
        )
        for pedido in pedidos
    ]
    linhas_itens = [
        (
            item["pedido_id"],
            item["linha"],
            item["produto_id"],
            item["quantidade"],
            _decimal_para_carga(item["preco_unitario"]),
        )
        for item in itens_pedido
    ]

    with psycopg.connect(**configuracao_conexao()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(SQL_TRUNCATE)
            cursor.executemany(SQL_INSERIR_PRODUTOS, linhas_produtos)
            cursor.executemany(SQL_INSERIR_CLIENTES, linhas_clientes)
            cursor.executemany(SQL_INSERIR_PEDIDOS, linhas_pedidos)
            cursor.executemany(SQL_INSERIR_ITENS, linhas_itens)
            cursor.execute(SQL_RECONCILIACAO)
            (
                produtos_destino,
                clientes_destino,
                pedidos_destino,
                itens_destino,
                soma_destino,
                divergentes_destino,
            ) = cursor.fetchone()

    diferenca = soma_destino - soma_origem
    reconciliacao_ok = (
        produtos_destino == len(produtos)
        and clientes_destino == len(clientes)
        and pedidos_destino == len(pedidos)
        and itens_destino == len(itens_pedido)
        and soma_destino == soma_origem
        and divergentes_destino == divergentes_origem
    )
    return {
        "produtos": produtos_destino,
        "clientes": clientes_destino,
        "pedidos": pedidos_destino,
        "itens_pedido": itens_destino,
        "soma_valor_itens_origem": soma_origem,
        "soma_valor_itens_destino": soma_destino,
        "diferenca": diferenca,
        "divergentes_origem": divergentes_origem,
        "divergentes_destino": divergentes_destino,
        "reconciliacao_ok": reconciliacao_ok,
    }


def imprimir_resultado(resultado: dict[str, Any]) -> None:
    print(
        "carga: "
        f"produtos={resultado['produtos']} "
        f"clientes={resultado['clientes']} "
        f"pedidos={resultado['pedidos']} "
        f"itens_pedido={resultado['itens_pedido']}"
    )
    print(
        "reconciliacao: "
        f"soma_valor_itens_origem={resultado['soma_valor_itens_origem']:.2f} "
        f"soma_valor_itens_destino={resultado['soma_valor_itens_destino']:.2f} "
        f"diferenca={resultado['diferenca']:.2f}"
    )
    print(
        "reconciliacao: "
        f"divergentes_origem={resultado['divergentes_origem']} "
        f"divergentes_destino={resultado['divergentes_destino']}"
    )
    status = "ok" if resultado["reconciliacao_ok"] else "divergencia"
    print(f"reconciliacao: status={status}")
