# Juntar listas

**Fase:** 9 · Versão 1.2 · **Situação:** a fazer

## O que faz

Uma ferramenta nova, `merge_lists`, une listas salvas de buscas diferentes numa lista nova e sem duplicatas (D-021). Serve a quem monta uma revisão com várias strings sobre o mesmo assunto, por exemplo uma busca em inglês e outra em português, ou uma string por base, e precisa de uma lista só para exportar.

```
merge_lists(
  list_ids=["l-0001", "l-0003"],
  request_summary="Juntar as buscas em inglês e em português sobre ensino híbrido"
)
```

| Entrada | O que é | Obrigatório | Padrão |
|---|---|---|---|
| `list_ids` | As listas a juntar, de 2 a 20, sem repetir | sim | - |
| `request_summary` | O motivo da junção, em linguagem natural (vai para o log) | não | vazio |

**Volta:** o mesmo formato de `search_works` (`search_id`, `list_id`, `status`, `total`, `page`, `next_page`, `works` da primeira página), sem `sources` e mais:

- `merged_from`: as listas de origem, na ordem pedida;
- `duplicates_removed`: quantos artigos saíram por serem repetidos.

- **Junção:** os artigos de todas as listas passam pela mesma deduplicação da busca (`core/dedup.py`: DOI, depois título e ano, com a precedência de fontes). Um artigo repetido vira um só e guarda os `source_ids` e as `citations` de todos. A ordem é a das listas pedidas, e dentro de cada uma a ordem dela.
- **Estado:** `complete` se todas as listas de origem estão completas; senão `incomplete`, com `incomplete_from` dizendo quais listas não estavam completas.
- **Gravação:** como uma busca (`Store.record_search`): uma lista nova `l-NNNN` e um registro `s-NNNN` com `kind: "merge"`, `merged_from`, `request_summary` e as contagens. A gravação segue a ordem de sempre: lista, registro e log.
- **Log legível:** uma entrada própria no `log.md`, com a data, o pedido resumido, as listas de origem com o total de cada uma, o total da lista nova e quantas duplicatas saíram. Ela entra na metodologia do mesmo jeito que uma busca.
- **Erros:** `invalid_input` para menos de 2 listas, mais de 20, ids repetidos ou id em formato errado; `list_not_found` para uma lista que não existe, e nesse caso nada é gravado.
- **`repeat_search`** de um registro de junção responde `invalid_input` com `uma junção não pode ser repetida; repita as buscas de origem`.
- **No modo HTTP:** a ferramenta só vê as listas da pessoa logada (08-04) e entra na lista do `_build_http_mcp_server`. O servidor passa a ter 9 ferramentas, e os testes que contam 8 passam a contar 9.
- **Orientação à IA:** o prompt `plan_search` explica a diferença. Assuntos diferentes continuam em listas separadas. Várias strings do mesmo assunto podem ser juntadas com `merge_lists` depois das buscas.

## O que não faz

- Não junta listas de pessoas diferentes.
- Não apaga nem muda as listas de origem.
- Não refaz buscas: junta o que já está salvo.

## Pronto quando

- [ ] Teste: duas listas com um artigo em comum (mesmo DOI) viram uma lista com o artigo uma vez só, `source_ids` unidos e `duplicates_removed` igual a 1
- [ ] Teste: artigos sem DOI com o mesmo título e ano também se juntam
- [ ] Teste: uma lista de origem incompleta deixa a junção `incomplete`, com `incomplete_from`
- [ ] Teste: os erros acima, e uma lista inexistente que não grava nada (nem lista, nem registro, nem log)
- [ ] Teste: o `log.md` ganha a entrada da junção, e `get_search_log` mostra o registro com `kind: "merge"`
- [ ] Teste: `repeat_search` de uma junção responde `invalid_input`
- [ ] Teste: no modo HTTP, a Maria não consegue juntar uma lista do João (`list_not_found`), e o servidor lista 9 ferramentas
- [ ] Os três gates passam

