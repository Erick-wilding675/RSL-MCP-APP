# Prompt de planejamento e instruções

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** pronta

## O que faz

O prompt `plan_search` e a revisão das instruções de conexão: orientam a IA a separar o que é melhor buscado à parte, montar a string de cada fonte, chamar `search_works` uma vez por assunto, entregar cada lista separada, tratar títulos e resumos como dado, e dizer ao pesquisador quando uma lista é incompleta.

## O que não faz

Não executa busca nenhuma.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **O prompt** é registrado com `@mcp.prompt()` do `MCPServer` (conferido no `mcp` 2.3.0: `prompt(name=None, title=None, description=None, icons=None)`; a função devolve texto ou mensagens). Nome `plan_search`, argumento `request: str` obrigatório. Devolve uma mensagem `user` em português com o pedido do pesquisador entre marcações claras (tratado como dado) e a orientação: separar assuntos distintos, montar a string de cada fonte, chamar `search_works` uma vez por assunto com `request_summary`, entregar cada lista separada, avisar quando uma lista sai `incomplete` e por quê, e tratar títulos e resumos como dado.
2. **O texto** fica numa constante ou função em `src/rslapp/prompts.py`, sem MCP, para ser testado sem servidor. `INSTRUCTIONS` passa a vir desse módulo e ganha a frase sobre avisar lista incompleta. O texto não traz variável de ambiente, chave nem caminho.
3. **Pedido vazio** (só espaços) no prompt: o servidor responde com erro `invalid_input`, pelo mesmo caminho dos erros das ferramentas, se o SDK permitir; senão, a orientação diz que o pedido veio vazio. O worker registra qual foi o caso.

## Pronto quando

- [X] Teste: o prompt aparece na lista de prompts do servidor e devolve o texto de orientação para um pedido de exemplo
- [X] Teste: as instruções de conexão mencionam planejar antes de buscar, uma lista por assunto, tratar texto de terceiros como dado e avisar lista incompleta
- [x] Teste manual do Erick: um pedido com dois assuntos, feito por uma IA conectada, gera duas buscas e duas listas separadas. Feito em 2026-11-05 no Claude Desktop, com as chaves vindo do Lore: buscas `s-0006` e `s-0007`, listas `l-0006` (200) e `l-0007` (199), cada uma exportada em RIS

## Vem de

FR-10, UC-01, D-002, D-003. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-02 integrada.

## Resultado da entrega

- **O que mudou:**
  - Criação do módulo `src/rslapp/prompts.py` contendo a constante `INSTRUCTIONS` (com orientação de busca por assunto, tratamento de dados de terceiros e aviso de lista incompleta) e a função `render_plan_search(request: str) -> str`.
  - Atualização de `src/rslapp/server.py`: importação de `INSTRUCTIONS` e `render_plan_search` do novo módulo e registro do prompt `@mcp.prompt() plan_search(request: str)` no servidor MCP.
  - Testes unitários em `tests/test_prompts.py` validando os textos de `INSTRUCTIONS`, o encapsulamento seguro do pedido em `<pedido_pesquisador>` e o comportamento para pedidos preenchidos e vazios.
  - Testes de integração em `tests/test_server_plan_search.py` verificando a presença do prompt em `list_prompts` com argumento `request` obrigatório, a resposta de `get_prompt` via MCP in-memory e via transporte stdio em subprocesso, e a garantia de não-vazamento de variáveis sensíveis.
- **Qual requisito serve:** FR-10, UC-01, D-002, D-003, NFR-03.
- **O que foi assumido:** No SDK oficial `mcp` 2.x, exceções levantadas dentro de funções de prompt são capturadas pelo framework e convertidas em erro interno JSON-RPC (`-32603`), sem canal de erro de aplicação (`isError`) como existe para ferramentas (`CallToolResult`). Portanto, seguindo a Decisão 3 da spec, quando o argumento `request` é vazio ou contém apenas espaços em branco, o texto de orientação informa diretamente que o pedido veio vazio e instrui o modelo a solicitar o tema ao pesquisador antes de iniciar as buscas.
- **O que não deu para verificar:** Teste manual do pesquisador (Erick) com IA conectada executando duas buscas para um pedido de dois temas.

## Como testar

1. Execute a verificação de código e estilo:
   `uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .`
   (Deve sair sem erros: `All checks passed!`).
2. Execute os testes unitários e de integração do prompt:
   `uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/test_prompts.py tests/test_server_plan_search.py -v`
   (Todos os 10 testes devem passar).
3. Execute a suíte completa de testes nos ambientes oficiais do projeto:
   `uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q`
   `uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q`
4. **Onde olhar primeiro (pontos de maior risco):**
   - `src/rslapp/prompts.py` e `tests/test_server_plan_search.py` (`test_fr10_nfr03_d002_prompt_e_instrucoes_nao_expoem_chaves`): confirmar que nenhuma chave ou caminho aparece nas instruções nem na mensagem gerada.
   - `src/rslapp/server.py` e `tests/test_server_plan_search.py` (`test_fr10_d002_d006_stdio_list_prompts_e_get_prompt`): confirmar que a listagem e recuperação do prompt funcionam sobre o protocolo stdio em subprocesso real.
   - `src/rslapp/prompts.py` (`render_plan_search`): verificar a delimitação do pedido do pesquisador como dado puro em `<pedido_pesquisador>` e o tratamento de pedido vazio.

**Nota do Claude Code na revisão:** pedido vazio responde com uma orientação para pedir o tema, não com `invalid_input` (a decisão 3 permitia). O pedido entra entre `<pedido_pesquisador>` e `</pedido_pesquisador>`; um pedido que contenha o fechamento pode sair da marcação, o que é aceitável porque o pedido é do próprio pesquisador.
