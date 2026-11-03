# CSV, JSON, lista de DOIs e URL do OpenAlex

**Fase:** 5 · Resto das chamadas e formatos · **Situação:** não iniciada

## O que faz

Os exportadores `csv.py`, `json.py` (registro completo, com autores, afiliações, referências e citações por fonte), `dois.py` (um DOI por linha) e `openalex_url.py` (a URL da consulta do OpenAlex que o VOSviewer aceita, só para listas que vieram do OpenAlex). A ferramenta `export_list` aceita todos os formatos.

## O que não faz

Não abre o VOSviewer. Não cria formatos de outras ferramentas.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer. O que abre no VOSviewer só se confirma no teste do Erick (T-008); estas escolhas podem mudar depois dele.

1. **`csv`:** UTF-8 com BOM, separador vírgula, aspas onde precisar, uma linha por trabalho. Colunas com os nomes do CSV do Scopus, que o VOSviewer lê: `Authors` (nomes separados por `; `), `Author full names`, `Title`, `Year`, `Source title`, `DOI`, `Abstract`, `Author Keywords` (`; `), `References` (DOIs separados por `; `), `Cited by` (o maior número entre as fontes), `Affiliations` (`; `), `Document Type`, `Source` (`RSL.app`), e por fim `OpenAlex ID`, `Crossref DOI`, `Semantic Scholar ID`, `Citations OpenAlex`, `Citations Crossref`, `Citations Semantic Scholar`.
2. **Referências como DOI no CSV:** antes de escrever, os ids do OpenAlex das referências são trocados por DOI com o serviço da 04-01. Se a troca sai incompleta (sem chave, limite), o arquivo é gravado com o que deu, e a resposta ganha `warnings: ["referências: <motivo>"]`. Ids sem DOI não entram na coluna.
3. **`json`:** a lista salva inteira (`id`, `search_id`, `status`, `total`, `works` completos), mais `exported_at` e `format_version: 1`, indentada, UTF-8.
4. **`dois`:** um DOI por linha, só os trabalhos que têm DOI, na ordem da lista; `count` é o número de linhas.
5. **`openalex_url`:** só para listas em que algum trabalho tem `source_ids.openalex`; senão, `format_not_available`. Gera as URLs `https://api.openalex.org/works?filter=openalex:W1|W2|…` em grupos de 100 ids (o máximo do filtro) e grava uma por linha num `.txt`; a resposta traz `url` (a primeira) e `count` (quantas URLs). Nenhuma URL leva chave.
6. **Arquivos:** `<RSL_EXPORT_DIR>/<list_id>.<ext>` (`csv`, `json`, `dois.txt`, `openalex.txt`), com a mesma gravação atômica e os mesmos erros da 02-03.

## Pronto quando

- [ ] Teste: cada formato gera o arquivo esperado para a mesma lista de exemplo
- [ ] Teste: `openalex_url` numa lista que não veio do OpenAlex devolve `format_not_available`
- [ ] Teste: o JSON guarda tudo o que a lista guarda; o CSV, as colunas combinadas
- [ ] Teste manual do Erick: o CSV e a lista de DOIs abrem no VOSviewer; a URL do OpenAlex funciona (T-008)

## Vem de

FR-06, FR-12, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefas 02-03 e 04-01 integradas.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
