# Achar um artigo e repetir uma busca

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

## O que faz

As ferramentas `find_work` (por título ou DOI, devolve os candidatos numa lista própria) e `repeat_search` (refaz uma busca do log com as mesmas strings e as mesmas fontes, grava busca e lista novas com `repeated_from`, e não mexe na original).

## O que não faz

Não altera nenhuma busca ou lista já gravada.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **`find_work(title=None, doi=None, request_summary="", sources=None, max_results=10)`:** exatamente um de `title` ou `doi`, senão `invalid_input`; `max_results` de 1 a 100.
2. **Por DOI:** cada fonte ganha `find_by_doi(doi) -> SourceResult`, com uma leitura direta: OpenAlex `GET /works/doi:<doi>` (grátis), Crossref `GET /works/<doi>`, Semantic Scholar `GET /paper/DOI:<doi>` com os mesmos `fields` da busca. Um 404 é `ok` com zero trabalhos. Mesmo mapeamento, chave, novas tentativas e ritmo de cada conector.
3. **Por título:** reaproveita o `search` de cada fonte com o título como consulta e `max_results` pequeno (padrão 10). Os candidatos são juntados pela regra da 03-03.
4. **Gravação:** `kind: "work"` e `params: {"doi" ou "title", "max_results", "sources"}`. Sem resultado, a lista sai vazia e registrada.
5. **`repeat_search(search_id)`:** lê a busca original; se ela não tem `params` (busca gravada antes da 03-03), `invalid_input` com "busca sem parâmetros gravados"; inexistente, `search_not_found`. Roda de novo pelo mesmo caminho do tipo original (`terms` pela busca, `work` pelo `find_work`, `related` pelo `get_related_works`), com os mesmos `params` e as mesmas fontes, e grava busca e lista novas com `kind: "repeat"`, `repeated_from: <id original>`, `params` e `origin` copiados. A original não é tocada.
6. **Onde fica:** `core/find.py` e `core/repeat.py` (sem MCP); as ferramentas em `server.py`.

## Pronto quando

- [ ] Teste: `find_work` por DOI exato devolve o artigo; por título parecido devolve candidatos; sem resultado devolve lista vazia registrada
- [ ] Teste: `repeat_search` usa as strings originais de cada fonte e gera `s-` e `l-` novos, com `repeated_from` apontando para a original
- [ ] Teste: a busca original e a lista original continuam idênticas depois da repetição
- [ ] Teste: se uma fonte usada antes está sem chave, a repetição segue com as outras e marca a falha

## Vem de

FR-02, FR-11, UC-02, UC-03, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefas 03-03 e 04-02 integradas.

## Resultado da entrega

- **O que mudou:**
  - Adicionado método `find_by_doi(doi: str) -> SourceResult` nos três conectores (`OpenAlexSource`, `CrossrefSource` e `SemanticScholarSource`), com URL quoting estrito (`urllib.parse.quote(doi, safe="")`), tratamento de 404 retornando `status="ok"` com 0 trabalhos, cabeçalhos de autenticação/contato e retentativas em 429/5xx (FR-02, D-002, NFR-03, NFR-04).
  - Implementado o módulo `src/rslapp/core/find.py` com a função `run_find`, que valida estritamente `title` ou `doi` de forma mutuamente exclusiva, consulta fontes em paralelo (via `find_by_doi` para DOI ou via `search` com cache para título), deduplica candidatos e grava a lista própria (vazia ou preenchida) com `kind: "work"` e `params` (FR-02, UC-02, D-002, NFR-06).
  - Implementado o módulo `src/rslapp/core/repeat.py` com a função `run_repeat`, que valida o `search_id`, verifica se a busca contém `params`, reexecuta a consulta pelo caminho original (`terms`, `work` ou `related`) preservando os mesmos parâmetros e fontes via intermediário `_RepeatStoreProxy`, e grava novos registros com `kind: "repeat"`, `repeated_from` apontando para a busca original e cópia de `params` e `origin`, sem alterar a busca ou lista original (FR-11, UC-03, D-002).
  - Expostas as ferramentas `@mcp.tool() find_work` e `@mcp.tool() repeat_search` no `src/rslapp/server.py` com tratamento de erro `RSLError` → `ToolError` (D-002).
- **Qual requisito serve:** FR-02 (achar artigo específico por título ou DOI), FR-11 (repetir busca salva do log), UC-02 (jornada achar artigo específico), UC-03 (jornada repetir busca), D-002 (contrato de chamadas do servidor MCP), NFR-03 (segurança de chaves), NFR-04 (ritmo e retentativas) e NFR-06 (cache).
- **O que foi assumido:** Se uma busca gravada antes de ter o campo `params` for requisitada para repetição, o sistema recusa com `RSLError("invalid_input", "busca sem parâmetros gravados")`. Quando todas as fontes respondem 404 por DOI, `find_work` registra uma lista vazia (`total: 0, works: []`) em vez de levantar erro `work_not_found`.
- **O que não deu para verificar:** Chamadas a APIs reais em ambiente de produção (testes cobriram integralmente via `httpx.MockTransport` e fontes simuladas, sem tráfego real de rede).

## Como testar

1. **Rodar os gates de testes e linter:**
   ```bash
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
   Deve passar com zero erros e todos os testes aprovados.

2. **Onde olhar primeiro (pontos de maior risco):**
   1. **Imutabilidade e integridade na repetição:** Ao chamar `repeat_search`, verificar se `s-` e `l-` originais permanecem inalterados, se os novos gerados trazem `kind: "repeat"` e `repeated_from: <original_id>`, e se o `log.md` anexa a linha `Repetida de: s-XXXX` sem truncar o histórico anterior.
   2. **Segurança de injeção em caminhos de DOI:** Conferir nos testes de conectores se DOIs complexos ou com caracteres como `/`, spaces, `%` são encodados estritamente com `urllib.parse.quote(safe="")` e se barras transversais ou `..` não alteram a rota da API.
   3. **Tratamento de 404 vs falhas na busca de artigo:** Conferir que 404 em todas as fontes gera lista vazia registrada com status `complete`, enquanto falhas 5xx/timeout deixam a lista marcada como `incomplete` com o motivo da fonte.
