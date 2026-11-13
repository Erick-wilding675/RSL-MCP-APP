# String das bases pagas no log

**Fase:** 10 · Bases pagas e filtros (1.3) · **Situação:** para testar

## O que faz

Corrige o texto da string que o Scopus e o Web of Science gravam no registro da busca (`query` da fonte, que aparece no `log.md`). Hoje esse texto descreve a última página pedida, e não a busca inteira. Foi achado no teste real da 10-05, em 2026-11-13: uma busca de 40 artigos no Scopus gravou `query=TITLE-ABS-KEY(…) · count=15 · start=25`. Quem tenta refazer a busca à mão a partir do log é enganado.

O texto passa a seguir o modelo do OpenAlex (`… · per_page=40 · páginas 1-1`):

- **Scopus:** `query=<string mandada> · view=<visão usada> · count=<tamanho da página> · páginas 1-<última página>`.
  - Exemplo: `query=TITLE-ABS-KEY(telemedicine) · view=COMPLETE · count=25 · páginas 1-2`.
  - `view` é a visão que de fato trouxe os resultados: `STANDARD` quando o Scopus recusou a COMPLETE e a busca caiu para a reduzida.
  - `count` é o tamanho de página usado (`PAGE_SIZE`, ou menos quando `max_results` for menor), e não o `count` da última página.
- **Web of Science:** `q=<string mandada> · limit=<tamanho da página> · páginas 1-<última página>`.
- Vale para todos os caminhos que gravam o texto: sucesso, falha no meio da paginação e o registro antes da primeira página.
  - Quando a falha acontece numa página, o texto diz até onde chegou (`páginas 1-<página que falhou>`).
- O texto continua sem nenhum valor de chave (NFR-03).

## O que não faz

- Não muda o que é pedido às APIs nem os resultados.
- Não muda o texto das outras fontes.
- Não reescreve logs já gravados.

## Pronto quando

- [ ] Teste: uma busca simulada de 40 artigos no Scopus (páginas de 25 e 15) grava `query=… · view=COMPLETE · count=25 · páginas 1-2`
- [ ] Teste: com 403 na COMPLETE e queda para STANDARD, o texto diz `view=STANDARD`
- [ ] Teste: uma busca simulada no Web of Science de duas páginas grava `q=… · limit=50 · páginas 1-2`
- [ ] Teste: falha na segunda página grava `páginas 1-2` no Scopus e no Web of Science
- [ ] Os testes que conferiam o texto antigo passam a conferir o novo
- [ ] Os três gates passam

## Vem de

FR-05, FR-13, D-023. São os ids que o código leva como âncoras.

## Antes de começar

Ler `_format_query_text` e `search` em `src/rslapp/sources/scopus.py` e em `src/rslapp/sources/web_of_science.py`, e o `_format_query_text` de `src/rslapp/sources/openalex.py`, que é o modelo. Os testes estão em `tests/sources/test_scopus.py` e `tests/sources/test_web_of_science.py`.

Cerca de 80 linhas, testes incluídos. Um commit, com FR-13 no comentário e no nome dos testes.

## Resultado da entrega

- **Scopus:** o texto passou a `query=<string> · view=<visão que trouxe os resultados> · count=<tamanho da página> · páginas 1-<última página pedida>`. Isso vale no sucesso, na falha no meio da paginação, sem chave e na queda de COMPLETE para STANDARD.
- **Web of Science:** o texto passou a `q=<string> · limit=<tamanho da página> · páginas 1-<última página pedida>`.
- Os testes `test_fr13_*` em `tests/sources/test_scopus.py` e `tests/sources/test_web_of_science.py` cobrem os casos da spec e um registro ilegível na primeira página.

## Como testar

1. `uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -v tests/sources/test_scopus.py tests/sources/test_web_of_science.py -k fr13`: os testes passam.
2. Na rede da faculdade, uma busca de 40 artigos no Scopus deve gravar no `log.md` `query=TITLE-ABS-KEY(…) · view=COMPLETE · count=25 · páginas 1-2`.

Onde olhar primeiro: o fim do laço de `search` em `src/rslapp/sources/scopus.py`, onde `page` só sobe quando outra página vai mesmo ser pedida.

**Revisão do Claude (2026-11-13, run `b20261111-211913` do Playmaker):** três rodadas (Gemini 3.8 Flash).

1. **Primeira rodada:** voltou pelo agente revisor. Com um registro que `_parse_work` recusa, a busca fazia 2 pedidos e o log dizia `páginas 1-3`.
2. **Segunda rodada:** foi parada a pedido do Erick, que ia desligar o computador.
3. **Terceira rodada:** partiu do commit da primeira e corrigiu só esse ponto, com um teste. Foi integrada com os três gates refeitos pelo `board integrate`.

A parada `found <= start + count` não muda os pedidos às APIs, como o revisor conferiu.
