# Busca, lista e log

**Fase:** 2 · Fatia completa · **Situação:** pronta

## O que faz

O miolo de busca em `core/search.py` e a ferramenta `search_works` no servidor. A busca consulta as fontes pedidas (por ora só o OpenAlex), olha o cache antes de chamar cada fonte, tira as duplicatas dentro da lista (DOI, senão título normalizado), define se a lista é completa ou incompleta, grava a lista, a busca e a linha do log (tarefa 01-03) e devolve a resposta em resumo: `search_id`, `list_id`, `status`, `total`, `page`, `next_page`, `sources` e a primeira página de `works` (25 por página). A busca roda direto, sem etapa de aprovação.

## O que não faz

Não consulta Crossref nem Semantic Scholar (tarefas 03-01 e 03-02). Não deduplica entre fontes (03-03). Não exporta (02-03). Não muda `list_sources`.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Como o erro chega à IA.** No `mcp` 2.3.0, um `ToolError` levantado na ferramenta vira um resultado com `is_error=True` e o texto da exceção, que o modelo lê; qualquer outra exceção vira só "Error executing tool …", sem detalhe. Por isso o servidor captura `RSLError` (tarefa 02-01) e levanta `ToolError(f"{code}: {mensagem}")`, por exemplo `no_source_available: nenhuma fonte pode responder; configure OPENALEX_API_KEY`. O código do contrato vem sempre primeiro. O miolo não importa nada do MCP.
2. **Campos dos JSON**, os já usados pelo armazenamento (spec 01-03):
   - busca: `kind` (`terms`), `request_summary`, `sources` com um objeto por fonte: `name`, `query` (texto, o `SourceResult.query`), `status`, `reason`, `found`, `fetched`, `from_cache` e `fetched_at` (quando veio do cache);
   - lista: `status` (`complete` ou `incomplete`), `total` e `works` (o `Work.to_dict()` completo);
   - cache: a consulta é o dicionário de `Source.cache_query(query, max_results)`, e a resposta é o `SourceResult.to_dict()`.
3. **Lista incompleta** quando alguma fonte consultada não terminou em `ok`. O corte por `max_results` não deixa a lista incompleta: `found` e `fetched` mostram o corte, e a IA vê os dois.
4. **`no_source_available`** quando todas as fontes pedidas estão em `missing_key`. Nesse caso nada é gravado. Fontes que falharam por rede ou limite geram lista, mesmo vazia, marcada `incomplete`.
5. **Padrões de `search_works`:** `max_results` padrão 100, aceito de 1 a 1.000 (até dez páginas do OpenAlex, US$ 0,01 por busca); `sources` padrão: todas as fontes que o servidor tem; nome de fonte desconhecido, `query` vazia ou `max_results` fora da faixa dão `invalid_input`.

## Como a busca anda

`core/search.py` expõe uma função assíncrona, por exemplo `run_search(store, sources, *, query, request_summary, max_results) -> dict`, que recebe o `Store` e as fontes já montadas, para os testes passarem fontes simuladas.

1. Para cada fonte: monta `cache_query`; se `store.get_cache` devolve uma entrada válida, usa o `SourceResult` dela, com `from_cache: true` e o `fetched_at` da entrada; senão chama `search`, e grava no cache só resultados `ok`.
2. Junta os trabalhos e tira as duplicatas: a chave é `doi:<doi minúsculo>` quando há DOI, senão `title:<título normalizado>` (minúsculas, sem acento, só letras e números, espaços simples). Fica o primeiro; os `source_ids` e `citations` do repetido entram no que ficou.
3. Define `complete` ou `incomplete` (decisão 3) e chama `store.record_search(search, list)`.
4. Devolve o resumo: por trabalho, só `doi`, `title`, `authors` (só os nomes), `year`, `venue`, `references_count` e `citations`. `page` é 1 e `next_page` é 2 quando há mais de 25 trabalhos, senão `null`. `total` é o número depois de tirar as duplicatas.

A ferramenta `search_works(query, request_summary="", sources=None, max_results=100)` em `server.py` lê `config.load()` dentro da chamada, monta `Store(cfg.data_dir, cfg.cache_days)` e as fontes (`[OpenAlexSource()]`), chama o miolo e converte `RSLError` em `ToolError`.

## Pronto quando

- [x] Teste com fonte simulada: uma busca devolve lista, grava `lists/`, `searches/` e a linha no `log.md`, e os ids de busca e lista aparecem na resposta
- [x] Teste: dois registros com o mesmo DOI viram um; sem DOI, o mesmo título normalizado vira um; o caso de DOI diferente e título igual fica como dois
- [x] Teste: com a fonte em `failed`, a lista sai `incomplete` com a fonte e o motivo na resposta e no log (FR-08); com zero resultados, a lista sai vazia e registrada
- [x] Teste: com todas as fontes em `missing_key`, devolve o erro `no_source_available` e não grava lista, busca nem log
- [x] Teste: a segunda busca igual, dentro do prazo, vem do cache sem chamar a fonte, com `from_cache: true` na resposta e no log; um resultado `failed` não vai para o cache
- [x] Teste: a resposta à IA não passa de um resumo por artigo (25 no máximo); o registro completo fica na lista salva
- [x] Teste: cada busca gera uma lista própria; duas buscas seguidas não se juntam
- [x] Teste pelo servidor (`Client(mcp)` em memória, com fonte simulada e `RSL_DATA_DIR` temporário): `search_works` responde como no contrato, e uma entrada inválida volta como erro com `invalid_input:` no início do texto

## Vem de

