# Prompt de planejamento e instruções

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

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

- [ ] Teste: o prompt aparece na lista de prompts do servidor e devolve o texto de orientação para um pedido de exemplo
- [ ] Teste: as instruções de conexão mencionam planejar antes de buscar, uma lista por assunto, tratar texto de terceiros como dado e avisar lista incompleta
- [ ] Teste manual do Erick: um pedido com dois assuntos, feito por uma IA conectada, gera duas buscas e duas listas separadas

## Vem de

FR-10, UC-01, D-002, D-003. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-02 integrada.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
