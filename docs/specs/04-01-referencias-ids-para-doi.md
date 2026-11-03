# Troca de ids de referências por DOI

**Fase:** 4 · Referências e citações · **Situação:** não iniciada

## O que faz

Um serviço no miolo que troca os ids das referências (por ora, ids do OpenAlex) por DOI, na exportação ou a pedido, usando o cache e agrupando os ids em poucas chamadas. Os ids sem DOI continuam como ids. O custo em chamadas de cada troca é medido e anotado.

## O que não faz

Não busca quem cita o artigo (04-02). Não troca ids na hora da busca (D-010).

## Pronto quando

- [ ] Antes de escrever, conferir o T-005: ver na documentação oficial do OpenAlex se um filtro por vários ids aceita muitos valores por chamada e a que custo, e anotar no spec
- [ ] Teste com respostas simuladas: uma lista de 120 ids vira DOI em poucas chamadas, e os ids sem DOI ficam como estão
- [ ] Teste: a segunda troca dos mesmos ids vem do cache e não gasta chamada
- [ ] Teste: se a troca falha no meio, o resultado é marcado incompleto e o motivo vai para o log
- [ ] Medida real, uma vez, com a chave do Erick: número de chamadas e créditos para trocar as referências de uma lista de 100 artigos, anotado no T-005

## Vem de

FR-14, D-005, D-010. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

T-005. Depende de 02-01.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