FR-01, FR-04, FR-05, FR-08, FR-09, FR-12, NFR-06, D-002, D-003. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefas 01-02 (servidor), 01-03 (armazenamento) e 02-01 (modelos, erros e fonte OpenAlex) integradas.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/core/search.py`: implementação de `run_search`, `deduplicate_works` e `normalize_title` sem dependência do MCP (**FR-01**, **FR-04**, **FR-05**, **FR-08**, **FR-09**, **FR-12**, **NFR-06**, **D-002**, **D-003**). Valida `query`, `request_summary`, `max_results` (`1..1000`) e `source_names`; consulta `store.get_cache` antes de chamar cada fonte e só grava em cache resultados com `status == "ok"`; levanta `RSLError("no_source_available", ...)` sem gravar arquivos quando todas as fontes estão em `missing_key`; deduplica artigos por `doi:<doi minúsculo>` ou `title:<título normalizado>` preservando o primeiro registro e incorporando `source_ids` e `citations` novas dos repetidos; marca a lista como `complete` apenas quando todas as fontes consultadas terminam em `ok` (senão `incomplete`); persiste lista, busca e `log.md` via `store.record_search`; e devolve o resumo paginado (até 25 itens na primeira página, `next_page: 2` quando `total > 25` ou `None` caso contrário).
  - `src/rslapp/server.py`: acréscimo de `_build_sources()` (devolvendo `[OpenAlexSource()]`) e da ferramenta assíncrona `@mcp.tool() search_works(query, request_summary="", sources=None, max_results=100)`, que carrega `config.load()` dinamicamente, instancia `Store(cfg.data_dir, cfg.cache_days)`, delega a `run_search` e converte `RSLError` em `ToolError(f"{e.code}: {e.message}")` (**FR-01**, **FR-04**, **FR-05**, **FR-08**, **FR-09**, **FR-12**, **NFR-06**, **D-002**, **D-003**).
  - `tests/core/test_search.py` e `tests/test_server_search_works.py`: suíte de testes cobrindo gravação de lista/busca/log, deduplicação por DOI e título normalizado, preservação de DOIs distintos com mesmo título, estado `incomplete` em falha, lista vazia em zero resultados, erro `no_source_available` sem gravação quando todas as fontes estão em `missing_key`, leitura/escrita seletiva de cache, resumo de 25 itens vs registro completo salvo na lista, isolamento entre buscas seguidas e chamadas via `Client(mcp)` em memória com validação de `invalid_input:`.
  - `tests/test_server.py`: atualização de asserção de ferramentas de `assert tool_names == ["list_sources"]` para `assert "list_sources" in tool_names`, refletindo o registro da nova ferramenta `search_works` no servidor MCP.
- **O que foi assumido:**
  - Quando uma duplicata traz uma chave em `source_ids` ou `citations` já existente no primeiro registro (por exemplo, dois registros da mesma fonte), prevalece o valor do primeiro registro; chaves de fontes ainda ausentes no primeiro registro são acrescentadas.
  - Em `sources` na entrada de `search_works`, nomes duplicados na mesma chamada (por exemplo `["openalex", "openalex"]`) são consultados uma única vez mantendo a ordem.
- **O que não deu para verificar:**
  - Busca real fim a fim contra a API do OpenAlex pelo cliente MCP (todos os testes automatizados usam fontes simuladas, sem chamadas de rede).

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
2. **O que deve aparecer:**
   - `All checks passed!` no `ruff check .`
   - Todos os testes passando (`64 passed`) nas duas execuções do `pytest` (Python 3.10 e Python 3.14).
3. **Onde olhar primeiro (pontos de risco, do mais difícil ao mais simples):**
   1. **Gravação condicional, cache seletivo e estado da lista (`src/rslapp/core/search.py` — `run_search`, FR-05, FR-08, FR-12, NFR-06, D-002):** conferir que `store.set_cache` só é chamado quando `result.status == "ok"`, que `all(entry["status"] == "missing_key" ...)` levanta `RSLError("no_source_available", ...)` antes de qualquer chamada a `store.record_search`, e que qualquer fonte com estado diferente de `"ok"` resulta em `status == "incomplete"` tanto na lista salva quanto no `log.md`.
   2. **Resumo para a IA vs dados pessoais completos na lista salva (`src/rslapp/core/search.py` — `_summarize_work` e `run_search`, FR-12, D-002, D-004):** verificar que `works` na resposta de `search_works` contém no máximo 25 itens e expõe apenas `doi`, `title`, `authors` (somente nomes), `year`, `venue`, `references_count` e `citations`, enquanto `lists/l-NNNN.json` guarda todos os registros completos (`Work.to_dict()`, incluindo ORCID, afiliações, resumo e ids de referências).
   3. **Deduplicação por DOI e título normalizado (`src/rslapp/core/search.py` — `normalize_title`, `_dedup_key` e `deduplicate_works`, FR-04):** confirmar que DOIs com maiúsculas convergem para a mesma chave `doi:<minúsculo>` (o prefixo de URL é tirado pela fonte, não aqui), títulos sem DOI convergem após remoção de acentos (`NFKD`) e pontuação, e dois trabalhos com DOIs distintos nunca são fundidos mesmo que tenham título idêntico.

**Para ver na prática (nota do Claude Code na revisão):** conecte um cliente MCP ao servidor sem `OPENALEX_API_KEY` e chame `search_works(query="x")`. Deve voltar um erro começando por `no_source_available:`, e nada deve ser gravado na pasta de dados. Com a chave, uma busca pequena devolve `search_id`, `list_id` e até 25 trabalhos, e cria `lists/`, `searches/` e `log.md`.

**Acompanhamentos da revisão (não bloqueiam):** falta um teste de que uma exceção que não é `RSLError` não vira texto com detalhes no servidor, e o teste de `RSL_CACHE_DAYS` não confere os 14 dias. Um título só de pontuação, sem DOI, normaliza para vazio e junta trabalhos diferentes: fica para a 03-03.
