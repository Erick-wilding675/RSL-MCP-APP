# Busca, lista e log

**Fase:** 2 · Fatia completa · **Situação:** não iniciada

## O que faz

O miolo de busca em `core/search.py` e a ferramenta `search_works` no servidor. A busca consulta as fontes configuradas (por ora só o OpenAlex), tira as duplicatas dentro da lista (DOI, senão título normalizado), define se a lista é completa ou incompleta, grava a lista, a busca e a linha do log (tarefa 01-03) e devolve a resposta em resumo: `search_id`, `list_id`, `status`, `total`, `page`, `next_page`, `sources` e a primeira página de `works` (25 por página). A busca roda direto, sem etapa de aprovação.

## O que não faz

Não consulta Crossref nem Semantic Scholar (tarefas 03-01 e 03-02). Não deduplica entre fontes (03-03). Não exporta (02-03).

## Pronto quando

- [ ] Teste com fonte simulada: uma busca devolve lista, grava `lists/`, `searches/` e a linha no `log.md`, e os ids de busca e lista aparecem na resposta
- [ ] Teste: dois registros com o mesmo DOI viram um; sem DOI, o mesmo título normalizado vira um; o caso de DOI diferente e título igual fica como dois
- [ ] Teste: com a fonte em `failed`, a lista sai `incomplete` com a fonte e o motivo na resposta e no log (FR-08); com zero resultados, a lista sai vazia e registrada
- [ ] Teste: sem nenhuma fonte disponível, devolve o erro `no_source_available` e não grava lista
- [ ] Teste: a resposta à IA não passa de um resumo por artigo; o registro completo fica na lista salva
- [ ] Teste: cada busca gera uma lista própria; duas buscas seguidas não se juntam

## Vem de

FR-01, FR-04, FR-05, FR-08, FR-09, FR-12, D-002, D-003. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Nenhuma.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
