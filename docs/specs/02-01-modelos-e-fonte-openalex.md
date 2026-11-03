# Modelos e fonte OpenAlex

**Fase:** 2 · Fatia completa · **Situação:** não iniciada

## O que faz

Os modelos do miolo (`Work`, `Author`, `Affiliation`, `SourceResult`) em `core/models.py`, os erros do miolo em `core/errors.py`, a interface comum das fontes em `sources/base.py` e o conector `sources/openalex.py`. O conector monta a consulta de busca, usa `per_page=100`, `select` para trazer só os campos necessários, a chave de API, e traduz o resultado para `Work`. Em cada autor guarda nome, ORCID, id do autor no OpenAlex e as afiliações com seus ids (incluindo o ROR). Guarda também as referências (`referenced_works`, como ids) e o número de citações (`cited_by_count`). Espera e tenta de novo (até 3 vezes, 1 s, 2 s, 4 s) em 429 e 5xx; trata a paginação básica, que para em 10 mil resultados; devolve o estado da fonte (`ok`, `failed`, `rate_limited`, `missing_key`) e quantos resultados a fonte disse ter e quantos foram trazidos.

## O que não faz

Não faz deduplicação, lista, cache nem log (tarefa 02-02). Não traz citações de um artigo (tarefa 04-02). Não troca ids de referências por DOI (tarefa 04-01). Não mexe em `server.py`.

## Conferência do T-001 (OpenAlex)

Lida pelo Claude Code em 2026-11-03 nas páginas oficiais: `help.openalex.org/api/authentication/`, `/api/paging/`, `/api/selecting-fields/`, `/api/errors/`, `/api/llm-quick-reference/`, `/data/works/attributes/` e `/data/authorships/`.

- **Chave:** vai como `?api_key=` ou no cabeçalho `Authorization: Bearer <chave>`. **Usar o cabeçalho**: assim a chave nunca aparece na URL, que vai para o cache, o log e as mensagens de erro do `httpx`.
- **Custo:** lista US$ 0,0001, busca com `search=` US$ 0,001, leitura de um trabalho avulso grátis. Orçamento de US$ 1 por dia com a chave gratuita. Respostas 4xx e 5xx custam zero. O `meta` de cada resposta traz o custo da chamada, e os cabeçalhos `X-RateLimit-Remaining` e `X-RateLimit-Credits-Used` também.
- **Limite por segundo:** 30 com chave gratuita.
- **Paginação:** `per_page` de 1 a 100 (padrão 25). `page × per_page` não passa de 10.000. O cursor existe, mas a página não diz se vale com `search=`: não usar.
- **`select`:** só campos de primeiro nível, sem campos aninhados (`open_access.is_oa` dá erro). Funciona em `/works`.
- **Erros:** 429 cobre limite por segundo e orçamento do dia esgotado; este último vem com `"error": "not_enough_credits"` no corpo. 403 com `key_not_activated` quando a chave ainda não foi ativada pelo link do e-mail. 500 é temporário. Outras 4xx não se repetem. Tempo limite de cerca de 30 s.
- **Work:** `id` (`https://openalex.org/W…`), `doi` (a página não diz se vem como URL; na prática vem `https://doi.org/…`: aceitar os dois), `display_name` (título; pode ser nulo), `publication_year`, `type`, `abstract_inverted_index` (palavra → posições; o texto é remontado), `authorships` (só os 100 primeiros autores numa lista), `primary_location.source.display_name` (periódico; a página do Work não detalha `source`, aceitar nulo em qualquer nível), `keywords` (lista com `score`; a página não detalha o nome do campo de texto: ler `display_name` e ignorar o item sem ele), `referenced_works` (ids do OpenAlex), `referenced_works_count`, `cited_by_count`.
- **Authorship:** `author_position` (`first`, `middle`, `last`), `author.id`, `author.display_name`, `author.orcid` (URL ou nulo), `institutions[]` com `id`, `display_name`, `ror`, `country_code`, `raw_affiliation_strings`, `is_corresponding`.
- **O que a página não detalha:** o formato exato de `doi`, `orcid` e `ror`, e o campo de texto de `keywords`. O código aceita as variações acima e os testes cobrem URL e forma curta.
- **T-010 (MCPs de referência):** não é exigido nesta tarefa; a conferência acima substitui a leitura do código deles para o OpenAlex.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **A chave chega ao conector lida do ambiente na hora da chamada.** `config.load()` continua guardando só se a chave existe (NFR-03). O conector lê `OPENALEX_API_KEY` com `os.environ` dentro da chamada, passa no cabeçalho e não guarda o valor em atributo, `repr`, log, mensagem de erro nem `SourceResult`.
2. **`httpx`, não `httpx2`.** O `mcp` 2.x traz o `httpx2` para uso dele. O projeto usa o `httpx` declarado, que é o da arquitetura. São dois clientes instalados, aceito.
3. **`typing_extensions` declarado.** O `server.py` importa esse pacote, que hoje só chega por meio do `mcp`. Esta tarefa o acrescenta às dependências do `pyproject.toml`.
4. **Erros do miolo** (para a 02-02 e as seguintes): `core/errors.py` define `RSLError(code, message)`, com `code` igual a um dos códigos do contrato (`no_source_available`, `invalid_input`, `list_not_found`, `search_not_found`, `work_not_found`, `format_not_available`, `export_folder_not_writable`). O miolo não importa nada do MCP; o servidor converte.

## Os modelos

`dataclasses` com `to_dict()` e `from_dict()`, nomes de campo em inglês, para gravar em JSON e no cache sem perder nada. `from_dict(x.to_dict()) == x`.

