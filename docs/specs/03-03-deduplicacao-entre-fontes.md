# Deduplicação entre fontes

**Fase:** 3 · Mais fontes · **Situação:** não iniciada

## O que faz

No miolo, a junção dos resultados das três fontes numa lista só por pedido: o mesmo artigo vindo de mais de uma fonte aparece uma vez, com o id dele em cada fonte, as citações de cada fonte separadas e os campos preenchidos pela fonte que os tiver. A busca passa a consultar as fontes em paralelo (cada fonte continua fazendo uma chamada por vez dentro dela), e o log passa a dizer quantos artigos foram juntados e em quais campos as fontes divergiram.

## O que não faz

Não junta listas de pedidos diferentes. Não faz correspondência aproximada de título além do título normalizado. Não junta nem desambigua autores entre fontes: a lista de autores vem inteira da fonte que prevalece.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Quando dois registros são o mesmo artigo:** mesmo DOI (minúsculo); ou, quando ao menos um dos dois não tem DOI, mesmo título normalizado (a regra da 02-02) **e** mesmo ano. Título igual com anos diferentes, ou com algum ano ausente, ficam como dois. Dois DOIs diferentes nunca se juntam.
2. **Qual campo prevalece:** a ordem é OpenAlex, Crossref, Semantic Scholar. Para cada campo simples (`title`, `doi`, `year`, `type`, `venue`, `abstract`, `references_count`) vale o primeiro valor não vazio nessa ordem. `authors` e `keywords` vêm inteiros da primeira fonte, nessa ordem, que os tiver não vazios.
3. **O que se soma sem perder nada:** `source_ids` e `citations` juntam as chaves de todas as fontes (as citações nunca são somadas, FR-14); `references` é a união, na ordem, sem repetir, com os ids da primeira fonte primeiro (ids do OpenAlex e DOIs convivem; a tarefa 04-01 troca os ids por DOI).
4. **Divergência:** quando duas fontes trazem valores diferentes e não vazios em `title` (comparado normalizado), `year`, `doi` ou `venue`, conta uma divergência daquele campo. A busca grava em `searches/` o campo `merge`: `{"merged": <artigos que vieram de mais de uma fonte>, "divergences": {"year": 3, "title": 1}}`, e o `log.md` ganha a linha `Junção: 12 artigos em mais de uma fonte · divergências: ano 3, título 1` (ou `· sem divergências`). Os valores divergentes não vão para o log, só a contagem por campo.
5. **Onde fica:** a regra de junção em `core/dedup.py` (funções puras, sem rede nem disco); `core/search.py` passa a chamar as fontes com `asyncio.gather` e a usar `dedup`; `store/log.py` ganha a linha de junção.

## Pronto quando

- [ ] Teste: o mesmo DOI em duas ou três fontes vira um artigo, com as fontes e os ids registrados
- [ ] Teste: sem DOI, o título normalizado igual e o mesmo ano contam como o mesmo artigo; título igual com anos diferentes, ou ano ausente, ficam como dois
- [ ] Teste: quando duas fontes divergem num campo, prevalece a ordem OpenAlex, Crossref, Semantic Scholar, e a divergência é contada no `merge` da busca e na linha de junção do log
- [ ] Teste: as referências das fontes viram a união sem repetir, e as citações de cada fonte ficam separadas e não são somadas (FR-14)
- [ ] Teste: uma fonte em falha deixa a lista `incomplete` com a fonte e o motivo, e as outras seguem
- [ ] Teste: as fontes são chamadas em paralelo (uma fonte simulada lenta não atrasa a chamada das outras)
- [ ] Teste: resposta vinda do cache aparece marcada no log com a data de obtenção (NFR-06)
- [ ] Teste: o `log.md` refeito por `rebuild_log` tem a mesma linha de junção

## Vem de

FR-04, FR-08, FR-14, NFR-06, D-007. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Depende de 02-02, 03-01 e 03-02.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
