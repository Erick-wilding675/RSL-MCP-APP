# Entradas numéricas sem verdadeiro/falso

**Fase:** 7 · Manutenção depois da v1 · **Situação:** pronta

## O que faz

As seis entradas numéricas das ferramentas passam a recusar `true` e `false`, com o erro `invalid_input`. Hoje o SDK (`mcp` 2.3.0, validação do pydantic no modo tolerante) converte `true` em 1 e `false` em 0 antes de chegar ao miolo. Assim `get_list(page_size=false)` vira `page_size=0`, e as checagens de booleano que o miolo já tem (`core/find.py`, `core/related.py`) nunca são alcançadas.

As entradas são:

| Ferramenta | Entrada |
|---|---|
| `search_works` | `max_results` |
| `get_related_works` | `max_results` |
| `find_work` | `max_results` |
| `get_list` | `page`, `page_size` |
| `get_search_log` | `limit` |

## O que não faz

- **Não fica estrito em tudo.** O número escrito como texto (`"2"`) e o número com `.0` (`2.0`) continuam aceitos e viram 2. O próprio SDK registra que o Claude Desktop costuma mandar entradas como texto; recusar isso quebraria clientes reais. O que já é recusado hoje (`2.5`, `"abc"`, número numa entrada de texto) continua recusado.
- Não muda as entradas de texto nem de lista: o probe de 2026-11-09 mostrou que o SDK já recusa número em `query`, `list_id`, `detail`, `format`, `doi` e `search_id`, e texto solto em `sources`.
- Não muda o esquema JSON das ferramentas: as seis entradas continuam `"type": "integer"`.
- Não publica versão nova no PyPI. Publicar a 1.0.1 é decisão do Erick depois do teste.

## Decisões desta spec

Tomadas pelo Claude em 2026-11-09, baratas de desfazer, dentro da proposta pendente que o Erick aprovou ("prossiga"):

- **Recusar só o booleano**, em vez de usar `StrictInt` do pydantic: o `StrictInt` também recusaria `"2"`, e o `pre_parse_json` do SDK não converte texto em número (pula `str | int | float`), então o número como texto chega cru à validação.
- **Um tipo só, no servidor:** um `Annotated[int, BeforeValidator(...)]` definido uma vez em `src/rslapp/server.py` e usado nas seis assinaturas. A recusa acontece na validação do SDK, antes do miolo; as checagens do miolo ficam como defesa para quem chama as funções `run_*` direto.
- **Mensagem:** o `ValueError` do validador começa com `invalid_input:` e diz o nome da entrada quando possível (`invalid_input: deve ser um número inteiro, não true/false` serve). O SDK a entrega como erro da ferramenta, como faz hoje com `2.5`.

## Pronto quando

- [X] Teste, pelo cliente MCP em memória (como em `tests/test_server_get_list.py`): cada uma das seis entradas com `true` e com `false` volta como erro da ferramenta (`isError`) com `invalid_input` no texto, e o miolo não é chamado (nenhuma lista nem entrada de log nova; nas ferramentas de busca, nenhuma fonte consultada)
- [X] Teste: `get_list` com `page="2"` e com `page=2.0` devolve a página 2, como hoje
- [X] Teste: `page=2.5` continua recusado
- [X] Teste: o `inputSchema` das seis entradas, em `list_tools`, continua `"type": "integer"` com o mesmo padrão de antes
- [X] Os testes que já existem passam sem mudança de comportamento
- [X] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-002 (as chamadas e suas entradas, `docs/interface-contract.md`, código `invalid_input`). Acompanhamento da revisão da 05-02. É o identificador que o código leva como âncora, no comentário do tipo novo e no nome dos testes.

## Antes de começar

Ler `src/rslapp/server.py` inteiro e, no SDK instalado, `.venv/Lib/site-packages/mcp/server/mcpserver/utilities/func_metadata.py`: `func_metadata` (como monta o modelo dos argumentos a partir de `Annotated`) e `pre_parse_json`. Conferir na documentação do pydantic 2 o `BeforeValidator` antes de usar. O SDK é a versão 2 (`from mcp.server import MCPServer`), não a 1.

