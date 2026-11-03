# Armazenamento em arquivos

**Fase:** 1 · Esqueleto · **Situação:** não iniciada

## O que faz

O pacote `store/`, que grava e lê tudo na pasta de dados: `searches/s-NNNN.json`, `lists/l-NNNN.json`, `log.md` e `cache/<fonte>/<chave>.json`. Toda gravação é atômica (arquivo temporário e renomear). Os ids são sequenciais, `s-0001` e `l-0001`, com ao menos quatro dígitos. O log legível `log.md` ganha uma entrada a cada busca e pode ser refeito a partir de `searches/`. O cache guarda a resposta, a data de obtenção e a de expiração (padrão de 7 dias, `RSL_CACHE_DAYS`); a chave do cache nunca inclui a chave de API.

## O que não faz

Não decide o que uma busca contém (isso vem da tarefa 02-02). Não apaga nem reescreve busca, lista ou entrada do log depois de gravada.

## Pronto quando

- [ ] Teste: gravar uma lista, uma busca e uma entrada de log, e lê-las de volta iguais
- [ ] Teste: se a gravação é interrompida no meio, nenhum arquivo fica pela metade
- [ ] Teste: ordem de gravação lista, busca, log; apagar o `log.md` e chamar o refazer reconstrói o log a partir de `searches/`
- [ ] Teste: uma lista já gravada não pode ser alterada pela API do módulo
- [ ] Teste: cache dentro do prazo devolve a resposta e diz que veio do cache, com a data de obtenção; cache vencido é ignorado
- [ ] Teste: a chave de API não aparece em nenhum arquivo gravado nem na chave do cache
- [ ] O `log.md` segue o formato abaixo, legível por pessoas e pronto para anexar na metodologia (FR-13)

## Formato do `log.md`

Uma entrada por busca, a mais nova por último, no texto abaixo (exemplo):

```
## s-0007 · 2026-11-02 16:41 UTC · busca por termos
Pedido: Artigos sobre interpretabilidade de modelos de aprendizado de máquina
Lista: l-0007 · incompleta · 187 artigos
- openalex · ok · encontrados 412, trazidos 100 · cache: não · string: `machine learning interpretability`
- semantic_scholar · rate_limited · HTTP 429 depois de 3 tentativas · string: `machine learning interpretability`
- crossref · ok · encontrados 230, trazidos 100 · cache: sim, obtida em 2026-11-01 · string: `machine learning interpretability`
```

Quando a busca repete outra, a entrada ganha a linha `Repetida de: s-0003`. Quando é uma lista de referências ou citações, ganha `Artigo de origem: <DOI ou id> · direção: citações`. O tipo no cabeçalho é um de: busca por termos, busca de artigo, referências, citações, repetição. As chaves de API nunca aparecem. O Claude Code pode ajustar o texto na entrega, mantendo todas essas informações.

## Vem de

FR-05, FR-09, FR-12, FR-13, NFR-03, NFR-06, D-007. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Nenhuma.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
