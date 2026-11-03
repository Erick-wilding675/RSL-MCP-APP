# Armazenamento em arquivos

**Fase:** 1 · Esqueleto · **Situação:** não iniciada

## O que faz

O pacote `store/`, que grava e lê tudo na pasta de dados: `searches/s-NNNN.json`, `lists/l-NNNN.json`, `log.md` e `cache/<fonte>/<chave>.json`. Toda gravação é atômica (arquivo temporário e renomear). Os ids são sequenciais, `s-0001` e `l-0001`, com ao menos quatro dígitos. O log legível `log.md` ganha uma entrada a cada busca e pode ser refeito a partir de `searches/`. O cache guarda a resposta, a data de obtenção e a de expiração (padrão de 7 dias, `RSL_CACHE_DAYS`); a chave do cache nunca inclui a chave de API.

## O que não faz

Não decide o que uma busca contém (isso vem da tarefa 02-02). Não apaga nem reescreve busca, lista ou entrada do log depois de gravada.

## Pronto quando

- [ ] Teste: gravar uma lista, uma busca e uma entrada de log, e lê-las de volta iguais
- [ ] Teste: se a gravação é interrompida no meio, nenhum arquivo fica pela metade
- [ ] Teste: ordem de gravação lista, busca, log; apagar o `log.md` e chamar o refazer reconstrói o log a partir de `searches/`
- [ ] Teste: uma lista já gravada não pode ser alterada pela API do módulo
- [ ] Teste: cache dentro do prazo devolve a resposta e diz que veio do cache, com a data de obtenção; cache vencido é ignorado
- [ ] Teste: a chave de API não aparece em nenhum arquivo gravado nem na chave do cache
- [ ] O `log.md` segue o formato abaixo, legível por pessoas e pronto para anexar na metodologia (FR-13)

## Formato do `log.md`

Uma entrada por busca, a mais nova por último, no texto abaixo (exemplo):

```
## s-0007 · 2026-11-02 16:41 UTC · busca por termos
Pedido: Artigos sobre interpretabilidade de modelos de aprendizado de máquina
Lista: l-0007 · incompleta · 187 artigos
- openalex · ok · encontrados 412, trazidos 100 · cache: não · string: `machine learning interpretability`
- semantic_scholar · rate_limited · HTTP 429 depois de 3 tentativas · string: `machine learning interpretability`
- crossref · ok · encontrados 230, trazidos 100 · cache: sim, obtida em 2026-11-01 · string: `machine learning interpretability`
```

Quando a busca repete outra, a entrada ganha a linha `Repetida de: s-0003`. Quando é uma lista de referências ou citações, ganha `Artigo de origem: <DOI ou id> · direção: citações`. O tipo no cabeçalho é um de: busca por termos, busca de artigo, referências, citações, repetição. As chaves de API nunca aparecem. O Claude Code pode ajustar o texto na entrega, mantendo todas essas informações.

## Vem de

