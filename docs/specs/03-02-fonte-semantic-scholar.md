# Fonte Semantic Scholar

**Fase:** 3 · Mais fontes · **Situação:** pronta

## O que faz

O conector `sources/semantic_scholar.py`, com a interface `Source` da tarefa 02-01: busca por termos e tradução para `Work` (título, DOI, ano, periódico, resumo, tipo, autores com nome e id, número de referências e de citações, id do artigo na Semantic Scholar). Chave opcional, uma chamada por vez (com pelo menos 1 segundo entre elas) e novas tentativas em 429 e 5xx. Sem chave devolve os resultados que conseguir e o estado `rate_limited` quando o pool compartilhado recusar.

## O que não faz

Não traz a lista de quem cita um artigo nem a de referências (04-02). Não busca ORCID nem afiliações dos autores, que pediriam uma chamada a mais por autor (ver a conferência). Não deduplica entre fontes (03-03). Não mexe em `server.py`: a fonte entra nas fontes do servidor e em `list_sources` na 03-03.

## Conferência do T-001 (Semantic Scholar)

Lida pelo Claude Code em 2026-11-03 no OpenAPI oficial (`api.semanticscholar.org/graph/v1/swagger.json`), no tutorial (`semanticscholar.org/product/api/tutorial`) e no e-mail de aprovação da chave do Erick.

- **Chave:** cabeçalho `x-api-key` (o nome diferencia maiúsculas). A do Erick dá **1 requisição por segundo, somando todos os endpoints**. Sem chave, o pool é compartilhado com todo mundo: as chamadas de teste de 2026-11-03 sem chave voltaram 429 quase sempre.
- **Busca por relevância:** `GET https://api.semanticscholar.org/graph/v1/paper/search?query=<termos>&offset=<n>&limit=<n>&fields=<campos>`. `limit` no máximo 100. Devolve no máximo 1.000 resultados (e até 10 MB por vez). Resposta: `total` (aproximado), `offset`, `next` (ausente quando acaba) e `data`. Termos com hífen não casam: trocar hífen por espaço na consulta.
- **Campos do artigo usados:** `paperId` (sempre vem), `externalIds` (objeto; a chave `DOI` quando há), `title`, `abstract` (pode faltar por motivo legal), `venue`, `journal` (`name`), `year`, `publicationTypes`, `referenceCount`, `citationCount`, `authors` (por padrão vêm `authorId` e `name`).
- **Subcampos de autor** (`externalIds` com ORCID, `affiliations`): existem no esquema, mas a documentação da busca indica o formato `author.url` e não deixa claro se a busca por relevância os aceita. Um campo não aceito devolve 400 ("Unrecognized or unsupported fields") e derruba a página inteira. **Por isso a primeira versão pede só `authors`**, e a confirmação com uma chamada real fica para o Erick (ver "Como testar").
- **Erros:** 400 com `{"error": "..."}` para campo ou parâmetro inválido; 429 para limite.
- **Referências e citações** de um artigo ficam nos endpoints `/paper/{id}/references` e `/paper/{id}/citations` (até 1.000 por chamada), usados na 04-02, não aqui.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Campos pedidos:** `fields=title,externalIds,abstract,venue,journal,year,publicationTypes,referenceCount,citationCount,authors`.
2. **Mapeamento:** `title` (sem título, descarta); `doi` = `externalIds.DOI` minúsculo; `year`; `venue` = `journal.name` ou, sem ele, `venue`; `abstract`; `type` = o primeiro de `publicationTypes`; `keywords` vazio; `authors` na ordem com `name` e `ids["semantic_scholar"] = authorId`, sem ORCID nem afiliação; `references` vazio; `references_count` = `referenceCount`; `citations` = `{"semantic_scholar": citationCount}`; `source_ids` = `{"semantic_scholar": paperId}`.
3. **Ritmo:** uma chamada por vez em todo o processo, com pelo menos 1 segundo entre o início de uma e o da seguinte, com ou sem chave. A trava e o relógio ficam no nível do módulo, para a 04-02 reaproveitar. O relógio e a espera são injetáveis para os testes.
4. **Estados:** a chave é opcional, então a fonte nunca dá `missing_key`. 429, 5xx, tempo esgotado e erro de rede com até 3 novas tentativas (1, 2 e 4 s, somadas ao ritmo); esgotadas, `rate_limited` (429) ou `failed`; 400 e outras 4xx `failed` na hora, com o texto do `error` da API no motivo (sem a chave). Páginas já trazidas ficam.
5. **A chave** é lida de `SEMANTIC_SCHOLAR_API_KEY` na hora da chamada e vai só no cabeçalho, como no OpenAlex.

## Pronto quando

- [x] Antes de escrever, conferir o T-001 para a Semantic Scholar (feito acima pelo Claude Code)
- [x] Teste com respostas simuladas: os campos acima são mapeados, e o que falta (`abstract`, `journal`, `externalIds` sem DOI, `year` nulo) fica vazio
- [x] Teste: paginação por `offset` para em `max_results`, quando `next` some ou nos 1.000
- [x] Teste: as chamadas saem uma por vez, com pelo menos um segundo entre elas, com e sem chave (relógio falso)
- [x] Teste: sem chave, um 429 que persiste dá `rate_limited` e não derruba a busca; com chave, ela vai no cabeçalho `x-api-key` e não aparece na URL, no `query`, no `reason` nem no `repr`
- [x] Teste: um 400 vira `failed` com o motivo, sem novas tentativas

## Vem de

