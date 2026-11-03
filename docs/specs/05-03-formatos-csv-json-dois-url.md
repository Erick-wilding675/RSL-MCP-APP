# CSV, JSON, lista de DOIs e URL do OpenAlex

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

## O que faz

Os exportadores `csv.py`, `json.py` (registro completo, com autores, afiliações, referências e citações por fonte), `dois.py` (um DOI por linha) e `openalex_url.py` (a URL da consulta do OpenAlex que o VOSviewer aceita, só para listas que vieram do OpenAlex). A ferramenta `export_list` aceita todos os formatos.

## O que não faz

Não abre o VOSviewer. Não cria formatos de outras ferramentas.

## Pronto quando

- [ ] Teste: cada formato gera o arquivo esperado para a mesma lista de exemplo
- [ ] Teste: `openalex_url` numa lista que não veio do OpenAlex devolve `format_not_available`
- [ ] Teste: o JSON guarda tudo o que a lista guarda; o CSV, as colunas combinadas
- [ ] Teste manual do Erick: o CSV e a lista de DOIs abrem no VOSviewer; a URL do OpenAlex funciona (T-008)

## Vem de

FR-06, FR-12, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Depende de 02-03.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
