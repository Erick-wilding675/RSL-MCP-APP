# Ver uma lista e ver o log

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

## O que faz

As ferramentas `get_list` (por páginas, com `detail="summary"` ou `"full"`) e `get_search_log` (as entradas e o caminho do `log.md`).

## O que não faz

Não cria nem altera listas ou entradas.

## Pronto quando

- [ ] Teste: `get_list` pagina com `page` e `page_size`, devolve `next_page` e respeita `detail`
- [ ] Teste: `get_list` com id inexistente devolve `list_not_found`
- [ ] Teste: `get_search_log` devolve as entradas em ordem, filtra por `search_id` e devolve o caminho do `log.md`
- [ ] Medida: o tamanho da resposta de `get_list` com 100 e 500 artigos em `summary` e em `full`, anotado no T-006

## Vem de

FR-05, FR-12, FR-13, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

T-006. Depende de 02-02.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
