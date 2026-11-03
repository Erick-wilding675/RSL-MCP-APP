# Troca de ids de referências por DOI

**Fase:** 4 · Referências e citações · **Situação:** não iniciada

## O que faz

Um serviço no miolo, `core/references.py`, que troca os ids das referências (ids do OpenAlex, `W123`) por DOI, para a exportação ou a pedido. Usa o cache e agrupa os ids em chamadas de até 100. Os ids sem DOI continuam como ids. O resultado diz quantas chamadas foram feitas, se a troca ficou completa e, se não, por quê. A chamada à API fica num método novo do conector do OpenAlex.

## O que não faz

Não busca quem cita o artigo (04-02). Não troca ids na hora da busca (D-010). Não grava log nem lista: quem chama o serviço (a exportação, na 05-03, e a 04-02) decide o que registrar com o estado e o motivo devolvidos. Não mexe em `server.py`.

## Conferência do T-005 (OpenAlex)

Feita pelo Claude Code em 2026-11-03 na página oficial de filtros (`help.openalex.org/api/filtering/`) e com uma chamada real sem chave:

- O OR com `|` aceita **até 100 valores** num filtro.
- O filtro de ids do OpenAlex é `openalex` (a API o reescreve como `ids.openalex`). Aceita a forma curta: `GET /works?filter=openalex:W2741809807|W2755950973&select=id,doi&per_page=100`. A página de filtros não nomeia esse filtro; o nome foi confirmado na chamada real.
- Um id que não existe é simplesmente omitido do resultado, sem erro.
- O custo medido foi `cost_usd: 0.0001` por chamada (uma chamada de lista), com até 100 ids. Trocar as referências de 100 artigos com 40 referências cada (4.000 ids, menos os repetidos) custa no máximo 40 chamadas, ou US$ 0,004.
- O `doi` volta como URL (`https://doi.org/10.7717/peerj.4375`), e `null` quando o trabalho não tem DOI.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Na API:** `OpenAlexSource.lookup_dois(ids: list[str]) -> DoiLookup` em `sources/openalex.py`, reaproveitando a montagem de cabeçalhos, a chave no cabeçalho, as novas tentativas e os estados que já existem (`_request_page` e `_retry_failure`). `select=id,doi`, `per_page=100`, no máximo 100 ids por chamada. Nunca levanta exceção.
2. **No miolo:** `async def resolve_reference_dois(ids, *, store, source) -> ReferenceResolution` em `core/references.py`:
   - tira repetidos e ignora o que não é id do OpenAlex (por exemplo, um DOI que já veio da Crossref fica como está);
   - olha o cache por id (`store.get_cache("openalex_doi", {"id": "W123"})`), e só chama a API para os que faltam, em grupos de 100;
   - grava no cache cada id respondido, inclusive os sem DOI (`{"doi": null}`), para não perguntar de novo. Um id omitido pela API também vai para o cache como sem DOI;
   - devolve `mapping: dict[str, str | None]` (id → DOI minúsculo sem prefixo, ou `None`), `calls: int`, `from_cache: int`, `complete: bool` e `reason: str | None`.
3. **Falha no meio:** se um grupo falha (sem chave, limite, rede), os grupos já trocados ficam, os ids do grupo que falhou ficam como `None` **sem** ir para o cache, `complete` é falso e `reason` diz o estado e o motivo da fonte. Sem `OPENALEX_API_KEY`, nenhuma chamada é feita e `reason` diz `missing_key`.
4. **Dataclasses** `DoiLookup` (em `sources/openalex.py`) e `ReferenceResolution` (em `core/references.py`), com nomes de campo em inglês.

## Pronto quando

- [x] Antes de escrever, conferir o T-005 (feito acima pelo Claude Code)
- [ ] Teste com respostas simuladas: uma lista de 120 ids vira DOI em 2 chamadas (100 e 20), cada chamada com o filtro `openalex:` e no máximo 100 ids; os ids sem DOI e os omitidos ficam `None`
- [ ] Teste: ids repetidos e entradas que não são ids do OpenAlex não geram chamada
- [ ] Teste: a segunda troca dos mesmos ids vem do cache e não gasta chamada (`calls == 0`)
- [ ] Teste: se a segunda chamada falha, o resultado tem os DOIs da primeira, `complete` falso e o motivo; os ids do grupo que falhou não vão para o cache
- [ ] Teste: sem chave, nenhuma chamada e `reason` com `missing_key`; com chave, ela vai só no cabeçalho
- [ ] Medida real, uma vez, com a chave do Erick: número de chamadas e créditos para trocar as referências de uma lista de 100 artigos, anotado no T-005. **É do Erick**

## Vem de

FR-14, NFR-01, NFR-03, D-005, D-010. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-01 integrada.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
