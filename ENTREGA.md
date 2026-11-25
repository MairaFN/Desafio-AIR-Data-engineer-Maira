# Entrega Final — Desafio ETL Verdejar (Data Engineer)

- **Aluna:** Maira Fernandes Nunes
- **Data da entrega:** 25/11/2026
- **Banco de destino:** PostgreSQL 18 local (Caminho A — banco `verdejar`, driver `psycopg`)
- **Repositório GitHub:** https://github.com/MairaFN/Desafio-AIR-Data-engineer-Maira
- **Vídeo da defesa oral:** LINK AQUI.

---

## 1. Pull Requests e Branches por Etapa

- **Branch base:** `desafio-final-maira`
- **Parte 1 — Extração e persistência de brutos:** `feature/parte-1-extracao` (commit `365e95b`) — [PR #1](https://github.com/MairaFN/Desafio-AIR-Data-engineer-Maira/pull/1) (merged).

- **Parte 2 — Transformação (A1–A6) e contrato de dados:** `feature/parte-2-transformacao` (commit `15115ff`) — [PR #2](https://github.com/MairaFN/Desafio-AIR-Data-engineer-Maira/pull/2) (merged).

- **Parte 3 — Carga idempotente no PostgreSQL e orquestração:** `feature/parte-3-carga-postgres` (commit `8e4d99d`) — [PR #3](https://github.com/MairaFN/Desafio-AIR-Data-engineer-Maira/pull/3) (merged).

- **Parte 4 — Testes automatizados e consultas de validação:** `feature/parte-4-testes` — [PR #4](https://github.com/MairaFN/Desafio-AIR-Data-engineer-Maira/pull/4) (merged no commit `1ff5305`).

- **Ajustes posteriores da Parte 4:** commit `0a87164` na branch `feature/parte-4-testes`;

- **Parte 5 — Documentação final:** `README.md`, `COMO_USEI_IA.md` e `ENTREGA.md`. LINK AQUI

---

## 2. Evidência da Execução Idempotente e Reconciliação (`python -m etl.main`)

O pipeline completo foi executado **duas vezes consecutivas** contra a API local (`http://127.0.0.1:8000`) e o PostgreSQL local (`verdejar`), utilizando `TRUNCATE TABLE itens_pedido, pedidos, clientes, produtos RESTART IDENTITY` e inserções parametrizadas (`%s`) dentro da mesma transação na ordem das chaves estrangeiras (`produtos` -> `clientes` -> `pedidos` -> `itens_pedido`). Ambas as execuções produziram exatamente os mesmos resultados:

```text
PGPASSWORD configurado: True
extracao: clientes paginas=10 registros=1000
extracao: pedidos paginas=51 registros_brutos=5100
transformacao: pedidos_unicos=5000 repetidos_descartados=100
transformacao: emails_nulos=81 estados_padronizados=151 datas_convertidas=5000 valores_convertidos=1267
divergentes: 238 pedidos com valor_total diferente da soma dos itens
carga: produtos=12 clientes=1000 pedidos=5000 itens_pedido=12455
reconciliacao: soma_valor_itens_origem=311228.75 soma_valor_itens_destino=311228.75 diferenca=0.00
reconciliacao: divergentes_origem=238 divergentes_destino=238
reconciliacao: status=ok
```

O mesmo bloco de resultados foi observado na segunda execução. A variável
`PGPASSWORD` foi configurada na sessão do PowerShell antes de iniciar o ETL; a
senha não foi incluída no código nem nesta evidência.

## 3. Evidências complementares

- **Testes automatizados:** `python -m pytest -q` — **14 passed**.
- **Validação SQL:** as consultas de `consultas_validacao.sql` foram executadas no banco `verdejar` pelo `psql.exe` do PostgreSQL 18 no Windows.
- **Resultado reconciliado:** 12 produtos, 1.000 clientes, 5.000 pedidos, 12.455 itens, soma de `valor_itens` de `311228.75` na origem e no destino, diferença `0.00` e 238 divergências consistentes.
- **Uso de IA:** descrito em [COMO_USEI_IA.md](COMO_USEI_IA.md).
- **Instruções e visão geral:** disponíveis no [README.md](README.md).
