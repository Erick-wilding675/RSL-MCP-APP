# Ajustes do teste real

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** para testar

## O que faz

Corrige três pontos que o teste real de 2026-11-05 mostrou, com as decisões que o Erick tomou no mesmo dia:

1. **CSV protegido contra fórmula.** Uma célula de texto que começa com `=`, `+`, `-`, `@`, tabulação ou retorno de carro ganha um `'` na frente. Assim o Excel não a executa como fórmula.
2. **Lista vazia não exporta.** `export_list` numa lista sem nenhum artigo devolve o erro novo `empty_list` ("a lista está vazia, não há o que exportar") e não grava arquivo, em qualquer formato.
3. **Total desconhecido da Semantic Scholar.** Nas referências e citações, a Semantic Scholar não informa o total. Hoje o `log.md` escreve "encontrados 0", e a fonte nunca avisa que o teto cortou a lista. Passa a escrever "total não informado" e a marcar "teto de N atingido" quando parou no teto com mais páginas por vir.

## O que não faz

Não muda o teto: ele continua valendo por fonte, como decidido (o contrato ganha "por fonte" no `get_related_works`, e essa mudança de documento é do Claude, já feita). Não muda outros formatos além do CSV na proteção. Não muda os outros códigos de erro.

## Decisões desta spec

Tomadas pelo Erick em 2026-11-05, baratas de desfazer:

- **Teto por fonte:** `max_results=100` traz até 100 de cada fonte; a lista juntada pode passar disso. Só o texto do contrato muda.
- **Proteção do CSV:** sim. Só nas colunas de texto (`Authors`, `Author full names`, `Title`, `Source title`, `Abstract`, `Author Keywords`, `Affiliations`, `Document Type`, `References`). Colunas de número (`Year`, `Cited by`, `Citations …`) e de id (`DOI`, `OpenAlex ID`, `Crossref DOI`, `Semantic Scholar ID`) ficam como estão. Nas colunas com vários valores separados por `; `, a regra vale para o começo da célula.
- **Lista vazia:** erro com aviso claro, sem arquivo. Código novo `empty_list` no contrato.

## Pronto quando

- [x] Teste: título, resumo, autor e palavra-chave começando com cada um dos seis caracteres saem com `'` na frente; o mesmo texto no meio da célula não muda; `Year` e `Cited by` não mudam
- [x] Teste: `export_list` numa lista com `works` vazio devolve `empty_list` nos cinco formatos e não cria arquivo na pasta de exportação
- [x] Teste: `empty_list` está em `ERROR_CODES` e chega à IA como erro da ferramenta, como os outros códigos
- [x] Teste: no `log.md`, uma fonte `ok` com `found` vazio (`None`) mostra "total não informado, trazidos N"; com `found=0` continua "encontrados 0"
- [x] Teste: a Semantic Scholar, nas citações, sem `total` na resposta e com `next` presente quando chegou ao teto, devolve o motivo "teto de N atingido" e a lista sai `incomplete`; sem `next`, sem motivo
- [x] Os três gates passam (ruff, pytest em 3.10 e em 3.14)
- [ ] Teste manual do Erick: o CSV de uma busca real ainda abre no VOSviewer depois da proteção

## Vem de

FR-06 (exportação e lista vazia), FR-13 e FR-15 (log legível das relacionadas), D-010 (teto declarado). São os identificadores que o código leva como âncoras.

## Antes de começar

Tarefas 04-02 e 05-03 integradas. Ler `src/rslapp/exporters/csv.py`, `src/rslapp/exporters/__init__.py` (`run_export`), `src/rslapp/core/errors.py`, `src/rslapp/store/log.py` (linha "encontrados") e `SemanticScholarSource.related` em `src/rslapp/sources/semantic_scholar.py`. A resposta da Semantic Scholar em `/paper/DOI:…/citations` e `/references` traz `offset`, `next` e `data`, sem `total` (conferido com a chave em 2026-11-05).

