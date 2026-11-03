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

- **O que mudou:**
  - Criação dos quatro novos exportadores em `src/rslapp/exporters/`:
    - `csv.py` (`CSVExporter`): formato CSV compatível com Scopus / VOSviewer (UTF-8 com BOM, delimitador vírgula, RFC 4180), contendo as 19 colunas especificadas (`Authors`, `Author full names`, `Title`, `Year`, `Source title`, `DOI`, `Abstract`, `Author Keywords`, `References`, `Cited by`, `Affiliations`, `Document Type`, `Source`, `OpenAlex ID`, `Crossref DOI`, `Semantic Scholar ID`, `Citations OpenAlex`, `Citations Crossref`, `Citations Semantic Scholar`). Resumo preserva aspas, vírgulas e quebras de linha. Resolução automática das referências OpenAlex para DOI via cache/serviço da 04-01 (`resolve_reference_dois`), omitindo referências sem DOI e retornando avisos se incompleta.
    - `json.py` (`JSONExporter`): exportação do registro completo da lista salva (`id`, `search_id`, `status`, `total`, `works`), acrescido de `exported_at` (ISO 8601 UTC) e `format_version: 1`, indentado e em UTF-8.
    - `dois.py` (`DOIsExporter`): lista de um DOI por linha (`<list_id>.dois.txt`), incluindo apenas os trabalhos que possuem DOI e reportando no campo `count` o número exato de linhas com DOI.
    - `openalex_url.py` (`OpenAlexURLExporter`): gera as URLs de consulta aceitas pelo VOSviewer (`https://api.openalex.org/works?filter=openalex:...`) agrupadas em lotes de até 100 IDs em `<list_id>.openalex.txt`, devolvendo a primeira URL e o total de URLs (`count`). Retorna erro `format_not_available` se a lista não possuir trabalhos do OpenAlex. Nenhuma chave de API é inserida nas URLs.
  - Atualização de `src/rslapp/exporters/__init__.py`: registro dos exportadores no catálogo de formatos suportados (`ris`, `csv`, `json`, `dois`, `openalex_url`) e orquestração em `run_export` com tratamento síncrono/assíncrono para resolução de referências e coleta de avisos e campos extras (`url`).
  - Atualização de `src/rslapp/server.py`: documentação da ferramenta `export_list` aceitando os cinco formatos.
  - Adição de testes unitários em `tests/exporters/` (`test_csv.py`, `test_json.py`, `test_dois.py`, `test_openalex_url.py`) e testes de integração de ferramenta MCP em `tests/test_server_export_list.py`.
- **Requisitos atendidos:** FR-06 (exportação de listas nos formatos solicitados), FR-12 (armazenamento e exportação de listas salvas), D-002 (ferramenta `export_list` do servidor MCP). Âncoras adicionadas aos comentários e nomes de testes.
- **Assunções adotadas:** `Author full names` no CSV replica os nomes completos dos autores separados por `; `, preservando o formato esperado pelo VOSviewer; e quando a resolução de referências falha ou está sem chave de API, o arquivo é gravado com o que foi possível resolver e a resposta inclui `warnings: ["referências: <motivo>"]`.
- **O que não deu para verificar:** A abertura manual dos arquivos exportados diretamente dentro da interface gráfica do VOSviewer (T-008), que depende do teste manual do Erick.

## Como testar

1. **Testes automatizados completos:**
   - Executar os gates do projeto:
     ```powershell
     uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
     uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
     uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
     ```
   - Deve aparecer: `All checks passed!` no ruff e `186 passed` em ambos os testes do pytest.

2. **Onde olhar primeiro (pontos de risco):**
   - `src/rslapp/exporters/csv.py` e `tests/exporters/test_csv.py`: verificar a gravação do BOM UTF-8 (`\xef\xbb\xbf`), a troca de referências do OpenAlex para DOI e a preservação de quebras de linha e aspas no resumo ao reler via módulo `csv`.
   - `src/rslapp/exporters/openalex_url.py` e `tests/exporters/test_openalex_url.py`: conferir que nenhuma URL contém credenciais/chaves, que o agrupamento respeita o limite de 100 IDs por filtro, e que listas sem trabalhos do OpenAlex levantam `format_not_available`.
   - `src/rslapp/exporters/__init__.py`: conferir a execução da resolução de referências dentro de `run_export` e o repasse de `warnings` e `url` sem quebrar o transporte síncrono do servidor MCP.
