# Referências e citações de um artigo

**Fase:** 4 · Referências e citações · **Situação:** não iniciada

## O que faz

A ferramenta `get_related_works` e o miolo por trás dela, em `core/related.py`. Dado um DOI ou um id do OpenAlex e a direção (`references` ou `citations`), consulta as fontes que entregam o dado (OpenAlex e Semantic Scholar), junta e tira as duplicatas com a regra da 03-03, aplica o teto (padrão 1.000, ajustável) e grava uma lista própria, com a busca ligada ao artigo de origem e à direção. A Crossref aparece como `not_supported`.

## O que não faz

Não busca por tema. Não é chamada dentro de `search_works`. Não troca ids por DOI (os trabalhos vêm completos das fontes).

## Conferência (T-001 e T-005)

Feita pelo Claude Code em 2026-11-03, a partir do que já foi conferido nas specs 02-01, 03-02 e 04-01:

- **OpenAlex, artigo de origem:** `GET /works/doi:<doi>` ou `GET /works/W123` (leitura de um trabalho avulso, grátis), com `select=id,doi,referenced_works`.
- **OpenAlex, referências:** os ids de `referenced_works` são trazidos completos em grupos de até 100, com `filter=openalex:W1|W2|…` e o mesmo `select` da busca (US$ 0,0001 por grupo).
- **OpenAlex, citações:** `filter=cites:W123` com o mesmo `select`, `per_page=100` e a paginação da busca, que para em 10.000 (`page × per_page`).
- **Semantic Scholar:** `GET /paper/DOI:<doi>/references` ou `/citations`, com `offset` e `limit` (até 1.000 por chamada) e `fields` com os mesmos campos da busca (`title,externalIds,abstract,venue,journal,year,publicationTypes,referenceCount,citationCount,authors`), que se aplicam ao `citedPaper` ou ao `citingPaper` de cada item. Fontes de terceiros (research.md) dizem que `offset + limit` acima de 10.000 dá 400 nas citações: o conector para antes disso. O ritmo de 1 chamada por segundo da 03-02 vale aqui também.
- **Crossref:** a lista de referências da Crossref traz só DOIs, sem os metadados, e não há consulta de citações aberta. Fica `not_supported` nas duas direções.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Nas fontes:** `OpenAlexSource.related(doi_or_id, direction, max_results) -> SourceResult` e `SemanticScholarSource.related(doi, direction, max_results) -> SourceResult`, reaproveitando cabeçalhos, chave, novas tentativas, ritmo e mapeamento que já existem. Nunca levantam exceção. A Semantic Scholar precisa do DOI: sem DOI do artigo de origem, devolve `not_supported` com o motivo "artigo de origem sem DOI".
2. **O artigo de origem:** o miolo resolve primeiro no OpenAlex (pega o id e o DOI). Se o OpenAlex não acha e a entrada é um DOI, segue só com a Semantic Scholar. Se nenhuma fonte acha o artigo (OpenAlex responde 404 e a Semantic Scholar 404, ou a entrada é id do OpenAlex inexistente), o erro é `work_not_found` e nada é gravado.
3. **Teto:** `max_results` padrão 1.000, aceito de 1 a 10.000 (D-010). Quando o número que a fonte diz existir passa do que foi trazido por causa do teto ou do limite da fonte, a fonte fica `ok` com o motivo ("teto de 1.000 atingido" ou "limite de 10.000 da fonte") e a **lista sai `incomplete`** (D-010: o corte das relacionadas é dito).
4. **Gravação:** como a busca da 02-02, com `kind: "related"`, `origin: {"work": <DOI ou id>, "direction": "references" | "citations"}` e `params` (como na 03-03, com `doi` ou `work_id`, `direction` e `max_results`). O `log.md` já mostra a linha "Artigo de origem" (01-03).
5. **A ferramenta** `get_related_works(doi=None, work_id=None, direction, request_summary="", sources=None, max_results=1000)` em `server.py`: exatamente um de `doi` ou `work_id`; `direction` só `references` ou `citations`; fora disso, `invalid_input`. Volta no mesmo formato de `search_works`.

## Pronto quando

- [ ] Teste com respostas simuladas: as citações de um artigo viram uma lista própria, ligada ao artigo de origem no log com a direção; o mesmo para as referências
- [ ] Teste: as referências do OpenAlex são pedidas em grupos de no máximo 100 ids
- [ ] Teste: com mais trabalhos que o teto, a lista sai `incomplete` com o motivo; com a Semantic Scholar perto de 10 mil, ela para antes e o limite da fonte é o motivo
- [ ] Teste: a Crossref aparece como `not_supported`, e a Semantic Scholar também quando o artigo de origem não tem DOI; nenhum campo é preenchido com valor suposto
- [ ] Teste: artigo de origem não achado devolve `work_not_found` e não grava lista, busca nem log
- [ ] Teste: os trabalhos que vêm das duas fontes são juntados pela regra da 03-03
- [ ] Teste pelo servidor (`Client(mcp)` com fontes simuladas): a lista entra no log e pode ser exportada em RIS como qualquer outra; entradas inválidas dão `invalid_input`

## Vem de

FR-15, FR-08, FR-14, UC-04, D-005, D-010. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefas 02-03, 03-03 e 04-01 integradas.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