Um commit por item (três commits), cada um com o id no comentário e no nome do teste.

## Resultado da entrega

- **O que mudou:**
  1. **CSV protegido contra fórmula (FR-06):** em `src/rslapp/exporters/csv.py`, adicionada a função `_protect_formula` que prefixa com `'` qualquer célula das nove colunas de texto (`Authors`, `Author full names`, `Title`, `Source title`, `Abstract`, `Author Keywords`, `Affiliations`, `Document Type`, `References`) que comece com `=`, `+`, `-`, `@`, `\t` ou `\r`. Nas colunas com múltiplos valores separados por `; `, a regra vale para o começo da célula. Colunas de número (`Year`, `Cited by`, `Citations …`) e de identificador (`DOI`, `OpenAlex ID`, `Crossref DOI`, `Semantic Scholar ID`) permanecem inalteradas.
  2. **Erro `empty_list` para lista vazia (FR-06, D-002):** adicionado `"empty_list"` a `ErrorCode` e `ERROR_CODES` em `src/rslapp/core/errors.py`, e validação em `run_export` (`src/rslapp/exporters/__init__.py`) que levanta `RSLError("empty_list", "a lista está vazia, não há o que exportar")` antes de qualquer renderização ou criação de arquivo quando `works` está vazio.
  3. **Total desconhecido e teto na Semantic Scholar (FR-13, FR-15, D-010):** em `src/rslapp/store/log.py`, `_format_source_line` passa a escrever `"total não informado, trazidos N"` quando `status == "ok"` e `found is None`, mantendo `"encontrados 0, trazidos N"` quando `found == 0`. Em `SemanticScholarSource.related` (`src/rslapp/sources/semantic_scholar.py`), quando a busca atinge `effective_max` e a página traz `next > offset`, marca `stopped_by_ceiling = True` e devolve `reason = "teto de N atingido"` mesmo sem `total` na resposta, fazendo a lista sair `incomplete`.
- **Requisitos atendidos:** FR-06, FR-13, FR-15, D-002 e D-010.
- **O que não deu para verificar:** A abertura manual no VOSviewer de um CSV exportado com células protegidas por `'` (depende do teste manual do Erick).

## Como testar

1. **Gates automatizados:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
   Deve aparecer `All checks passed!` no ruff e todos os testes aprovados em Python 3.10 e 3.14.

2. **Onde olhar primeiro (pontos mais arriscados, do mais difícil ao mais simples):**
   1. **Proteção do CSV sem quebrar a leitura do VOSviewer (`src/rslapp/exporters/csv.py`, `tests/exporters/test_csv.py`):** conferir que os seis prefixos (`=`, `+`, `-`, `@`, `\t`, `\r`) ganham `'` apenas no início da célula das nove colunas de texto, que os mesmos caracteres no meio da célula (incluindo o segundo autor ou segunda palavra-chave após `; `) não mudam, que `Year`, `Cited by` e colunas de ID não são alteradas, e testar manualmente abrir um CSV real no VOSviewer (aba Scopus).
   2. **Recusa de exportação em lista vazia (`src/rslapp/exporters/__init__.py`, `tests/test_server_export_list.py`):** conferir que `export_list` numa lista com `works: []` devolve `empty_list: a lista está vazia, não há o que exportar` nos cinco formatos (`ris`, `csv`, `json`, `dois`, `openalex_url`) — inclusive antes do erro `format_not_available` de `openalex_url` — e não cria arquivo nem pasta de exportação.
   3. **Corte pelo teto e log quando `total` não é informado (`src/rslapp/sources/semantic_scholar.py`, `src/rslapp/store/log.py`, `tests/core/test_related.py`):** conferir que em `SemanticScholarSource.related` sem `total` na resposta, a presença de `next` ao atingir `max_results` preenche `reason="teto de N atingido"` e marca a lista como `incomplete`, enquanto a ausência de `next` mantém `reason=None` e a lista `complete`, e o `log.md` registra `total não informado, trazidos N`.
