# Deduplicação entre fontes

**Fase:** 3 · Mais fontes · **Situação:** não iniciada

## O que faz

No miolo, a junção dos resultados das três fontes numa lista só por pedido: o mesmo artigo vindo de mais de uma fonte aparece uma vez, com a lista das fontes em que apareceu e o id dele em cada uma, e os campos preenchidos pela fonte que os tiver. A busca passa a consultar as fontes em paralelo, e o log passa a marcar o que veio do cache, com a data de obtenção.

## O que não faz

Não junta listas de pedidos diferentes. Não faz correspondência aproximada de título além do título normalizado.

## Pronto quando

- [ ] Teste: o mesmo DOI em duas ou três fontes vira um artigo, com as fontes e os ids registrados
- [ ] Teste: sem DOI, o título normalizado igual e o mesmo ano contam como o mesmo artigo; título igual com anos diferentes ficam como dois
- [ ] Teste: quando duas fontes divergem num campo, prevalece a ordem OpenAlex, Crossref, Semantic Scholar, e a divergência é registrada no log
- [ ] Teste: uma fonte em falha deixa a lista `incomplete` com a fonte e o motivo, e as outras seguem
- [ ] Teste: resposta vinda do cache aparece marcada no log com a data de obtenção (NFR-06)
- [ ] Teste: as citações de cada fonte ficam separadas e não são somadas (FR-14)

## Vem de

FR-04, FR-08, NFR-06, D-007. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Depende de 02-02, 03-01 e 03-02.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
