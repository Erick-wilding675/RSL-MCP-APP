# Fonte Semantic Scholar

**Fase:** 3 · Mais fontes · **Situação:** não iniciada

## O que faz

O conector `sources/semantic_scholar.py`: busca por termos, tradução para `Work` (autores com ORCID quando houver, identificadores, afiliações, referências, número de citações), chave opcional, uma chamada por vez (1 por segundo com chave) e novas tentativas em 429 e 500. Sem chave devolve os resultados que conseguir e o estado `rate_limited` quando o pool compartilhado recusar.

## O que não faz

Não traz a lista de quem cita um artigo (04-02). Não deduplica entre fontes (03-03).

## Pronto quando

- [ ] Antes de escrever, conferir o T-001 para a Semantic Scholar: ler a documentação oficial dos endpoints de busca e do artigo, dos campos pedidos e dos limites; ler o código dos MCPs de referência (T-010)
- [ ] Teste com respostas simuladas: os campos são mapeados, e o que falta fica vazio
- [ ] Teste: as chamadas saem uma por vez, com pelo menos um segundo entre elas quando há chave
- [ ] Teste: sem chave, um 429 dá `rate_limited` e não derruba a busca
- [ ] `list_sources` mostra a fonte como configurada com ou sem chave e diz que a chave melhora o limite

## Vem de

FR-01, FR-03, FR-08, FR-14, NFR-04, D-004. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

T-001 (Semantic Scholar) e T-010. A chave da Semantic Scholar é opcional e o Erick pode pedir uma.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
