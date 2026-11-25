from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import MagicMock, patch

from etl import carga


class CargaTests(unittest.TestCase):
    def test_carrega_na_ordem_de_fk_com_sql_parametrizado(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (
            1,
            1,
            1,
            1,
            Decimal("10.00"),
            0,
        )
        conexao = MagicMock()
        conexao.__enter__.return_value = conexao
        conexao.cursor.return_value.__enter__.return_value = cursor
        dados = {
            "produtos": [
                {
                    "produto_id": 1,
                    "nome": "Alface",
                    "categoria": "folhas",
                    "preco_base": 3.50,
                }
            ],
            "clientes": [
                {
                    "id": 1,
                    "nome": "Ana",
                    "email": None,
                    "cidade": "Porto Alegre",
                    "estado": "RS",
                    "cadastro_em": "2025-01-02",
                }
            ],
            "pedidos": [
                {
                    "id": 1,
                    "cliente_id": 1,
                    "data_pedido": "2026-03-15",
                    "status": "entregue",
                    "valor_total": 10.00,
                    "valor_itens": 10.00,
                    "divergente": 0,
                }
            ],
            "itens_pedido": [
                {
                    "pedido_id": 1,
                    "linha": 1,
                    "produto_id": 1,
                    "quantidade": 1,
                    "preco_unitario": 10.00,
                }
            ],
        }

        with patch("etl.carga.psycopg.connect", return_value=conexao):
            resultado = carga.carregar_dados(dados)
            resultado_repetido = carga.carregar_dados(dados)

        chamadas_insert = cursor.executemany.call_args_list
        comandos_insert = [chamada.args[0] for chamada in chamadas_insert]
        self.assertEqual(len(chamadas_insert), 8)
        self.assertEqual(
            chamadas_insert[0].args[1][0][3],
            Decimal("3.50"),
        )
        self.assertEqual(
            chamadas_insert[1].args[1][0][5],
            date(2025, 1, 2),
        )
        self.assertIs(
            chamadas_insert[2].args[1][0][6],
            False,
        )
        self.assertEqual(
            chamadas_insert[3].args[1][0][4],
            Decimal("10.00"),
        )
        for offset in (0, 4):
            self.assertIn("produtos", comandos_insert[offset])
            self.assertIn("clientes", comandos_insert[offset + 1])
            self.assertIn("pedidos", comandos_insert[offset + 2])
            self.assertIn("itens_pedido", comandos_insert[offset + 3])
        self.assertTrue(all("%s" in comando for comando in comandos_insert))
        self.assertEqual(cursor.execute.call_count, 4)
        self.assertEqual(
            [chamada.args[0] for chamada in cursor.execute.call_args_list],
            [
                carga.SQL_TRUNCATE,
                carga.SQL_RECONCILIACAO,
                carga.SQL_TRUNCATE,
                carga.SQL_RECONCILIACAO,
            ],
        )
        self.assertTrue(resultado["reconciliacao_ok"])
        self.assertEqual(resultado, resultado_repetido)
        self.assertEqual(conexao.__exit__.call_count, 2)


if __name__ == "__main__":
    unittest.main()
