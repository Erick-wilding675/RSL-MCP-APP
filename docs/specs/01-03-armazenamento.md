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
  - `src/rslapp/store/_atomic.py`: gravação atômica em UTF-8 (`ensure_ascii=False`, fim de linha `\n`) com arquivo temporário na mesma pasta do destino, `flush` e `os.fsync`; publicação exclusiva via `os.link` (com fallback para `os.rename` no Windows quando o sistema de arquivos não aceita hard links e erro explícito fora do Windows); publicação com substituição via `os.replace` e repetição de até ~1 s para `PermissionError` no Windows; trava entre processos e threads via arquivo `.lock` (`O_CREAT | O_EXCL`, expiração de trava órfã e remoção em `finally`); formatação/validação canônica de IDs (`s-NNNN` e `l-NNNN`); e limpeza cirúrgica de credenciais em três funções (`strip_dict_credentials`, `strip_url_credentials` e `strip_response_credentials`) (**D-007**, **FR-05**, **FR-09**, **FR-12**, **NFR-03**).
  - `src/rslapp/store/cache.py`: cache em `cache/<fonte>/<sha256>.json` com validação estrita de `<fonte>` (`^[a-z0-9_]+$`), remoção recursiva de chaves de credencial (`api_key`, `apikey`, `api-key`, `key`, `token`, `authorization`, sem diferenciar maiúsculas) da consulta sem alterar valores de texto, limpeza de parâmetros de credencial em URLs `http(s)` dentro das strings de `response`, cálculo de `fetched_at` e `expires_at` em UTC ISO 8601 e leitura com verificação de validade (**NFR-03**, **NFR-06**, **D-007**).
  - `src/rslapp/store/log.py`: validação prévia e formatação determinística de entradas do `log.md` em português conforme a spec (cabeçalho com tipo traduzido de `kind` e `origin.direction`, `Pedido:`, `Repetida de:`, `Artigo de origem: ... · direção: ...`, `Lista: ... · completa/incompleta · 1 artigo / N artigos` ou `Lista: l-NNNN · arquivo ausente`, exibição de `reason` inclusive com `status == "ok"`, data do cache em UTC e substituição de quebras de linha por espaço em pedido, string e motivo) (**FR-05**, **FR-13**, **NFR-03**, **NFR-06**).
  - `src/rslapp/store/__init__.py`: classe `Store(data_dir, cache_days=7)` com API pública enxuta (`record_search`, `get_list`, `get_search`, `list_searches`, `read_log`, `rebuild_log`, `set_cache`, `get_cache`), numeração única por par `s-NNNN`/`l-NNNN` (`maior número em lists/ ou searches/ + 1`), validação do log antes de publicar a lista e preservação integral dos dicionários de entrada (acrescentando apenas `id`, `search_id`/`list_id` e `created_at`, e limpando URLs apenas em `sources[].query` e `sources[].reason`) (**FR-05**, **FR-09**, **FR-12**, **FR-13**, **NFR-03**, **NFR-06**, **D-007**).
  - `tests/store/test_store.py`: 8 testes cobrindo preservação integral dos dados de entrada, `ensure_ascii=False` em lista/busca/log/cache, formato e regras do `log.md`, validação prévia sem lista órfã, interrupções em `os.fsync`/`os.link`/`os.replace`, fallback exFAT/POSIX, colisão no `os.link`, concorrência com threads e `multiprocessing` (3 processos x 15 buscas) e limpeza de credenciais nos 3 pontos (**FR-05**, **FR-09**, **FR-12**, **FR-13**, **NFR-03**, **NFR-06**, **D-007**).
- **O que foi assumido:**
  - Campos base de busca (`searches/s-NNNN.json`): `id`, `created_at` (UTC, ISO 8601), `kind` (`terms`, `work`, `related` ou `repeat`), `request_summary`, `list_id`, `repeated_from` (ou `null`), `origin` (`{"work": ..., "direction": "references" | "citations"}` ou `null`) e `sources` (lista de objetos com `name`, `query`, `status`, `reason`, `found`, `fetched`, `from_cache` e `fetched_at`), preservando quaisquer campos adicionais recebidos sem conversão de tipos.
  - Campos base de lista (`lists/l-NNNN.json`): `id`, `search_id`, `created_at` (UTC, ISO 8601), `status` (`complete` ou `incomplete`), `total` e `works`, preservando quaisquer campos adicionais recebidos.
  - Campos de cache (`cache/<fonte>/<sha256>.json`): `source`, `query`, `response`, `fetched_at` e `expires_at`.
- **O que não deu para verificar:**
  - Partição **exFAT real** (o comportamento sem suporte a hard links foi verificado simulando `OSError` em `os.link` com `monkeypatch`).

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
2. **O que deve aparecer:**
   - `All checks passed!` no `ruff check .`
   - `26 passed` (18 de `tests/test_config.py` + 8 de `tests/store/test_store.py`) em ambas as execuções do `pytest` (Python 3.10 e Python 3.14).
3. **Onde olhar primeiro (pontos de risco, do mais crítico ao menos crítico):**
   1. **Limpeza cirúrgica de credenciais nos três pontos e preservação dos dados de entrada (`src/rslapp/store/_atomic.py` — `strip_dict_credentials`, `strip_url_credentials`, `strip_response_credentials` e `src/rslapp/store/__init__.py` — `_clean_sources`, NFR-03):** conferir que (a) a consulta do cache remove apenas chaves de credencial em qualquer nível sem tocar nos valores de texto (`"key=0.5"` vs `"key=0.9"`), (b) `sources[].query` e `sources[].reason` removem apenas parâmetros de credencial de URLs `http(s)` mantendo o resto byte a byte, (c) `response` do cache aplica a mesma limpeza de URLs nas strings, e (d) listas e buscas gravam o dicionário recebido sem descartar campos nem alterar `works` ou `request_summary`.
   2. **Trava entre processos, reserva do par `s-NNNN`/`l-NNNN` e validação antes de gravar (`src/rslapp/store/_atomic.py` — `file_lock`, `atomic_write_exclusive` e `src/rslapp/store/__init__.py` — `Store.record_search`, D-007, FR-05, FR-09, FR-12):** verificar que `record_search` e `rebuild_log` rodam sob trava em `.lock` (`O_CREAT | O_EXCL`), que a entrada do log é montada/validada antes de publicar `lists/l-NNNN.json` (evitando listas órfãs em entradas inválidas) e que uma falha ao publicar a busca não faz a busca seguinte reusar o ID.
   3. **Formatação e reconstrução byte a byte do `log.md` (`src/rslapp/store/log.py` — `format_log_entry` e `src/rslapp/store/__init__.py` — `Store.rebuild_log`, FR-13, NFR-06):** confirmar singular/plural (`1 artigo` vs `N artigos`), exibição de `reason` com `status == "ok"`, data do cache em UTC, substituição de quebras de linha por espaço e indicação `Lista: l-NNNN · arquivo ausente` quando o arquivo da lista não existe.
