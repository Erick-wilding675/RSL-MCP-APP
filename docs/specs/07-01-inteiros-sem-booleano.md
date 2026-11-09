# Entradas numéricas sem verdadeiro/falso

**Fase:** 7 · Manutenção depois da v1 · **Situação:** a fazer

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

- [ ] Teste, pelo cliente MCP em memória (como em `tests/test_server_get_list.py`): cada uma das seis entradas com `true` e com `false` volta como erro da ferramenta (`isError`) com `invalid_input` no texto, e o miolo não é chamado (nenhuma lista nem entrada de log nova; nas ferramentas de busca, nenhuma fonte consultada)
- [ ] Teste: `get_list` com `page="2"` e com `page=2.0` devolve a página 2, como hoje
- [ ] Teste: `page=2.5` continua recusado
- [ ] Teste: o `inputSchema` das seis entradas, em `list_tools`, continua `"type": "integer"` com o mesmo padrão de antes
- [ ] Os testes que já existem passam sem mudança de comportamento
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-002 (as chamadas e suas entradas, `docs/interface-contract.md`, código `invalid_input`). Acompanhamento da revisão da 05-02. É o identificador que o código leva como âncora, no comentário do tipo novo e no nome dos testes.

## Antes de começar

Ler `src/rslapp/server.py` inteiro e, no SDK instalado, `.venv/Lib/site-packages/mcp/server/mcpserver/utilities/func_metadata.py`: `func_metadata` (como monta o modelo dos argumentos a partir de `Annotated`) e `pre_parse_json`. Conferir na documentação do pydantic 2 o `BeforeValidator` antes de usar. O SDK é a versão 2 (`from mcp.server import MCPServer`), não a 1.

Um commit só, com D-002 no comentário e no nome dos testes. Cabe em menos de 400 linhas.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega: os comandos dos três gates, o que deve aparecer e os pontos mais arriscados, o mais difícil primeiro)
