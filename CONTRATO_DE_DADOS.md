# Contrato de dados — ETL Verdejar

## Escopo e destino

Este documento define o acordo para os dados que entram no ETL, as
transformações esperadas e as quatro tabelas de destino. O banco escolhido é
**PostgreSQL local (Caminho A)**, conforme `insumos_verdejar/schema.sql`.

As etapas de transformação e carga implementam as regras deste contrato em
`etl/transformacao.py` e `etl/carga.py`.

- Clientes e pedidos: API local, rotas `/clientes` e `/pedidos`; as respostas
  paginadas contêm `items` e `total_pages`.
- Produtos: `insumos_verdejar/dados/produtos.csv`, com cabeçalho
  `produto_id,nome,categoria,preco_base`.
- Em cada pedido, a lista de linhas vem na chave `itens`. Cada linha contém
  `produto_id`, `quantidade` e `preco_unitario`.
- Os arquivos em `brutos/` preservam os registros extraídos antes de qualquer
  transformação.

## Regras gerais de carga

1. Validar e transformar os registros extraídos, sem sobrescrever os arquivos
   brutos.
2. Normalizar valores monetários para duas casas decimais usando `Decimal` e
   arredondamento `ROUND_HALF_UP`. Antes de enviar ao driver, `etl/carga.py`
   converte os valores numéricos tratados para `Decimal`, compatível com as
   colunas `NUMERIC`.
3. Normalizar datas para o texto ISO `AAAA-MM-DD`; na carga, converter esses
   valores para objetos `datetime.date`, aceitos pela coluna `DATE`.
4. Carregar primeiro `clientes` e `produtos`, depois `pedidos` e
   `itens_pedido`, respeitando as chaves estrangeiras.
5. Não inventar valores para campos obrigatórios inválidos: rejeitar ou
   encaminhar o registro para tratamento, informando o erro.

## Tabelas de destino

### `clientes`

| Campo | Tipo PostgreSQL | Nulidade | Origem e regra de transformação |
|---|---|---|---|
| `id` | `INTEGER` | `NOT NULL`; chave primária | API `/clientes`, campo `id`. Preservar o identificador numérico e rejeitar valor ausente. |
| `nome` | `TEXT` | `NOT NULL` | API `/clientes`, campo `nome`. Preservar o nome. |
| `email` | `TEXT` | Pode ser nulo | API `/clientes`, campo `email`. **A1:** converter `null`, campo ausente ou texto vazio em `NULL`; contar em `emails_nulos`. |
| `cidade` | `TEXT` | `NOT NULL` | API `/clientes`, campo `cidade`. Preservar a cidade. |
| `estado` | `CHAR(2)` | `NOT NULL`; exatamente 2 letras | API `/clientes`, campo `estado`. **A2:** converter a sigla para maiúsculas (por exemplo, `rs` → `RS`); contar em `estados_padronizados` quando o valor mudar. |
| `cadastro_em` | `DATE` | `NOT NULL` | API `/clientes`, campo `cadastro_em`. Validar e converter para `datetime.date`; serializar como `AAAA-MM-DD` quando necessário. |

### `produtos`

| Campo | Tipo PostgreSQL | Nulidade | Origem e regra de transformação |
|---|---|---|---|
| `produto_id` | `INTEGER` | `NOT NULL`; chave primária | CSV `produtos.csv`, campo `produto_id`. Converter para inteiro e rejeitar valor ausente. |
| `nome` | `TEXT` | `NOT NULL` | CSV `produtos.csv`, campo `nome`. Preservar o nome. |
| `categoria` | `TEXT` | `NOT NULL` | CSV `produtos.csv`, campo `categoria`. Preservar a categoria. |
| `preco_base` | `NUMERIC(10,2)` | `NOT NULL` | CSV `produtos.csv`, campo `preco_base`. Converter para valor decimal com duas casas (**A4**). |

### `pedidos`