FR-05, FR-09, FR-12, FR-13, NFR-03, NFR-06, D-007. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Nenhuma.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/store/_atomic.py`: gravação atômica em UTF-8 (`ensure_ascii=False`, fim de linha `\n`) usando arquivo temporário na mesma pasta do destino com `flush` e `os.fsync`, publicação exclusiva com `os.link` (para listas e buscas imutáveis) e publicação com substituição via `os.replace` com repetição curta em caso de `PermissionError` no Windows (para `log.md` e cache), cálculo de IDs sequenciais numéricos (`s-NNNN` e `l-NNNN`, crescendo para 5+ dígitos após 9999) e remoção recursiva de parâmetros de credencial (**D-007**, **FR-09**, **NFR-03**).
  - `src/rslapp/store/cache.py`: cache em `cache/<fonte>/<sha256>.json` com validação estrita de `<fonte>` (`^[a-z0-9_]+$`), normalização determinística da consulta (`dict` com chaves ordenadas) após retirar parâmetros de credencial (`api_key`, `apikey`, `api-key`, `key`, `token`, `authorization`, sem diferenciar maiúsculas), cálculo de `fetched_at` e `expires_at` em UTC ISO 8601 e leitura que devolve `{"response": ..., "from_cache": True, "fetched_at": ...}` quando dentro do prazo ou `None` quando vencido/ausente (**NFR-03**, **NFR-06**, **D-007**).
  - `src/rslapp/store/log.py`: formatação determinística de entradas do `log.md` em português conforme o formato da spec (cabeçalho com tipo traduzido de `kind` e `origin.direction`, `Pedido:`, `Repetida de:`, `Artigo de origem: ... · direção: ...`, `Lista: ... · completa/incompleta · N artigos` e linhas por fonte com contagens, motivo e marca de cache com data `YYYY-MM-DD`) (**FR-05**, **FR-13**, **NFR-03**, **NFR-06**).
  - `src/rslapp/store/__init__.py`: classe `Store(data_dir, cache_days=7)` (sem ler variáveis de ambiente nem importar MCP) com `record_search` (que reserva `list_id` e `search_id` e grava estritamente na ordem `lists/` -> `searches/` -> `log.md`), `save_list`, `get_list`, `save_search`, `get_search`, `list_searches`, `append_log`, `read_log`, `rebuild_log`, `set_cache`, `get_cache` e `cache_path` (**FR-05**, **FR-09**, **FR-12**, **FR-13**, **NFR-03**, **NFR-06**, **D-007**).
  - `tests/store/test_store.py`: 9 testes cobrindo todos os itens de "Pronto quando", interrupções simuladas em `os.fsync`, `os.link` e `os.replace`, repetição em `PermissionError` no Windows, concorrência com threads e colisão de `os.link`, IDs de 5 dígitos (`10000`), reconstrução byte a byte do `log.md`, imutabilidade de listas e buscas, expiração do cache e ausência total de chaves de API nos arquivos e nomes de arquivos (**FR-05**, **FR-09**, **FR-12**, **FR-13**, **NFR-03**, **NFR-06**, **D-007**).
- **O que foi assumido:**
  - Campos do JSON de busca (`searches/s-NNNN.json`): `id`, `created_at` (UTC, ISO 8601), `kind` (`terms`, `work`, `related` ou `repeat`), `request_summary`, `list_id`, `repeated_from` (ou `null`), `origin` (`{"work": ..., "direction": "references" | "citations"}` ou `null`) e `sources` (lista de objetos com `name`, `query`, `status`, `reason`, `found`, `fetched`, `from_cache` e `fetched_at`).
  - Campos do JSON de lista (`lists/l-NNNN.json`): `id`, `search_id`, `created_at` (UTC, ISO 8601), `status` (`complete` ou `incomplete`), `total` e `works`.
  - Campos do JSON de cache (`cache/<fonte>/<sha256>.json`): `source`, `query`, `response`, `fetched_at` e `expires_at`.
  - Na reconstrução do `log.md` (`rebuild_log`), o estado (`completa`/`incompleta`) e o `total` de artigos de cada busca vêm da lista correspondente em `lists/<list_id>.json` (que é sempre gravada antes de `searches/<search_id>.json`), com fallback para os campos da própria busca caso o arquivo da lista não esteja presente.
- **O que não deu para verificar:**
  - Nada dentro do escopo do pacote `store/`; a integração com o miolo de busca (`core/search.py`) e com as ferramentas do servidor MCP ocorre nas tarefas 02-02 e 05-02.

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
2. **O que deve aparecer:**
   - `All checks passed!` no `ruff check .`
   - `27 passed` (18 de `tests/test_config.py` + 9 de `tests/store/test_store.py`) em ambas as execuções do `pytest` (Python 3.10 e Python 3.14).
3. **Onde olhar primeiro (pontos de risco, do mais crítico ao menos crítico):**
   1. **Remoção de chaves de API e isolamento de pasta no cache (`src/rslapp/store/_atomic.py` — `sanitize_query` / `sanitize_string` e `src/rslapp/store/cache.py` — `compute_cache_key` / `validate_source_name`, NFR-03, D-007):** conferir que `api_key`, `apikey`, `api-key`, `key`, `token` e `authorization` (em qualquer caixa, em dicionários aninhados ou query strings de URL) são removidos antes de calcular o SHA-256 do cache e antes de gravar qualquer arquivo em `cache/`, `searches/`, `lists/` ou `log.md`, e que `validate_source_name` aceita apenas `[a-z0-9_]+`.
   2. **Gravação atômica, imutabilidade com `os.link` e ordem `lista -> busca -> log` (`src/rslapp/store/_atomic.py` — `_write_temp_file`, `atomic_write_exclusive`, `atomic_write_replace` e `src/rslapp/store/__init__.py` — `Store.record_search`, D-007, FR-05, FR-09, FR-12):** verificar que todo arquivo passa por temporário na mesma pasta + `flush` + `os.fsync` + limpeza em `finally`, que listas e buscas usam `os.link` (impedindo sobrescrita de IDs existentes e tratando colisão concorrente de IDs automáticos) e que `record_search` grava `lists/` antes de `searches/` e `log.md` por último.
   3. **Fidelidade do `log.md` e reconstrução byte a byte a partir de `searches/` (`src/rslapp/store/log.py` — `format_log_entry` e `src/rslapp/store/__init__.py` — `Store.rebuild_log`, FR-13, NFR-06):** confirmar que a ordenação numérica dos IDs (`s-0002`, `s-9999`, `s-10000`) e a formatação de cabeçalhos, origens, repetições e fontes produzem exatamente o mesmo `log.md`, byte a byte, tanto na escrita incremental quanto em `rebuild_log()`.
