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

- **O que mudou:**
  - Implementado o método `related` e `get_origin_work` em `src/rslapp/sources/openalex.py` para consulta de citações (`filter=cites:W...`) e referências em lotes de no máximo 100 IDs (`filter=openalex:W1|...`).
  - Implementado o método `related` em `src/rslapp/sources/semantic_scholar.py` para consulta de referências e citações via `/paper/DOI:<doi>/references` e `/citations`, com parada preventiva antes do limite de 10.000 para evitar erro 400.
  - Criado `src/rslapp/core/related.py` com a orquestração `run_related`: resolução do artigo de origem (OpenAlex seguido de Semantic Scholar), consulta concorrente, deduplicação com merge (regra 03-03), aplicação de teto (padrão 1.000 até 10.000) com marcação de lista `incomplete`, gravação de buscas, listas e entrada legível com linha "Artigo de origem" em `log.md`.
  - Adicionada a ferramenta `get_related_works` no servidor MCP `src/rslapp/server.py`.
  - Criadas suítes de testes cobrindo todos os cenários em `tests/sources/test_openalex_related.py`, `tests/sources/test_semantic_scholar_related.py`, `tests/core/test_related.py` e `tests/test_server_related.py`.
- **Requisitos atendidos:** FR-15, FR-08, FR-14, UC-04, D-002, D-005, D-010.
- **O que foi assumido:**
  - A Semantic Scholar exige DOI para trabalhos relacionados; na ausência de DOI, devolve `not_supported` com motivo "artigo de origem sem DOI".
  - A Crossref devolve `not_supported` em ambas as direções com motivo "não suportado pela Crossref", sem campos preenchidos com valores supostos.
  - Artigo de origem inexistente em ambas as fontes levanta erro `work_not_found` e nada é gravado em disco.
- **O que não deu para verificar:**
  - Chamadas reais contra as APIs com chaves de produção (todos os testes usam `httpx.MockTransport`).

## Como testar

Rode a suíte de testes completa da entrega:

```bash
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/test_server_related.py tests/core/test_related.py tests/sources/test_openalex_related.py tests/sources/test_semantic_scholar_related.py -v
```

Deve aparecer: 30 testes passando.

**Onde olhar primeiro (pontos mais arriscados):**
1. **Resolução de artigo inexistente e garantia de não gravação** (`tests/core/test_related.py::test_fr15_artigo_origem_nao_achado_work_not_found_nada_gravado`): confere que o erro `work_not_found` é levantado e nenhuma busca, lista ou log é gravado em disco.
2. **Agrupamento de referências em lotes de até 100 ids** (`tests/sources/test_openalex_related.py::test_fr14_openalex_related_references_lotes_100`): confere que as chamadas ao OpenAlex dividem as referências em batches estritamente `<= 100`.
3. **Parada preventiva antes de 10.000 na Semantic Scholar e corte de teto** (`tests/sources/test_semantic_scholar_related.py::test_d010_s2_limite_10k_fonte` e `tests/core/test_related.py::test_d010_teto_incompleta_com_motivo`): confere que a busca para antes de estourar 10.000 na fonte e que a lista sai marcada como `incomplete` com o motivo registrado.