- **`Affiliation`:** `name: str | None`, `ids: dict[str, str]` (por exemplo `{"openalex": "I123", "ror": "https://ror.org/…"}`), `country_code: str | None`.
- **`Author`:** `name: str` (obrigatório), `orcid: str | None` (forma curta `0000-0002-1825-0097`, sem URL), `ids: dict[str, str]` (`{"openalex": "A123"}`), `position: str | None`, `is_corresponding: bool | None`, `affiliations: list[Affiliation]`, `raw_affiliations: list[str]`.
- **`Work`:** `title: str` (obrigatório), `doi: str | None` (minúsculo, sem `https://doi.org/`), `year: int | None`, `type: str | None`, `venue: str | None`, `abstract: str | None`, `keywords: list[str]`, `authors: list[Author]` (na ordem), `references: list[str]` (ids curtos, `W123`), `references_count: int | None`, `citations: dict[str, int]` (`{"openalex": 17}`; por fonte, nunca somado), `source_ids: dict[str, str]` (`{"openalex": "W123"}`).
- **`SourceResult`:** `name: str`, `status: str` (`ok`, `failed`, `rate_limited`, `missing_key`, `not_supported`), `reason: str | None`, `query: str` (o que foi pedido à fonte, como texto legível, sem a chave), `found: int | None`, `fetched: int`, `works: list[Work]`.

Um trabalho sem título (`display_name` nulo ou só espaços) é descartado e não conta em `fetched`. Ids do OpenAlex são guardados na forma curta (`W123`, `A123`, `I123`).

## A interface das fontes

`sources/base.py` define `Source` (classe abstrata ou `Protocol`):

- `name: str` e `needs_key: bool`;
- `def cache_query(self, query: str, max_results: int) -> dict`: os parâmetros que identificam a consulta, sem a chave, para a 02-02 usar como chave do cache;
- `async def search(self, query: str, max_results: int) -> SourceResult`: nunca levanta exceção para o miolo. Falha vira `SourceResult` com o estado e o motivo.

## O conector do OpenAlex

- `GET https://api.openalex.org/works` com `search=<query>`, `per_page=100` (ou menos, se `max_results` for menor), `page=N` e `select=id,doi,display_name,publication_year,type,primary_location,authorships,abstract_inverted_index,keywords,referenced_works,referenced_works_count,cited_by_count`. Cabeçalhos `Authorization: Bearer <chave>` e `User-Agent: rslapp/<versão>`. Tempo limite de 30 s.
- Pede páginas até chegar a `max_results`, acabar o resultado ou bater os 10.000. `found` é o `meta.count` da primeira página.
- `query` do `SourceResult`: a consulta como texto legível, por exemplo `search=machine learning interpretability · per_page=100 · páginas 1-1`. Nunca a URL com chave.
- **Estados e motivos** (o motivo em português, curto, sem dado de autor):
  - sem `OPENALEX_API_KEY` (ou vazia): `missing_key`, sem chamar a API;
  - 429 com `not_enough_credits`: `rate_limited`, "créditos diários do OpenAlex esgotados", sem novas tentativas;
  - 429 sem esse código, 5xx, tempo esgotado ou erro de rede: até 3 novas tentativas com espera de 1 s, 2 s e 4 s; esgotadas, `rate_limited` (para 429) ou `failed` (o resto), com o motivo, por exemplo "HTTP 503 depois de 3 tentativas";
  - 403 com `key_not_activated`: `failed`, "a chave do OpenAlex ainda não foi ativada pelo link do e-mail";
  - outras 4xx: `failed` na hora, com o código HTTP no motivo;
  - se uma página depois da primeira falha, os trabalhos já trazidos ficam no resultado, com o estado da falha.
- A espera entre tentativas é injetável (por exemplo `sleep` no construtor), para os testes não esperarem de verdade.
- A chamada usa um `httpx.AsyncClient` que pode ser injetado no construtor, para os testes usarem `httpx.MockTransport`.

## Pronto quando

- [x] Antes de escrever, conferir o T-001 para o OpenAlex (feito acima pelo Claude Code)
- [ ] Teste com respostas simuladas: título, DOI, ano, tipo, periódico, resumo (remontado do índice invertido), palavras-chave, autores na ordem com ORCID e afiliações com ROR, ids das referências e contagem de citações são mapeados; DOI, ORCID e ids aceitam forma de URL e forma curta
- [ ] Teste: trabalho sem título é descartado; campos ausentes ou nulos em qualquer nível ficam vazios, sem exceção
- [ ] Teste: paginação pede a segunda página quando `max_results` passa de 100, e para em `max_results`, no fim do resultado ou nos 10.000
- [ ] Teste: 429 e 5xx provocam novas tentativas com espera de 1, 2 e 4 s; esgotadas, a fonte devolve `rate_limited` ou `failed` com o motivo, sem exceção para o miolo; `not_enough_credits` e `key_not_activated` não repetem
- [ ] Teste: sem `OPENALEX_API_KEY`, devolve `missing_key` sem chamar a API
- [ ] Teste: a chave vai no cabeçalho e não aparece na URL, no `query`, no `reason`, no `repr` do conector nem nos logs (`caplog`)
- [ ] Teste: `from_dict(to_dict())` devolve o mesmo modelo
- [ ] Chamada real, uma vez, com a chave do Erick: uma busca de 100 trabalhos funciona; o custo medido é anotado no T-002. **É do Erick** (a chave está no Lore secrets; ver "Como testar")

## Vem de

FR-01, FR-03, FR-14, NFR-01, NFR-03, NFR-04, NFR-05, D-004, D-010. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefas 01-01 e 01-03 integradas. A chave do OpenAlex está no Lore secrets desde 2026-11-03 (só para a chamada real; os testes não usam rede).

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
