# Ajustes do teste real

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

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

- [ ] Teste: título, resumo, autor e palavra-chave começando com cada um dos seis caracteres saem com `'` na frente; o mesmo texto no meio da célula não muda; `Year` e `Cited by` não mudam
- [ ] Teste: `export_list` numa lista com `works` vazio devolve `empty_list` nos cinco formatos e não cria arquivo na pasta de exportação
- [ ] Teste: `empty_list` está em `ERROR_CODES` e chega à IA como erro da ferramenta, como os outros códigos
- [ ] Teste: no `log.md`, uma fonte `ok` com `found` vazio (`None`) mostra "total não informado, trazidos N"; com `found=0` continua "encontrados 0"
- [ ] Teste: a Semantic Scholar, nas citações, sem `total` na resposta e com `next` presente quando chegou ao teto, devolve o motivo "teto de N atingido" e a lista sai `incomplete`; sem `next`, sem motivo
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)
- [ ] Teste manual do Erick: o CSV de uma busca real ainda abre no VOSviewer depois da proteção

## Vem de

FR-06 (exportação e lista vazia), FR-13 e FR-15 (log legível das relacionadas), D-010 (teto declarado). São os identificadores que o código leva como âncoras.

## Antes de começar

Tarefas 04-02 e 05-03 integradas. Ler `src/rslapp/exporters/csv.py`, `src/rslapp/exporters/__init__.py` (`run_export`), `src/rslapp/core/errors.py`, `src/rslapp/store/log.py` (linha "encontrados") e `SemanticScholarSource.related` em `src/rslapp/sources/semantic_scholar.py`. A resposta da Semantic Scholar em `/paper/DOI:…/citations` e `/references` traz `offset`, `next` e `data`, sem `total` (conferido com a chave em 2026-11-05).

Um commit por item (três commits), cada um com o id no comentário e no nome do teste.

## Resultado da entrega

A preencher por quem entrega.

## Como testar

A preencher por quem entrega: os gates, o que deve aparecer e os pontos mais arriscados, o mais difícil primeiro. O mais arriscado aqui é a proteção do CSV não estragar o que o VOSviewer lê.
