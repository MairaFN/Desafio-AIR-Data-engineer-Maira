SELECT 'clientes' AS tabela, COUNT(*) AS registros FROM clientes
UNION ALL
SELECT 'produtos', COUNT(*) FROM produtos
UNION ALL
SELECT 'pedidos', COUNT(*) FROM pedidos
UNION ALL
SELECT 'itens_pedido', COUNT(*) FROM itens_pedido
ORDER BY tabela;

WITH itens_por_pedido AS (
    SELECT
        p.id AS pedido_id,
        COALESCE(
            SUM(ip.quantidade * ip.preco_unitario),
            0.00
        )::NUMERIC(12, 2) AS soma_itens
    FROM pedidos AS p
    LEFT JOIN itens_pedido AS ip ON ip.pedido_id = p.id
    GROUP BY p.id
)
SELECT
    COALESCE(SUM(p.valor_itens), 0.00)::NUMERIC(14, 2)
        AS soma_valor_itens_pedidos,
    COALESCE(SUM(i.soma_itens), 0.00)::NUMERIC(14, 2)
        AS soma_itens_calculada,
    COALESCE(SUM(p.valor_itens - i.soma_itens), 0.00)::NUMERIC(14, 2)
        AS diferenca,
    COUNT(*) FILTER (
        WHERE p.valor_itens IS DISTINCT FROM i.soma_itens
    ) AS pedidos_com_valor_itens_inconsistente
FROM pedidos AS p
JOIN itens_por_pedido AS i ON i.pedido_id = p.id;

WITH itens_por_pedido AS (
    SELECT
        p.id AS pedido_id,
        COALESCE(
            SUM(ip.quantidade * ip.preco_unitario),
            0.00
        )::NUMERIC(12, 2) AS soma_itens
    FROM pedidos AS p
    LEFT JOIN itens_pedido AS ip ON ip.pedido_id = p.id
    GROUP BY p.id
)
SELECT
    COUNT(*) FILTER (WHERE p.divergente IS TRUE)
        AS divergentes_armazenados,
    COUNT(*) FILTER (
        WHERE ABS(p.valor_total - i.soma_itens) > 0.01
    ) AS divergentes_calculados,
    COUNT(*) FILTER (
        WHERE p.divergente IS DISTINCT FROM (
            ABS(p.valor_total - i.soma_itens) > 0.01
        )
    ) AS divergentes_inconsistentes
FROM pedidos AS p
JOIN itens_por_pedido AS i ON i.pedido_id = p.id;
