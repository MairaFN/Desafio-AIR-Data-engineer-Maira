import unittest
from contextlib import redirect_stdout
from http.client import RemoteDisconnected
from io import StringIO
from unittest.mock import patch

from etl.extracao import buscar_paginas


class ExtracaoTests(unittest.TestCase):
    def test_conexao_remotamente_encerrada_e_reportada_sem_excecao(self):
        saida = StringIO()
        with patch(
            "etl.extracao.urlopen",
            side_effect=RemoteDisconnected(
                "Remote end closed connection without response"
            ),
        ):
            with redirect_stdout(saida):
                resultado = buscar_paginas("/pedidos")

        self.assertIsNone(resultado)
        self.assertIn("conexao interrompida", saida.getvalue())
        self.assertIn("API continua em execucao", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
