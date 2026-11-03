# Fonte Semantic Scholar

**Fase:** 3 · Mais fontes · **Situação:** não iniciada

## O que faz

O conector `sources/semantic_scholar.py`, com a interface `Source` da tarefa 02-01: busca por termos e tradução para `Work` (título, DOI, ano, periódico, resumo, tipo, autores com nome e id, número de referências e de citações, id do artigo na Semantic Scholar). Chave opcional, uma chamada por vez (com pelo menos 1 segundo entre elas) e novas tentativas em 429 e 5xx. Sem chave devolve os resultados que conseguir e o estado `rate_limited` quando o pool compartilhado recusar. A fonte passa a entrar nas fontes que o servidor monta.

## O que não faz

Não traz a lista de quem cita um artigo nem a de referências (04-02). Não busca ORCID nem afiliações dos autores, que pediriam uma chamada a mais por autor (ver a conferência). Não deduplica entre fontes (03-03).

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
6. **`list_sources`** continua dizendo `configured: true` e `needs_key: false`, e ganha a informação de que a chave melhora o limite: o campo `status` fica `ok` e a descrição da ferramenta (docstring) diz que a chave é opcional e evita recusas por limite.

## Pronto quando

- [x] Antes de escrever, conferir o T-001 para a Semantic Scholar (feito acima pelo Claude Code)
- [ ] Teste com respostas simuladas: os campos acima são mapeados, e o que falta (`abstract`, `journal`, `externalIds` sem DOI, `year` nulo) fica vazio
- [ ] Teste: paginação por `offset` para em `max_results`, quando `next` some ou nos 1.000
- [ ] Teste: as chamadas saem uma por vez, com pelo menos um segundo entre elas, com e sem chave (relógio falso)
- [ ] Teste: sem chave, um 429 que persiste dá `rate_limited` e não derruba a busca; com chave, ela vai no cabeçalho `x-api-key` e não aparece na URL, no `query`, no `reason` nem no `repr`
- [ ] Teste: um 400 vira `failed` com o motivo, sem novas tentativas
- [ ] `list_sources` mostra a fonte como configurada com ou sem chave e diz que a chave melhora o limite; o servidor passa a consultá-la em `search_works` (teste pelo servidor com fontes simuladas)

## Vem de

FR-01, FR-03, FR-08, FR-14, NFR-03, NFR-04, D-004. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefas 02-01 e 02-02 integradas. A chave da Semantic Scholar foi aprovada em 2026-11-03 e vai para o Lore secrets (`SEMANTIC_SCHOLAR_API_KEY`); os testes não a usam.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
