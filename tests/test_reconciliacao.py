from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from etl import carga


def _dados_carga():
    return {
        "produtos": [
            {
                "produto_id": 1,
                "nome": "Adubo",
                "categoria": "Insumo",
                "preco_base": "50,00",
            }
        ],
        "clientes": [
            {
                "id": 1,
                "nome": "Ana",
                "email": None,
                "cidade": "Recife",
                "estado": "PE",
                "cadastro_em": "2026-01-10",
            }
        ],
        "pedidos": [
            {
                "id": 100,
                "cliente_id": 1,
                "data_pedido": "2026-02-01",
                "status": "pago",
                "valor_total": "100,00",
                "valor_itens": "100,00",
                "divergente": False,
            }
        ],
        "itens_pedido": [
            {
                "pedido_id": 100,
                "linha": 1,
                "produto_id": 1,
                "quantidade": 2,
                "preco_unitario": "50,00",
            }
        ],
    }


def _simular_conexao(monkeypatch, linha_reconciliacao):
    cursor = MagicMock()
    cursor.fetchone.return_value = linha_reconciliacao
    conexao = MagicMock()
    conexao.__enter__.return_value = conexao
    conexao.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(
        carga.psycopg,
        "connect",
        lambda **kwargs: conexao,
    )


def test_converte_valores_para_carga():
    assert carga._decimal_para_carga("125,84") == Decimal("125.84")
    assert carga._data_para_carga("2026-03-15") == date(2026, 3, 15)
    assert carga._booleano_para_carga(1) is True
    assert carga._booleano_para_carga(0) is False

    with pytest.raises(ValueError):
        carga._booleano_para_carga(2)


def test_reconciliacao_ok_com_totais_e_contagens_iguais(monkeypatch):
    _simular_conexao(
        monkeypatch,
        (1, 1, 1, 1, Decimal("100.00"), 0),
    )

    resultado = carga.carregar_dados(_dados_carga())

    assert resultado["diferenca"] == Decimal("0.00")
    assert resultado["divergentes_origem"] == 0
    assert resultado["divergentes_destino"] == 0
    assert resultado["reconciliacao_ok"] is True


def test_reconciliacao_detecta_soma_diferente_no_destino(monkeypatch):
    _simular_conexao(
        monkeypatch,
        (1, 1, 1, 1, Decimal("90.00"), 0),
    )

    resultado = carga.carregar_dados(_dados_carga())

    assert resultado["diferenca"] == Decimal("-10.00")
    assert resultado["reconciliacao_ok"] is False


def test_reconciliacao_detecta_contagem_de_divergentes_diferente(monkeypatch):
    _simular_conexao(
        monkeypatch,
        (1, 1, 1, 1, Decimal("100.00"), 1),
    )

    resultado = carga.carregar_dados(_dados_carga())

    assert resultado["divergentes_origem"] == 0
    assert resultado["divergentes_destino"] == 1
    assert resultado["reconciliacao_ok"] is False
