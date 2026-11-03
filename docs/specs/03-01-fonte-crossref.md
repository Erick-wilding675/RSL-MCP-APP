# Fonte Crossref

**Fase:** 3 · Mais fontes · **Situação:** não iniciada

## O que faz

O conector `sources/crossref.py` com a mesma interface do OpenAlex: busca por termos e por título, traduz o resultado para `Work` (título, autores com ORCID quando houver, afiliações, ano, periódico, resumo, DOI, referências, número de citações), usa o `RSL_CONTACT_EMAIL` na fila educada quando houver, e respeita o limite com novas tentativas.

## O que não faz

Não consulta citações de um artigo. Não deduplica entre fontes (03-03).

## Pronto quando

- [ ] Antes de escrever, conferir o T-001 para o Crossref: ler a documentação oficial da API e anotar os limites e os campos usados
- [ ] Teste com respostas simuladas: os campos acima são mapeados, e o que a Crossref não traz fica vazio, sem valor suposto
- [ ] Teste: 429 e 500 seguem a mesma regra de novas tentativas e estado do OpenAlex
- [ ] `list_sources` mostra a Crossref como configurada, sem chave

## Vem de

FR-01, FR-03, FR-14, NFR-04, D-004. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

T-001 (Crossref) e T-010.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