| Campo | Tipo PostgreSQL | Nulidade | Origem e regra de transformação |
|---|---|---|---|
| `id` | `INTEGER` | `NOT NULL`; chave primária | API `/pedidos`, campo `id`. **A5:** deduplicar pelo identificador, mantendo a primeira ocorrência e contando as demais em `repetidos_descartados`; rejeitar valor ausente. |
| `cliente_id` | `INTEGER` | `NOT NULL`; chave estrangeira para `clientes.id` | API `/pedidos`, campo `cliente_id`. Preservar o identificador e validar a referência ao cliente. |
| `data_pedido` | `DATE` | `NOT NULL` | API `/pedidos`, campo `data_pedido`. **A3:** aceitar `AAAA-MM-DD` e `DD/MM/AAAA`, normalizar para ISO e, na carga, converter para `datetime.date`; contar cada data válida em `datas_convertidas`. |
| `status` | `TEXT` | `NOT NULL` | API `/pedidos`, campo `status`. Preservar o status recebido. |
| `valor_total` | `NUMERIC(12,2)` | `NOT NULL` | API `/pedidos`, campo `valor_total`. **A4:** aceitar número ou texto com vírgula decimal, converter para decimal com duas casas e contar os valores normalizados em `valores_convertidos`. |
| `valor_itens` | `NUMERIC(12,2)` | `NOT NULL` | Calculado no ETL: soma de `quantidade × preco_unitario` das linhas do pedido, com aritmética decimal e duas casas. **A6.** |
| `divergente` | `BOOLEAN` | `NOT NULL`; `DEFAULT FALSE` | Calculado no ETL. **A6:** gravar `True` quando `abs(valor_total - valor_itens) > 0.01`, senão `False`; a carga converte o indicador para `bool`; contar pedidos marcados com `True` em `divergentes`. |

### `itens_pedido`

| Campo | Tipo PostgreSQL | Nulidade | Origem e regra de transformação |
|---|---|---|---|
| `pedido_id` | `INTEGER` | `NOT NULL`; parte da chave primária e chave estrangeira para `pedidos.id` | API `/pedidos`, identificador `id` do pedido que contém a linha. |
| `linha` | `INTEGER` | `NOT NULL`; parte da chave primária | Calculado no ETL: posição sequencial da linha dentro de `itens`, começando em `1` e preservando a ordem da API. |
| `produto_id` | `INTEGER` | `NOT NULL`; chave estrangeira para `produtos.produto_id` | API `/pedidos`, campo `produto_id` dentro de cada objeto em `itens`. Validar a referência ao produto. |
| `quantidade` | `INTEGER` | `NOT NULL` | API `/pedidos`, campo `quantidade` dentro de cada objeto em `itens`. Converter para inteiro. |
| `preco_unitario` | `NUMERIC(10,2)` | `NOT NULL` | API `/pedidos`, campo `preco_unitario` dentro de cada objeto em `itens`. Converter para decimal com duas casas (**A4**). |

## Armadilhas de qualidade A1–A6

| Regra | Problema e tratamento | Tabela/campo(s) afetado(s) |
|---|---|---|
| **A1** | E-mail nulo, ausente ou vazio vira `NULL`; contabilizar em `emails_nulos`. | `clientes.email` |
| **A2** | Sigla de estado em caixa mista é convertida para maiúsculas; contabilizar valores alterados em `estados_padronizados`. | `clientes.estado` |
| **A3** | Datas `AAAA-MM-DD` e `DD/MM/AAAA` são normalizadas para ISO; a carga converte para `datetime.date`. Contabilizar cada data válida de pedido em `datas_convertidas`. | `clientes.cadastro_em`, `pedidos.data_pedido` |
| **A4** | Valores monetários são arredondados com `Decimal` para duas casas; a carga vincula `Decimal` ao PostgreSQL. `valor_total` também aceita texto com vírgula decimal. `valores_convertidos` conta as conversões nos três campos monetários. | `produtos.preco_base`, `pedidos.valor_total`, `itens_pedido.preco_unitario` |
| **A5** | Pedidos repetidos entre páginas são deduplicados pelo `id`, preservando a primeira ocorrência; contabilizar descartes em `repetidos_descartados`. | `pedidos.id` e suas linhas em `itens_pedido` |
| **A6** | `valor_itens` é calculado pela soma das linhas; `divergente` vale `TRUE` apenas quando a diferença absoluta para `valor_total` excede `0.01`; contabilizar em `divergentes`. | `pedidos.valor_itens`, `pedidos.divergente` |

Os contadores de transformação são calculados sobre os registros efetivamente
considerados para carga: `datas_convertidas` conta cada data válida de pedido
normalizada, independentemente do formato de entrada; `valores_convertidos`
conta cada valor convertido nos campos monetários indicados,
independentemente do formato original. Pedidos
duplicados descartados não voltam a entrar nesses contadores nem em
`divergentes`.
`repetidos_descartados` conta cada ocorrência repetida removida após a
primeira.
