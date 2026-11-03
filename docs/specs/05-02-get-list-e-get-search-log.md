# Ver uma lista e ver o log

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

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

- [ ] Teste: `get_list` pagina com `page` e `page_size`, devolve `next_page` e respeita `detail`
- [ ] Teste: `get_list` com id inexistente devolve `list_not_found`
- [ ] Teste: `get_search_log` devolve as entradas em ordem, filtra por `search_id` e devolve o caminho do `log.md`
- [ ] Medida: o tamanho da resposta de `get_list` com 100 e 500 artigos em `summary` e em `full`, anotado no T-006

## Vem de

FR-05, FR-12, FR-13, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-02 integrada.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
