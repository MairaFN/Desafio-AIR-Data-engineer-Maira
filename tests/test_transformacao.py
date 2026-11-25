from copy import deepcopy
import pytest

from etl.transformacao import (
    calcular_divergencia_pedido,
    converter_data,
    converter_valor,
    limpar_email,
    padronizar_estado,
    remover_pedidos_duplicados,
    transformar_clientes,
    transformar_pedidos,
)


def test_a1_email_vazio_ou_nulo_vira_none():
    email_none, nulo_none = limpar_email(None)
    email_vazio, nulo_vazio = limpar_email("   ")
    email_ok, nulo_ok = limpar_email("ana@verdejar.com")

    assert email_none is None
    assert nulo_none is True
    assert email_vazio is None
    assert nulo_vazio is True
    assert email_ok == "ana@verdejar.com"
    assert nulo_ok is False


def test_a2_estado_em_minusculas_vira_maiusculas():
    estado, mudou = padronizar_estado(" rs ")
    assert estado == "RS"
    assert mudou is True

    estado_ok, mudou_ok = padronizar_estado("SP")
    assert estado_ok == "SP"
    assert mudou_ok is False


def test_a3_data_aceita_dois_formatos_e_rejeita_invalida():
    data_iso, ok_iso = converter_data("2026-03-15")
    data_br, ok_br = converter_data("15/03/2026")

    assert data_iso == "2026-03-15"
    assert ok_iso is True
    assert data_br == "2026-03-15"
    assert ok_br is True

    with pytest.raises(ValueError):
        converter_data("31/02/2026")


def test_a4_valor_com_virgula_vira_numero():
    valor, converteu = converter_valor("125,84")
    assert valor == 125.84
    assert converteu is True


def test_a5_pedidos_duplicados_mantem_primeiro():
    primeiro = {"id": 7, "status": "entregue"}
    segundo = {"id": 7, "status": "cancelado"}

    unicos, descartados = remover_pedidos_duplicados([primeiro, segundo])

    assert unicos == [primeiro]
    assert unicos[0]["status"] == "entregue"
    assert descartados == 1


def test_a6_divergencia_maior_que_um_centavo():
    itens = [{"produto_id": 1, "quantidade": 1, "preco_unitario": 10.00}]

    soma_sem_div, div_nao = calcular_divergencia_pedido(10.01, itens)
    assert soma_sem_div == 10.00
    assert div_nao is False

    soma_com_div, div_sim = calcular_divergencia_pedido(10.02, itens)
    assert soma_com_div == 10.00
    assert div_sim is True


def test_transformar_clientes_nao_altera_entrada():
    clientes = [
        {
            "id": 1,
            "nome": "Ana",
            "email": "  ",
            "cidade": "Porto Alegre",
            "estado": "rs",
            "cadastro_em": "2025-01-02",
        }
    ]
    copia = deepcopy(clientes)

    tratados, nulos, estados = transformar_clientes(clientes)

    assert clientes == copia
    assert tratados[0]["email"] is None
    assert tratados[0]["estado"] == "RS"
    assert nulos == 1
    assert estados == 1


def test_transformar_pedidos_gera_linhas_e_contadores():
    pedidos = [
        {
            "id": 10,
            "cliente_id": 1,
            "data_pedido": "15/03/2026",
            "status": "entregue",
            "valor_total": "20,00",
            "itens": [
                {"produto_id": 1, "quantidade": 2, "preco_unitario": "10,00"}
            ],
        },
        {
            "id": 10,
            "cliente_id": 1,
            "data_pedido": "15/03/2026",
            "status": "duplicado",
            "valor_total": "20,00",
            "itens": [
                {"produto_id": 1, "quantidade": 2, "preco_unitario": "10,00"}
            ],
        },
    ]

    pedidos_tratados, itens_tratados, contadores = transformar_pedidos(pedidos)

    assert len(pedidos_tratados) == 1
    assert len(itens_tratados) == 1
    assert itens_tratados[0]["linha"] == 1
    assert contadores["pedidos_unicos"] == 1
    assert contadores["repetidos_descartados"] == 1
    assert contadores["datas_convertidas"] == 1
    assert contadores["divergentes"] == 0