# Pareceres de revisão fora da busca

**Fase:** 10 · Bases pagas e filtros (1.3) · **Situação:** a fazer

## O que faz

Tira da busca os registros de revisão por pares (pareceres, cartas de decisão e respostas de autores, que o OpenAlex traz do Publons) e deixa quem quiser incluí-los (D-022).

- **Entrada nova em `search_works`:** `include_peer_review` (booleano, padrão `false`). Ela recusa número inteiro no lugar de booleano do mesmo jeito que as entradas inteiras recusam `true`/`false` (07-01): `invalid_input`.
- **OpenAlex:** com `include_peer_review=false`, o pedido leva o filtro `type:!peer-review`. Esse filtro foi conferido numa chamada real em 2026-11-11: 9.629 resultados sem filtro, 19 com `type:peer-review` e 9.610 com `type:!peer-review`. Se o pedido já tiver um `filter`, o novo se junta a ele com vírgula. O texto da string no log (`query` da fonte) mostra o filtro.
- **As outras fontes:** depois de trazer os resultados, a busca tira os artigos com `type` igual a `peer-review` (sem distinguir maiúsculas). A entrada da fonte no registro ganha `excluded_peer_review` com a quantidade, só quando for maior que zero.
- **Registro e log:**
  - `params` da busca guarda `include_peer_review`;
  - a entrada do `log.md` diz "pareceres de revisão excluídos" ou "incluídos";
  - quando houver, mostra quantos saíram por fonte.
- **`repeat_search`:** repete com o mesmo valor. Uma busca gravada antes desta tarefa, sem o campo, repete com `false`.
- **Cache:** a chave do cache do OpenAlex passa a incluir `include_peer_review`, para uma busca com o filtro não devolver o resultado guardado sem ele.
- **Orientação à IA:** a descrição de `search_works` e o prompt `plan_search` dizem que os pareceres ficam de fora por padrão e que `include_peer_review=true` serve a quem estuda o processo de revisão por pares.

## O que não faz

- Não mexe em `find_work` nem em `get_related_works`.
- Não muda listas já gravadas.
- Não muda o contrato por conta própria: o Claude atualiza `docs/interface-contract.md`.

## Pronto quando

- [ ] Teste: a busca no OpenAlex manda `filter=type:!peer-review` por padrão e não manda com `include_peer_review=true` (transporte simulado)
- [ ] Teste: uma fonte falsa que devolve um artigo `peer-review` e um `article` grava só o `article`, com `excluded_peer_review: 1` na entrada da fonte
- [ ] Teste: `include_peer_review=true` mantém os dois
- [ ] Teste: `include_peer_review=1` responde `invalid_input`
- [ ] Teste: `repeat_search` de uma busca antiga, sem o campo, repete com `false`; de uma busca com `true`, repete com `true`
- [ ] Teste: o cache do OpenAlex não confunde as duas buscas
- [ ] Teste: o `log.md` diz se os pareceres foram excluídos
- [ ] Os três gates passam

## Vem de

D-022, FR-01, FR-12, NFR-06. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/sources/openalex.py` (`search`, `cache_query`), `src/rslapp/core/search.py`, `src/rslapp/core/repeat.py`, `src/rslapp/store/log.py` (`format_log_entry`), `src/rslapp/server.py` (`search_works`, `NonBoolInt` e o validador de booleano) e `src/rslapp/prompts.py`.

Cerca de 200 linhas, testes incluídos. Um commit, com D-022 no comentário e no nome dos testes.

## Resultado da entrega

- **Entrada `include_peer_review` em `search_works` (D-022):** adicionado parâmetro booleano com padrão `false`. Criado o validador estrito `NonIntBool` em `server.py`, recusando números inteiros com `invalid_input` antes de chamar o miolo.
- **OpenAlex com filtro `type:!peer-review`:** quando `include_peer_review=false`, o conector adiciona o filtro `type:!peer-review` na requisição (e combina com vírgula caso já exista outro filtro). A string de consulta (`query`) da fonte reflete o filtro aplicado.
- **Exclusão pós-busca nas outras fontes:** quando `include_peer_review=false`, registros com `type` igual a `peer-review` (sem distinguir maiúsculas) são removidos dos resultados, e a fonte registra o campo `excluded_peer_review` com a quantidade quando for maior que zero.
- **Gravação e log (FR-12, FR-13):** `params` da busca registra `include_peer_review`. O arquivo `log.md` exibe na linha da lista `"pareceres de revisão excluídos"` ou `"pareceres de revisão incluídos"`, e na linha de cada fonte exibe quantos saíram quando houver (ex.: `"1 parecer de revisão excluído"`).
- **Repetição (`repeat_search`):** repete preservando o valor gravado de `include_peer_review`, usando `false` para buscas antigas gravadas antes desta tarefa.
- **Cache do OpenAlex (NFR-06):** `cache_query` passa a incluir `include_peer_review` no dicionário identificador, evitando que buscas com e sem filtro compartilhem cache incorretamente.
- **Orientação à IA (FR-10):** a docstring de `search_works` e o prompt `plan_search` orientam que os pareceres ficam de fora por padrão e que `include_peer_review=true` se destina a quem estuda o processo de revisão por pares.
- **Testes automatizados:** criada suíte dedicada `tests/test_peer_review.py` com 11 testes cobrindo todos os critérios da spec, além de atualizadas as asserções de query padrão em `tests/sources/test_openalex.py`.

## Como testar

1. **Rodar a suíte dedicada da tarefa:**
   ```bash
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q tests/test_peer_review.py
   ```
   Deve passar todos os 11 testes sem erros.

2. **Rodar os três gates obrigatórios do projeto (um após o outro):**
   ```bash
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
   Todos devem passar sem erros e com ruff limpo.

3. **Onde olhar primeiro (pontos mais arriscados):**
   - `src/rslapp/sources/openalex.py` (`search` e `cache_query`): verificar a injeção do filtro `type:!peer-review` e a inclusão de `include_peer_review` na chave de cache.
   - `src/rslapp/core/search.py` (`run_search`): verificar a filtragem em memória para fontes que não sejam OpenAlex e o preenchimento de `excluded_peer_review`.
   - `src/rslapp/server.py` (`NonIntBool` e `search_works`): verificar a rejeição estrita de números inteiros (`1`/`0`) com `invalid_input`.
