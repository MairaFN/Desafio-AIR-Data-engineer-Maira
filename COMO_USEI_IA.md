# Como usei IA — ETL Verdejar

## Escopo e justificativa de uso

Utilizei assistentes de IA (GitHub Copilot no VS Code e assistência de chat) como apoio técnico durante o desenvolvimento do pipeline ETL do projeto Verdejar (PostgreSQL local — Caminho A), para acelerar a estruturação do código, revisar aderência aos requisitos e esquemas, escrever testes automatizados e organizar a documentação.

Ao longo do processo, a assistência atuou em diferentes momentos das etapas de extração, transformação, carga, testes e documentação. Reconheço que o uso foi amplo em trechos do pipeline e que a responsabilidade técnica e a explicação de cada parte na defesa oral são minhas, motivo pelo qual revisei, testei e validei os comportamentos manualmente.

## Sugestões aceitas

1. **Tratamento de `RemoteDisconnected` e mensagens sem traceback na extração (`etl/extracao.py`):** aceitei capturar a desconexão do servidor HTTP durante `/pedidos` e reportar mensagens em texto simples em vez de deixar a exceção estourar sem tratamento.
2. **Estrutura da carga transacional e idempotente no PostgreSQL (`etl/carga.py` e `etl/main.py`):** aceitei o uso de `TRUNCATE TABLE ... RESTART IDENTITY` seguido de `INSERT` parametrizado (`%s`) na ordem das chaves estrangeiras (`produtos`, `clientes`, `pedidos`, `itens_pedido`) e leitura de credenciais via variáveis de ambiente (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`), sem gravar senhas no código.
3. **Alinhamento do contador `valores_convertidos` com a evidência real (`CONTRATO_DE_DADOS.md` e `tests/test_transformacao.py`):** aceitei definir explicitamente que `valores_convertidos` contabiliza valores monetários recebidos como texto (preservando o `1267` apurado nos dados reais) e incluir a verificação de entrada numérica (`94.34`) sem incrementar esse contador.

## Sugestões rejeitadas ou adaptadas

1. **Mudança do banco de destino para SQLite (Caminho C) no contrato inicial:** em um primeiro momento o contrato foi redigido apontando para SQLite (`schema_sqlite.sql`), mas rejeitei manter esse rumo para a carga principal e alinhei o contrato ao PostgreSQL local (`schema.sql`), que já estava configurado no ambiente.
2. **Commit único abrangendo todas as alterações:** quando foi sugerido criar uma única branch e um único commit com todas as mudanças do pipeline, rejeitei o formato agrupado e organizei os commits e branches separadamente por etapa/parte para revisão individual.
3. **Execução direta de `psql` sem caminho completo no Windows:** o comando `psql` direto não funcionou no PowerShell porque o executável não estava no `PATH`; adaptei a execução para chamar `psql.exe` pelo caminho completo do PostgreSQL 18 (`C:\Program Files\PostgreSQL\18\bin\psql.exe`).

## Falhas, limitações e retrabalho

1. **Desconexão HTTP (`RemoteDisconnected`) durante a extração de `/pedidos`:** na primeira execução do fluxo completo após configurar `PGPASSWORD`, a extração de clientes concluiu (`1000` registros em `10` páginas), mas a requisição de `/pedidos` sofreu `RemoteDisconnected` com traceback não tratado. Foi necessário ajustar `etl/extracao.py`, adicionar teste em `tests/test_extracao.py` e repetir a execução com a API ativa.
2. **Ausência de `PGPASSWORD` no ambiente de execução e necessidade de execução repetida:** a carga real no PostgreSQL exigiu configurar `PGPASSWORD` de forma segura na sessão do PowerShell e rodar `python -m etl.main` duas vezes seguidas para comprovar a idempotência (`status=ok` em ambas as execuções, com `12` produtos, `1000` clientes, `5000` pedidos, `12455` itens, `diferenca=0.00` e `238` divergentes).
3. **Reorganização do commit de testes/reconciliação entre a Parte 3 e a Parte 4:** o commit inicial de testes e consultas SQL (`test_reconciliacao.py` e `consultas_validacao.sql`) entrou na branch da Parte 3 e precisou ser movido/reorganizado para a branch da Parte 4 (`feature/parte-4-testes`), mantendo a Parte 3 focada na carga e orquestração.
4. **Falhas de diagnóstico do Pylance / ausência de `psql` no `PATH`:** durante a edição ocorreram timeouts na verificação estática do editor, exigindo validação via compilação/testes Python (`python -m py_compile` e `python -m pytest`), além do uso do caminho explícito do `psql.exe` no Windows.

## Como validei o resultado

- **Testes automatizados:** executei `python -m pytest` / `python -m pytest -q`, obtendo `14 passed` cobrindo extração, transformação (A1–A6), carga e reconciliação.
- **Execução real e idempotência:** rodei o fluxo completo duas vezes consecutivas contra a API local e o PostgreSQL (`verdejar`), verificando as mesmas contagens, `diferenca=0.00` e `status=ok`.
- **Validação SQL no banco:** executei `consultas_validacao.sql` no banco `verdejar` via `psql.exe` e conferi os resultados e a evidência visual registrada no `README.md`.