Um commit só, com D-002 no comentário e no nome dos testes. Cabe em menos de 400 linhas.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/server.py`: criado o validador `_reject_bool(v, info)` e o tipo `NonBoolInt = Annotated[int, BeforeValidator(_reject_bool)]` (marcado com `# D-002`), recusando valores `bool` com `ValueError("invalid_input: ...")` antes da coerção de `int` pelo Pydantic e aplicando `NonBoolInt` às seis entradas (`search_works.max_results`, `get_related_works.max_results`, `find_work.max_results`, `get_list.page`, `get_list.page_size` e `get_search_log.limit`).
  - `tests/test_server_int_inputs.py`: suíte de testes via `Client(server.mcp)` cobrindo a recusa de `True` e `False` nas seis entradas sem acionar o miolo nem criar listas/logs, a aceitação de `"2"` e `2.0` em `page`, a recusa de `2.5` em `page` e a preservação de `"type": "integer"` e `default` no `input_schema` de `list_tools`.
- **Requisito servido:** D-002.
- **O que foi assumido:** o uso de `ValidationInfo` do Pydantic no `BeforeValidator` permite incluir o nome do campo na mensagem de erro (`invalid_input: <campo> deve ser um número inteiro, não true/false`) sem alterar o esquema JSON gerado pelo SDK.
- **O que não deu para verificar:** nada; todos os cenários da spec foram verificados em memória.

## Como testar

Rode os três gates na raiz do repositório:

```bash
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
```

- **O que deve aparecer:** `All checks passed!` no `ruff check .` e todos os testes passando (`471 passed`, incluindo os 16 novos casos em `tests/test_server_int_inputs.py`) tanto no Python 3.10 quanto no Python 3.14.
- **Onde olhar primeiro (pontos mais arriscados, do mais difícil para o mais simples):**
  1. **Interação entre `pre_parse_json` do SDK e `BeforeValidator` (`src/rslapp/server.py`):** garantir que `NonBoolInt` barra `True`/`False` antes de o Pydantic converter booleano em `1`/`0`, mas deixa passar `"2"` (texto cru não convertido por `pre_parse_json`) e `2.0` para a validação normal de `int`, mantendo `2.5` recusado.
  2. **Não acionamento do miolo e ausência de efeitos colaterais (`tests/test_server_int_inputs.py`):** confirmar que falhas de validação em `max_results`, `page`, `page_size` e `limit` interrompem a execução na camada do SDK antes de instanciar fontes ou gravar arquivos de lista e log.
  3. **Preservação do contrato JSON Schema (`list_tools`):** verificar que `Annotated[int, BeforeValidator(_reject_bool)]` com `from __future__ import annotations` é avaliado por `func_metadata` mantendo `"type": "integer"` e os valores `default` originais nas seis entradas.

**Revisão do Claude (2026-11-09):** aprovada. Gates refeitos na revisão: ruff limpo, 471 testes em 3.10 e em 3.14. O `input_schema` das oito ferramentas, comparado byte a byte com o da `main`, ficou idêntico. Acompanhamento, não bloqueia: o teste de `2.5` só confere `is_error`, sem olhar a mensagem.

**Teste manual do Erick (opcional):** o Claude Desktop usa o `rslapp` do PyPI, então só vê a mudança depois de uma versão nova (1.0.1). Para conferir antes da versão nova, rode `uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q tests/test_server_int_inputs.py` e veja `16 passed`.

**Publicação (2026-11-09):** `rslapp` 1.0.1 no PyPI (wheel e sdist, token do Lore), conferido com `uvx --no-cache --from rslapp==1.0.1`. Tag `v1.0.1` e release no GitHub. Testada pelo Erick no Claude Desktop em 2026-11-10: pronta.
