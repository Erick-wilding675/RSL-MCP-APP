# Ver uma lista e ver o log

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** pronta

## O que faz

As ferramentas `get_list` (por páginas, com `detail="summary"` ou `"full"`) e `get_search_log` (as entradas e o caminho do `log.md`).

## O que não faz

Não cria nem altera listas ou entradas.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Onde fica:** a leitura e a paginação em `core/views.py` (sem MCP); as duas ferramentas em `server.py` só traduzem, com a mesma conversão de `RSLError` em `ToolError("<código>: <mensagem>")` da 02-02.
2. **`get_list(list_id, page=1, page_size=25, detail="summary")`:** `page` a partir de 1, `page_size` de 1 a 100, `detail` `summary` ou `full`; fora disso, `invalid_input`. Volta `list_id`, `search_id`, `status`, `total`, `page`, `page_size`, `next_page` (ou `null`) e `works`. Em `summary`, cada trabalho tem os mesmos campos do resumo de `search_works` (reaproveite a função da 02-02); em `full`, o `Work.to_dict()` completo, como está na lista salva. Uma página além do fim volta com `works` vazio e `next_page` nulo. Id inexistente ou malformado: `list_not_found`.
3. **`get_search_log(search_id=None, limit=20)`:** `limit` de 1 a 200. Sem `search_id`, as `limit` entradas mais recentes, em ordem cronológica (a mais antiga primeiro). Com `search_id`, só ela; inexistente ou malformado: `search_not_found`. Cada entrada é o JSON da busca como está em `searches/` (sem campos novos). `log_file` é o caminho absoluto do `log.md`, mesmo que ele ainda não exista.
4. **Medida do T-006:** um teste ou script de apoio calcula o tamanho em bytes do JSON de resposta de `get_list` com 100 e 500 trabalhos sintéticos (com 10 autores e 40 referências cada) em `summary` e em `full`, e a entrega anota os quatro números na spec e no T-006 do plano de testes.

## Pronto quando

- [x] Teste: `get_list` pagina com `page` e `page_size`, devolve `next_page` e respeita `detail`
- [x] Teste: `get_list` com id inexistente devolve `list_not_found`
- [x] Teste: `get_search_log` devolve as entradas em ordem, filtra por `search_id` e devolve o caminho do `log.md`
- [x] Medida: o tamanho da resposta de `get_list` com 100 e 500 artigos em `summary` e em `full`, anotado no T-006

## Vem de

FR-05, FR-12, FR-13, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-02 integrada.

## Resultado da entrega

- **O que mudou:**
  - Implementado `src/rslapp/core/views.py` com `get_list_view` e `get_search_log_view` (sem dependência de MCP):
    - `get_list_view`: valida `page` (>= 1), `page_size` (1 a 100) e `detail` (`summary` ou `full`), realiza paginação com `next_page` e resume trabalhos com `_summarize_work` de `search.py` ou retorna `Work.to_dict()` completo.
    - `get_search_log_view`: valida `limit` (1 a 200), retorna as entradas mais recentes em ordem cronológica (a mais antiga primeiro) ou filtra por `search_id`, e devolve o caminho absoluto de `log.md`.
  - Expostas as ferramentas MCP `get_list` e `get_search_log` em `src/rslapp/server.py`, traduzindo `RSLError` para `ToolError("<código>: <mensagem>")`.
  - Adicionados testes unitários em `tests/core/test_views.py` e testes de servidor MCP em memória (`Client(mcp)`) em `tests/test_server_get_list.py`.
  - Realizada a medição T-006 do tamanho de payload JSON UTF-8 compacto com 100 e 500 trabalhos sintéticos (10 autores e 40 referências cada):
    - 100 artigos summary: 55.839 bytes (~54,5 KB)
    - 100 artigos full: 399.239 bytes (~389,9 KB)
    - 500 artigos summary: 278.639 bytes (~272,1 KB)
    - 500 artigos full: 1.995.639 bytes (~1,95 MB)
    - Números anotados no item T-006 de `docs/test-plan.md`.
- **Qual requisito serve:** FR-05, FR-12, FR-13, D-002 e T-006.
- **O que foi assumido:**
  - Páginas além do final da lista devolvem `works: []` e `next_page: None`.
  - `list_id` inexistente ou com formato inválido devolve erro `list_not_found`.
  - `search_id` inexistente ou com formato inválido devolve erro `search_not_found`.
  - `log_file` usa `resolve()` para devolver o caminho absoluto canônico do `log.md`, mesmo que o arquivo ainda não exista.
- **O que não deu para verificar:**
  - Sessão interativa com cliente externo real (testes executados com o cliente em memória do SDK oficial `mcp.Client`).

## Como testar

- **Comandos:**
  ```powershell
  uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
  uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
  uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
  ```
- **O que deve aparecer:**
  - `ruff check .` passa limpo sem erros.
  - `pytest -q` em Python 3.10 e 3.14 mostra todos os testes passando (226 na entrega, antes de entrarem as tarefas seguintes).
- **Onde olhar primeiro:**
  1. *Paginação e corte de metadados em `get_list` (`summary` vs `full`)*: em `tests/core/test_views.py::test_fr12_d002_get_list_view_respeita_detail_summary_e_full` e `test_fr12_d002_get_list_view_paginacao_e_proxima_pagina`.
  2. *Ordem cronológica e janela mais recente em `get_search_log`*: em `tests/core/test_views.py::test_fr05_fr13_d002_get_search_log_ordem_cronologica_e_limite`.
  3. *Tradução de erros no servidor MCP*: em `tests/test_server_get_list.py`, conferindo `list_not_found`, `search_not_found` e `invalid_input` como `ToolError`.

**Acompanhamentos da revisão (não bloqueiam):** o SDK converte tipos antes de chegar ao miolo (`page=True` vira 1, `page="2"` vira 2), igual em `search_works` e `export_list`: fica para uma tarefa transversal de tipos estritos. Faltam testes de `log_file` com `RSL_DATA_DIR` relativo, de `limit=200`, da entrada do log sem campos novos e do `status` de uma lista `incomplete`. As medidas do T-006 usam `json.dumps` padrão; a resposta real pelo MCP é maior (texto indentado mais `structuredContent`).
