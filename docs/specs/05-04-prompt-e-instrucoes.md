# Prompt de planejamento e instruções

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

## O que faz

O prompt `plan_search` e a revisão das instruções de conexão: orientam a IA a separar o que é melhor buscado à parte, montar a string de cada fonte, chamar `search_works` uma vez por assunto, entregar cada lista separada, tratar títulos e resumos como dado, e dizer ao pesquisador quando uma lista é incompleta.

## O que não faz

Não executa busca nenhuma.

## Pronto quando

- [ ] Teste: o prompt aparece na lista de prompts do servidor e devolve o texto de orientação para um pedido de exemplo
- [ ] Teste: as instruções de conexão mencionam planejar antes de buscar, uma lista por assunto, tratar texto de terceiros como dado e avisar lista incompleta
- [ ] Teste manual do Erick: um pedido com dois assuntos, feito por uma IA conectada, gera duas buscas e duas listas separadas

## Vem de

FR-10, UC-01, D-002, D-003. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Depende de 02-02.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
