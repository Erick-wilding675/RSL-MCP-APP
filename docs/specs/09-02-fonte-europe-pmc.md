# Fonte Europe PMC

**Fase:** 9 · Versão 1.2 · **Situação:** pronta

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
- [x] Teste com respostas simuladas (`httpx.MockTransport`): os campos acima são mapeados, inclusive autor sem ORCID, autor coletivo, várias afiliações, resumo com HTML, `pubYear` ausente, título com ponto final, preprint (`source` `PPR`) e registro sem título descartado
- [x] Teste: a paginação pede o `cursorMark` seguinte e para em `max_results`, na página menor ou no cursor repetido
- [x] Teste: 429 e 5xx seguem as novas tentativas e os estados acima
- [x] Teste: com `RSL_CONTACT_EMAIL`, a URL leva `email`, que não aparece em `query`, `reason` nem `cache_query`
- [x] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

FR-01, FR-03, FR-14, NFR-04, D-004 e D-020. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/sources/crossref.py` e `tests/sources/test_crossref.py` inteiros (o molde) e `src/rslapp/core/models.py`.

Cerca de 300 linhas, testes incluídos. Um commit para o conector e outro para os testes, com D-020 no comentário e no nome dos testes.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/sources/europe_pmc.py`: conector `EuropePMCSource` (e alias `EuropePmcSource`) implementando o protocolo `Source` para a API REST do Europe PMC (`https://www.ebi.ac.uk/europepmc/webservices/rest/search`). Faz busca sequencial com `resultType=core`, `format=json`, `pageSize=min(100, max_results)` e paginação por `cursorMark`. Normaliza metadados com remoção de HTML e ponto final solto em títulos, extração de resumo sem tags e com entidades decodificadas, normalização de DOI minúsculo, ano inteiro de `pubYear`, periódico de `journalInfo.journal.title`, tipo em minúsculas de `pubTypeList.pubType`, palavras-chave únicas sem espaços nas pontas, autores com nome completo / primeiro e último / coletivo, ORCID curto, afiliações de texto, referências vazias (`references=[]`, `references_count=None`), contagem de citações em `citations["europe_pmc"]`, e identificadores de fonte em `source_ids` (`"europe_pmc": "<source>:<id>"` e opcionalmente `"pubmed": "<pmid>"`). Lida com e-mail de contato opcional via `RSL_CONTACT_EMAIL` no parâmetro de URL `email` (sem chave necessária, `needs_key=False`), isolado de `query`, `reason`, `cache_query`, logs e `repr`. Executa novas tentativas com esperas de 1, 2 e 4 s para 429, 5xx, timeout e erros de conexão, preservando os trabalhos já obtidos de páginas anteriores em caso de falha subsequente (**FR-01**, **FR-03**, **FR-14**, **NFR-04**, **D-004**, **D-020**).
  - `tests/sources/test_europe_pmc.py`: suíte completa de testes unitários sem rede com `httpx.MockTransport` e injeção de `sleep`. Cobre mapeamento de campos (autor sem ORCID, autor coletivo, múltiplas afiliações, resumo com tags HTML e entidades, ano ausente, título com ponto final, preprint PPR, descarte de registros sem título), paginação por cursorMark e critérios de parada (atingir `max_results`, página menor que `pageSize`, cursor repetido, cursor ausente, e preservação de páginas parciais em falha), novas tentativas com esperas crescentes em 429, 5xx, timeout e rede, erros sem repetição (400, 403, JSON inválido) e isolamento rigoroso de `RSL_CONTACT_EMAIL` (**FR-01**, **FR-03**, **FR-14**, **NFR-04**, **D-004**, **D-020**).
- **O que foi assumido:**
  - Registros sem título válido (vazio, espaços ou apenas ponto final) são descartados sem interromper a busca, permitindo que a paginação continue para preencher `max_results`.
  - A paginação por cursor encerra se `nextCursorMark` for idêntico ao cursor anterior ou vier nulo/vazio.
- **O que não deu para verificar:**
  - Chamada real com rede aberta à API do Europe PMC (testes executados com `httpx.MockTransport`, conforme regra do projeto de não fazer requisições externas nos testes automatizados).

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
2. **O que deve aparecer:**
   - `All checks passed!` na verificação do `ruff check .`
   - `557 passed` no `pytest` em Python 3.10 e em Python 3.14.
3. **Onde olhar primeiro (pontos de risco, do mais difícil ao mais simples):**
   1. **Isolamento de `RSL_CONTACT_EMAIL` (`src/rslapp/sources/europe_pmc.py` — `EuropePMCSource.search`, `cache_query`, `_request_page`, `__repr__`, NFR-04, D-020):** conferir que o e-mail vai apenas no parâmetro `email` da URL ao Europe PMC e nunca vaza em `SourceResult.query`, `SourceResult.reason`, `cache_query`, logs do `caplog` nem no `repr`.
   2. **Mapeamento de metadados, autores, HTML e IDs (`src/rslapp/sources/europe_pmc.py` — `_parse_work`, `_parse_author`, `_clean_html_text`, `_clean_title`, FR-03, FR-14, D-004, D-020):** verificar a limpeza de tags HTML e ponto final solto em títulos, decodificação de entidades em resumos, mapeamento de autor coletivo (`collectiveName`), autores com múltiplas afiliações, preprints (`source_ids={"europe_pmc": "PPR:..."}` sem `pubmed`), e `source_ids` com `MED:<id>` e `pubmed:<pmid>` quando presentes.
   3. **Paginação com cursorMark e retentativas (`src/rslapp/sources/europe_pmc.py` — `_request_page` e laço em `search`, FR-01, NFR-04, D-020):** confirmar parada correta em `max_results`, em página menor que `pageSize`, em cursor repetido ou ausente, e retentativas com recuo exponencial (1, 2, 4 s) para 429 transitório, 5xx, timeout e rede, mantendo os registros já coletados de páginas anteriores.

**Revisão do Claude (2026-11-11, run `b20261111-144701` do Playmaker):** feita pelo Gemini 3.8 Flash na segunda rodada (a primeira, no Gemini 4 Argon, parou pela cota). Aprovada pelo agente revisor e integrada com os gates refeitos pelo `board integrate`. Conferido: o e-mail só vai no parâmetro `email`, nunca em `query`, `reason`, `cache_query` ou `repr`; a paginação e as novas tentativas fazem o mesmo que a Crossref. Acompanhamentos, não bloqueiam:
- o apelido `EuropePmcSource` (fim de `europe_pmc.py`) não é usado por ninguém;
- `_clean_title` tira todos os pontos finais (`rstrip(".")`), e a spec pede tirar só o ponto solto;
- falta `assert year is None` para o registro sem `pubYear`, e um teste de 429 seguido de 200;
- `str.isdigit()` aceita dígitos Unicode; o mais seguro é `isascii() and isdigit()`;
- o registrador `httpx` grava a URL completa, com o e-mail, em nível INFO. Vale para todas as fontes, não só esta.
