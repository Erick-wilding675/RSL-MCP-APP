# Fonte Europe PMC

**Fase:** 9 · Versão 1.2 · **Situação:** a fazer

## O que faz

O conector `sources/europe_pmc.py`, com a mesma interface das outras fontes (`Source`): busca por termos no Europe PMC, que reúne PubMed, PMC, preprints e outras bases de ciências da vida, e traduz cada resultado para `Work`, com autores, ORCID, afiliações, resumo, palavras-chave e o número de citações.

## O que não faz

- Não entra nas fontes do servidor nem em `server.py`: isso é a 09-03.
- Não traz as referências de cada artigo (seria um pedido por artigo em `/{source}/{id}/references`); `references` fica vazio.
- Não busca por título ou DOI exato nem referências ou citações de um artigo.

## Conferência do T-001 (Europe PMC)

Lida pelo Claude Code em 2026-11-11: a descrição OpenAPI oficial em `https://www.ebi.ac.uk/europepmc/webservices/rest/v3/api-docs` (a página `europepmc.org/RestfulWebService` mostra essa mesma descrição) e uma chamada real a `/search` com `resultType=core`.

- **Busca:** `GET https://www.ebi.ac.uk/europepmc/webservices/rest/search` com:
  - `query`, com a sintaxe do Europe PMC;
  - `resultType` (`idlist`, `lite` ou `core`; o padrão é `lite`);
  - `format=json`;
  - `pageSize` (padrão 25, máximo **1000**);
  - `cursorMark` (`*` no primeiro pedido, depois o `nextCursorMark` da resposta);
  - `synonym` (padrão falso);
  - `sort`;
  - `email` (opcional, registra o e-mail na EBI).
- **Resposta (chamada real):** `hitCount`, `nextCursorMark`, `nextPageUrl`, `request` e `resultList.result`. Cada resultado `core` traz:
  - `id`, `source` (`MED`, `PMC`, `PPR`…), `pmid`, `pmcid`, `doi`, `title`;
  - `pubYear` (texto), `pubTypeList.pubType` (lista) e `journalInfo.journal.title`;
  - `abstractText`, que pode ter marcas HTML;
  - `keywordList.keyword` (lista);
  - `authorList.author`, com `fullName`, `firstName`, `lastName`, `initials`, `authorId` (`{"type": "ORCID", "value": "0000-…"}`) e `authorAffiliationDetailsList.authorAffiliation[].affiliation`;
  - `citedByCount` e `hasReferences`.
- **Limite:** a descrição oficial não declara limite de pedidos por segundo. A chamada real não trouxe cabeçalho de limite.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-11, baratas de desfazer:

1. **Fluxo:** `resultType=core`, `format=json`, `pageSize` = `min(100, max_results)`, paginação por `cursorMark` até `max_results`, até uma página vir menor que `pageSize` ou até o `nextCursorMark` vir igual ao anterior ou ausente. `found` = `hitCount`.
2. **Ritmo:** um pedido por vez, nunca em paralelo, como na Crossref.
3. **E-mail:** com `RSL_CONTACT_EMAIL`, vai no parâmetro `email`, com os mesmos cuidados da Crossref: fica fora de `query`, do cache e dos erros. Não há chave: `needs_key` é falso.
4. **Mapeamento:**
   - `title`: tira as marcas HTML e o ponto final solto que o Europe PMC acrescenta; sem título, o registro é descartado.
   - `doi`: em minúsculas.
   - `year`: `int(pubYear)` quando for número, senão nulo.
   - `venue`: `journalInfo.journal.title`.
   - `abstract`: `abstractText` sem marcas HTML, com as entidades decodificadas e espaços simples.
   - `keywords`: `keywordList.keyword`, sem espaços nas pontas e sem repetir.
   - `type`: o primeiro de `pubTypeList.pubType`, em minúsculas.
   - `authors`: na ordem. `name` = `fullName`, ou `firstName lastName`, ou `collectiveName` quando houver. `orcid` na forma curta, de `authorId` com `type` ORCID. `raw_affiliations` e `affiliations` (`Affiliation(name=texto)`) de `authorAffiliationDetailsList`. `position` nulo.
   - `references` vazio e `references_count` nulo.
   - `citations`: `{"europe_pmc": citedByCount}` quando for número.
   - `source_ids`: `{"europe_pmc": "<source>:<id>"}` (por exemplo `MED:33510057`). Quando houver, também `"pubmed": "<pmid>"`, para a deduplicação e o CSV acharem o mesmo artigo do PubMed.
5. **Estados e novas tentativas**, como nas outras fontes: 429, 5xx, tempo esgotado e erro de rede com até 3 novas tentativas (1, 2 e 4 s); esgotadas, `rate_limited` ou `failed`. Outras 4xx dão `failed` na hora. As páginas já trazidas ficam.
6. **Cache:** `cache_query` devolve `{"source": "europe_pmc", "query": ..., "max_results": ...}`, sem e-mail.

## Pronto quando

- [x] Antes de escrever, conferir o T-001 para o Europe PMC (feito acima pelo Claude Code)
- [ ] Teste com respostas simuladas (`httpx.MockTransport`): os campos acima são mapeados, inclusive autor sem ORCID, autor coletivo, várias afiliações, resumo com HTML, `pubYear` ausente, título com ponto final, preprint (`source` `PPR`) e registro sem título descartado
- [ ] Teste: a paginação pede o `cursorMark` seguinte e para em `max_results`, na página menor ou no cursor repetido
- [ ] Teste: 429 e 5xx seguem as novas tentativas e os estados acima
- [ ] Teste: com `RSL_CONTACT_EMAIL`, a URL leva `email`, que não aparece em `query`, `reason` nem `cache_query`
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

FR-01, FR-03, FR-14, NFR-04, D-004 e D-020. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/sources/crossref.py` e `tests/sources/test_crossref.py` inteiros (o molde) e `src/rslapp/core/models.py`.

Cerca de 300 linhas, testes incluídos. Um commit para o conector e outro para os testes, com D-020 no comentário e no nome dos testes.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
