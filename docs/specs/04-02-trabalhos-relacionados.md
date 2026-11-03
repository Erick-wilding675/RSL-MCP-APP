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

- **O que mudou (Rodada 2):**
  - Validação estrita de entrada no miolo (`core/related.py`): `work_id` aceito estritamente no formato `W[0-9]+` (ASCII) após remoção de prefixos `https://openalex.org/` ou `http://openalex.org/`; `doi` aceito estritamente iniciando com `10.`, sem espaços, caracteres `?#%` nem segmentos `.` ou `..` (preservando caracteres válidos em DOIs como `;`, `<` e `>`). Qualquer violação retorna `invalid_input`.
  - Codificação de caminhos de DOI nos conectores (`openalex.py` e `semantic_scholar.py`) utilizando `urllib.parse.quote(doi, safe="")`, impedindo vazamento de parâmetros e truncamento de rota.
  - Substituição de `isdigit()` por checagem de dígitos exclusivamente ASCII (`[0-9]`) no OpenAlex.
  - Correção na lógica de teto em `openalex.py` e `semantic_scholar.py`: a marcação do motivo do teto não depende de `len(works) >= max_results`, identificando o corte preventivo pela quantidade de referências originais ou parada na paginação mesmo se itens faltarem no lote.
  - Sinal explícito `not_found: bool` nos modelos (`OriginWorkResult` e `SourceResult`) para indicar 404, substituindo comparações de texto frágil.
  - Isolamento do tratamento 404 da Semantic Scholar no fluxo específico de `related` (`_request_related_page`), revertendo `_request_page` ao estado compartilhado original para não afetar `search()`.
  - Tratamento resiliente de falhas de rede/servidor (500, timeout, rate_limited): o OpenAlex retornando 500 não levanta `work_not_found`, mas grava a busca e lista como `incomplete` com o motivo da fonte no log (FR-08).
  - Remoção de cópias duplicadas de `_summarize_work` e `_select_sources` em `core/related.py`, importando-as diretamente de `core/search.py`.
  - Inclusão de testes unitários para isolamento de chaves (enviadas exclusivamente em cabeçalhos, nunca em URLs), Semantic Scholar próximo ao limite de 10.000 sem estourar `offset + limit > 10.000`, descarte de IDs sujos em `openalex:` e preservação de `max_results` em `params`.
- **Requisitos atendidos:** FR-15, FR-08, FR-14, UC-04, D-002, D-005, D-010.
- **O que foi assumido:**
  - A Semantic Scholar exige DOI para trabalhos relacionados; na ausência de DOI, devolve `not_supported` com motivo "artigo de origem sem DOI".
  - A Crossref devolve `not_supported` em ambas as direções com motivo "não suportado pela Crossref", sem campos preenchidos com valores supostos.
  - Artigo de origem inexistente em ambas as fontes (404) levanta erro `work_not_found` e nada é gravado em disco.
- **O que não deu para verificar:**
  - Chamadas reais contra as APIs com chaves de produção (todos os testes usam `httpx.MockTransport`).

## Como testar

Rode a suíte de testes completa da entrega:

```bash
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/test_server_related.py tests/core/test_related.py tests/sources/test_openalex_related.py tests/sources/test_semantic_scholar_related.py -v
```

Deve aparecer: 55 testes passando.

**Onde olhar primeiro (pontos mais arriscados):**
1. **Validação estrita de entrada e sanitização contra path traversal / injeção de parâmetros** (`tests/core/test_related.py::test_fr15_d002_validacao_estrita_doi_e_work_id` e `tests/test_server_related.py::test_fr15_d002_get_related_works_entradas_invalidas`): confere que tentativas de path traversal ou URLs malformadas retornam imediatamente `invalid_input`.
2. **Resolução de falhas 500 do OpenAlex gravando incompleta sem levantar work_not_found** (`tests/core/test_related.py::test_fr08_openalex_500_nao_da_work_not_found_grava_incompleta`): confere que erro 500 do OpenAlex registra a lista `incomplete` com o motivo da fonte e não assume erroneamente que o trabalho inexiste.
3. **Cálculo de teto com itens faltantes e corte preventivo próximo a 10.000** (`tests/sources/test_openalex_related.py::test_d010_openalex_related_teto_atingido_com_item_faltante` e `tests/sources/test_semantic_scholar_related.py::test_d010_s2_limite_10k_fonte_next_9500`): confere que a detecção de teto atinge `incomplete` mesmo com descartes de itens no lote e que a Semantic Scholar limita batches finais sem ultrapassar 10.000.
