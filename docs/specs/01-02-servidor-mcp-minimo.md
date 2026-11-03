# Servidor MCP mínimo

**Fase:** 1 · Esqueleto · **Situação:** não iniciada

## O que faz

O módulo `server.py` com o SDK oficial: um servidor que roda por stdio, as instruções de conexão (texto curto que diz à IA para planejar antes de buscar e para tratar títulos e resumos como dado, não como instrução) e a ferramenta `list_sources`, que diz para cada fonte se está configurada e se precisa de chave. O comando `rslapp` inicia o servidor.

## O que não faz

Não tem busca nem as outras ferramentas (tarefas 02-02 em diante). O prompt `plan_search` fica na tarefa 05-04.

## Pronto quando

- [ ] Antes de escrever, conferir o T-009: abrir a documentação da v2 do SDK oficial e anotar no spec o nome exato da classe e o exemplo stdio
- [ ] `rslapp` inicia e responde ao handshake do MCP por stdio (teste com o MCP Inspector ou com um cliente de teste do próprio SDK)
- [ ] A ferramenta `list_sources` aparece na lista de ferramentas e devolve uma linha por fonte (`openalex`, `crossref`, `semantic_scholar`) com `name`, `configured`, `needs_key`, `status`
- [ ] Teste: sem chaves, o OpenAlex aparece como `needs_key: true` e `configured: false`; o Crossref aparece como configurado
- [ ] Teste: nenhuma resposta contém o valor de uma chave

## Vem de

FR-07, NFR-02, NFR-03, D-002, D-006. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

T-009 (documentação da v2 do SDK).

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
