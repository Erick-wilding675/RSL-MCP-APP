# Achar um artigo e repetir uma busca

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

## O que faz

As ferramentas `find_work` (por título ou DOI, devolve os candidatos numa lista própria) e `repeat_search` (refaz uma busca do log com as mesmas strings e as mesmas fontes, grava busca e lista novas com `repeated_from`, e não mexe na original).

## O que não faz

Não altera nenhuma busca ou lista já gravada.

## Pronto quando

- [ ] Teste: `find_work` por DOI exato devolve o artigo; por título parecido devolve candidatos; sem resultado devolve lista vazia registrada
- [ ] Teste: `repeat_search` usa as strings originais de cada fonte e gera `s-` e `l-` novos, com `repeated_from` apontando para a original
- [ ] Teste: a busca original e a lista original continuam idênticas depois da repetição
- [ ] Teste: se uma fonte usada antes está sem chave, a repetição segue com as outras e marca a falha

## Vem de

FR-02, FR-11, UC-02, UC-03, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Depende de 03-03.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
