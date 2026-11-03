# Achar um artigo e repetir uma busca

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

## O que faz

As ferramentas `find_work` (por título ou DOI, devolve os candidatos numa lista própria) e `repeat_search` (refaz uma busca do log com as mesmas strings e as mesmas fontes, grava busca e lista novas com `repeated_from`, e não mexe na original).

## O que não faz

Não altera nenhuma busca ou lista já gravada.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **`find_work(title=None, doi=None, request_summary="", sources=None, max_results=10)`:** exatamente um de `title` ou `doi`, senão `invalid_input`; `max_results` de 1 a 100.
2. **Por DOI:** cada fonte ganha `find_by_doi(doi) -> SourceResult`, com uma leitura direta: OpenAlex `GET /works/doi:<doi>` (grátis), Crossref `GET /works/<doi>`, Semantic Scholar `GET /paper/DOI:<doi>` com os mesmos `fields` da busca. Um 404 é `ok` com zero trabalhos. Mesmo mapeamento, chave, novas tentativas e ritmo de cada conector.
3. **Por título:** reaproveita o `search` de cada fonte com o título como consulta e `max_results` pequeno (padrão 10). Os candidatos são juntados pela regra da 03-03.
4. **Gravação:** `kind: "work"` e `params: {"doi" ou "title", "max_results", "sources"}`. Sem resultado, a lista sai vazia e registrada.
5. **`repeat_search(search_id)`:** lê a busca original; se ela não tem `params` (busca gravada antes da 03-03), `invalid_input` com "busca sem parâmetros gravados"; inexistente, `search_not_found`. Roda de novo pelo mesmo caminho do tipo original (`terms` pela busca, `work` pelo `find_work`, `related` pelo `get_related_works`), com os mesmos `params` e as mesmas fontes, e grava busca e lista novas com `kind: "repeat"`, `repeated_from: <id original>`, `params` e `origin` copiados. A original não é tocada.
6. **Onde fica:** `core/find.py` e `core/repeat.py` (sem MCP); as ferramentas em `server.py`.

## Pronto quando

- [ ] Teste: `find_work` por DOI exato devolve o artigo; por título parecido devolve candidatos; sem resultado devolve lista vazia registrada
- [ ] Teste: `repeat_search` usa as strings originais de cada fonte e gera `s-` e `l-` novos, com `repeated_from` apontando para a original
- [ ] Teste: a busca original e a lista original continuam idênticas depois da repetição
- [ ] Teste: se uma fonte usada antes está sem chave, a repetição segue com as outras e marca a falha

## Vem de

FR-02, FR-11, UC-02, UC-03, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefas 03-03 e 04-02 integradas.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
