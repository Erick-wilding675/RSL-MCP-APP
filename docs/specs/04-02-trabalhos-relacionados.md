# Referências e citações de um artigo

**Fase:** 4 · Referências e citações · **Situação:** não iniciada

## O que faz

A ferramenta `get_related_works` e o miolo por trás dela. Dado um DOI ou um id e a direção (`references` ou `citations`), consulta as fontes que entregam o dado (OpenAlex por `referenced_works` e pelo filtro `cites`; Semantic Scholar pelos endpoints de citações e referências), junta e tira as duplicatas, aplica o teto (padrão 1.000, ajustável) e grava uma lista própria, com a busca ligada ao artigo de origem e à direção. As fontes que não entregam o dado aparecem como `not_supported`.

## O que não faz

Não busca por tema. Não é chamada dentro de `search_works`.

## Pronto quando

- [ ] Teste com respostas simuladas: as citações de um artigo viram uma lista própria, ligada ao artigo de origem no log com a direção
- [ ] Teste: com mais trabalhos que o teto, a lista sai `incomplete` com o motivo; com a Semantic Scholar acima de 10 mil, o limite da fonte é o motivo
- [ ] Teste: a fonte que não entrega o dado aparece como `not_supported`, e o campo não é preenchido com valor suposto
- [ ] Teste: artigo de origem não achado devolve `work_not_found` e não grava lista
- [ ] Teste: a lista entra no log e pode ser exportada como qualquer outra

## Vem de

FR-15, FR-08, UC-04, D-005, D-010. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

T-005. Depende de 03-02 e 04-01.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