FR-01, FR-03, FR-08, FR-14, NFR-03, NFR-04, D-004. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-01 integrada. Roda em paralelo com a 02-02 e a 03-01. A chave da Semantic Scholar foi aprovada em 2026-11-03 e vai para o Lore secrets (`SEMANTIC_SCHOLAR_API_KEY`); os testes não a usam.

## Resultado da entrega

- **O que mudou:** Implementado o conector `SemanticScholarSource` em `src/rslapp/sources/semantic_scholar.py` em conformidade com o protocolo `Source` (`name = "semantic_scholar"`, `needs_key = False`), com busca por relevância na API Graph da Semantic Scholar (`/graph/v1/paper/search`), substituição de hífens por espaços nos termos de busca, paginação por offset até `max_results` (com teto em 1.000 itens), aceitação de `total` numérico ou em texto com dígitos (`int`), conversão completa de metadados para `Work` (selecionando o primeiro tipo de `publicationTypes`), ritmo em nível de módulo (trava `asyncio.Lock` serializando chamadas concorrentes com pelo menos 1 segundo entre inícios, relógio e espera injetáveis), retentativas exponenciais (`1`, `2`, `4` s) para 429, 5xx, timeout e rede, erro 400 com falha imediata trazendo o motivo retornado pela API, e preservação dos trabalhos obtidos em páginas anteriores em caso de falha. Criada suíte completa de testes em `tests/sources/test_semantic_scholar.py` cobrindo concorrência com `asyncio.gather`, teto de 1.000 com descarte sem título, mapeamento, paginação, retentativas com sequência exata `[1, 2, 4]`, erros e isolamento de chave sem chamadas externas (`httpx.MockTransport`).
- **Qual requisito serve:** FR-01 (busca por termos técnicos), FR-03 (metadados e autores), FR-08 (tratamento de falhas, ritmo e rate_limited), FR-14 (contagens de citações e referências), NFR-03 (segurança e isolamento da chave opcional), NFR-04 (retentativas com espera exponencial e ritmo serializado), D-004 (dados dos autores).
- **O que foi assumido:** A busca solicita apenas o campo `authors` (sem subcampos `externalIds`/ORCID nem `affiliations`) para evitar respostas 400 da API da Semantic Scholar na busca por relevância; a chave `SEMANTIC_SCHOLAR_API_KEY` é estritamente opcional e lida dinamicamente de `os.environ` no momento da requisição.
- **O que não deu para verificar:** A chamada real à API da Semantic Scholar com a chave aprovada do Erick (`SEMANTIC_SCHOLAR_API_KEY`), reservada para o Erick conferir a resposta 200 com os campos da spec (ver "Como testar").

## Como testar

1. **Comandos para rodar (testes automatizados e verificação estática):**
   ```bash
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/sources/test_semantic_scholar.py -v
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```

2. **O que deve aparecer:**
   - `All checks passed!` no `ruff check .`
   - 13 testes aprovados (`13 passed`) em `test_semantic_scholar.py`, e 60 aprovados na suíte completa.

3. **Chamada real com SEMANTIC_SCHOLAR_API_KEY (para o Erick):**
   Com a variável de ambiente `SEMANTIC_SCHOLAR_API_KEY` configurada (ou via Lore secrets), confirmar que a busca por relevância com os `fields` da spec responde HTTP 200:
   ```bash
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev python -c "
   import asyncio
   from rslapp.sources.semantic_scholar import SemanticScholarSource

   async def main():
       source = SemanticScholarSource()
       res = await source.search('graph neural networks', max_results=10)
       print('Status:', res.status)
       print('Found:', res.found)
       print('Fetched:', res.fetched)
       if res.works:
           w = res.works[0]
           print('Primeiro artigo:', w.title)
           print('DOI:', w.doi)
           print('Tipo:', w.type)
           print('Citações:', w.citations)
           print('Autores:', [a.name for a in w.authors[:3]])

   asyncio.run(main())
   "
   ```
   Deve exibir `Status: ok`, `Found` com total de artigos encontrados (número inteiro positivo), `Fetched: 10`, e o primeiro artigo com metadados preenchidos (título, DOI minúsculo, tipo e citações).

4. **Onde olhar primeiro (pontos de risco, do mais difícil ao mais simples):**
   1. **Isolamento, leitura e validação da chave de API (`src/rslapp/sources/semantic_scholar.py` — `search`, `_is_valid_api_key`, cabeçalho `x-api-key`, NFR-03):** conferir que `SEMANTIC_SCHOLAR_API_KEY` é estritamente opcional, lida do ambiente na hora da chamada, enviada apenas no cabeçalho `x-api-key`, rejeitada com motivo fixo se tiver caracteres não-ASCII ou espaços, e nunca vaza em URL, query, reason, repr, cache_query ou logs.
   2. **Ritmo serializado e limite de taxa em nível de módulo (`src/rslapp/sources/semantic_scholar.py` — `RATE_LOCK`, `rate_limited_call`, FR-08, NFR-04):** conferir que a trava `asyncio.Lock` serializa chamadas simultâneas (provado no teste com `asyncio.gather`), garante pelo menos 1 segundo entre os inícios de chamadas (com e sem chave, e entre tentativas), e que 429 persistente devolve estado `rate_limited` sem derrubar o processo.
   3. **Paginação, parada nos 1.000 e mapeamento de campos (`src/rslapp/sources/semantic_scholar.py` — `search`, `_parse_work`, FR-01, FR-03, FR-14, D-004):** conferir descarte de itens sem título, seleção do primeiro tipo de `publicationTypes`, aceitação de `total` numérico ou em string de dígitos (`"15117"`), parada nos 1.000 resultados antes de requisitar offset >= 1000 (provado no teste com descarte), e preservação dos trabalhos obtidos em páginas anteriores em caso de falha.