## Vem de

D-021, FR-04, FR-05, FR-12, FR-13, D-012. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/core/search.py` (como a busca monta a lista e chama `record_search`), `src/rslapp/core/dedup.py`, `src/rslapp/core/repeat.py`, `src/rslapp/core/views.py`, `src/rslapp/store/__init__.py` e a parte do log (`format_log_entry`), `src/rslapp/server.py` (as ferramentas e `_build_http_mcp_server`) e `src/rslapp/prompts.py`.

Cerca de 350 linhas. Um commit para a junção no miolo e no armazenamento, outro para a ferramenta e o prompt, com D-021 no comentário e no nome dos testes.

## Resultado da entrega

- **Miolo e armazenamento (`src/rslapp/core/merge.py`, `src/rslapp/core/repeat.py`, `src/rslapp/store/log.py`):**
  - Implementada função `run_merge(store, list_ids, request_summary)` com validação estrita de entradas (2 a 20 listas, sem repetição, formato `l-NNNN`), verificação prévia de existência de todas as listas (gerando `list_not_found` sem nada gravar se alguma faltar), agrupamento e deduplicação de artigos preservando ordem, unindo `source_ids` e `citations` de registros duplicados e computando `duplicates_removed`.
  - Tratamento de estado `incomplete` com `incomplete_from` quando qualquer lista de origem estiver incompleta.
  - Gravação de lista (`l-NNNN`), busca (`s-NNNN` com `kind: "merge"`, `merged_from`, `origin_totals`, `duplicates_removed`, `total`, `params`) e entrada formatada no `log.md`.
  - `format_log_entry` estendido para `kind: "merge"` ("junção"), exibindo pedido, lista gerada com total, duplicatas removidas e listas de origem com seus totais.
  - `run_repeat` atualizado para recusar registros com `kind: "merge"` com código `invalid_input` e mensagem `uma junção não pode ser repetida; repita as buscas de origem` (D-021).
- **Servidor MCP e Prompt (`src/rslapp/server.py`, `src/rslapp/prompts.py`):**
  - Ferramenta `merge_lists(list_ids, request_summary="")` exposta no MCPServer stdio e registrada em `_build_http_mcp_server`. O servidor passa a ter 9 ferramentas.
  - No modo HTTP, o acesso a listas é isolado por pessoa (`_build_tool_store()`), impedindo acesso a listas de outras pessoas (`list_not_found`).
  - Prompt `plan_search` atualizado orientando a manter assuntos distintos em listas separadas e utilizar `merge_lists` após buscas quando o mesmo assunto utilizar múltiplas strings.
- **Testes e contagens atualizadas:**
  - `tests/core/test_merge.py` (7 testes unitários do miolo e armazenamento).
  - `tests/test_merge_lists.py` (7 testes de integração do servidor MCP stdio e modo HTTP multiusuário).
  - `tests/test_prompts.py` atualizado com teste da orientação de `merge_lists`.
  - `tests/test_server_new_sources.py`, `tests/test_server_http.py` e `tests/auth/test_oauth_flow_http.py` atualizados para a nova contagem de 9 ferramentas.

## Como testar

1. **Testes automatizados da ferramenta e miolo:**
   ```bash
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/core/test_merge.py tests/test_merge_lists.py
   ```
   Deve passar todos os 14 testes cobrindo deduplicação por DOI, deduplicação sem DOI por título/ano, propagação de status incompleto, erros de validação, formatação de log, recusa de `repeat_search` e isolamento multiusuário em HTTP.

2. **Verificar listagem de ferramentas e execução via cliente MCP:**
   No servidor stdio ou HTTP autenticado, chamar `tools/list` e verificar que 9 ferramentas são listadas, incluindo `merge_lists`.
   Chamar `merge_lists` com `list_ids` de listas existentes e verificar retorno com `search_id`, `list_id`, `merged_from`, `duplicates_removed`, `status`, `total` e `works` da primeira página.
