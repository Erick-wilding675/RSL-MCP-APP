# Exportação em RIS

**Fase:** 2 · Fatia completa · **Situação:** para testar

## O que faz

A interface comum dos exportadores em `exporters/base.py`, o exportador `exporters/ris.py` e a ferramenta `export_list` (por ora só com `format="ris"`). O arquivo é gravado em `RSL_EXPORT_DIR` com o nome da lista e o caminho volta à IA. Os campos de RIS mapeados são tipo, título, autores, ano, periódico, resumo, palavras-chave e DOI.

## O que não faz

Não exporta CSV, JSON, lista de DOIs nem URL do OpenAlex (tarefa 05-03). Não troca ids de referências por DOI (04-01).

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Interface dos exportadores** em `exporters/base.py`: `Exporter` com `format: str`, `extension: str` e `def render(self, list_data: dict) -> str`, que recebe a lista salva (com `works` no formato `Work.to_dict()`) e devolve o texto. A gravação do arquivo fica fora do exportador, numa função comum, para os outros formatos (tarefa 05-03) reaproveitarem.
2. **Arquivo:** `<RSL_EXPORT_DIR>/<list_id>.ris` (por exemplo `l-0007.ris`), em UTF-8 e fim de linha `\r\n`, gravado de forma atômica (arquivo temporário e `os.replace`). Exportar de novo a mesma lista substitui o arquivo. A pasta é criada se não existir; se não aceita gravação, `export_folder_not_writable`.
3. **Erros:** como na 02-02, o miolo levanta `RSLError` e o servidor converte em `ToolError("<código>: <mensagem>")`. `list_not_found` vem de `Store.get_list` (que levanta `FileNotFoundError` ou `ValueError` para id malformado; os dois viram `list_not_found`).
4. **Mapeamento RIS:** `TY` (`JOUR` para `article`, `CONF` para trabalhos de evento quando o tipo indicar, `GEN` para o resto), `TI`, um `AU` por autor na ordem (`Sobrenome, Nome` só se a fonte já trouxer assim; senão o nome como veio), `PY`, `JO` (o periódico), `AB`, um `KW` por palavra-chave, `DO`, `ER` no fim. Campos vazios não são escritos. Nada é inventado.
5. **ORCID, afiliações e referências** não têm campo padrão no RIS. Nesta tarefa ficam de fora do RIS (estão no JSON da lista e no formato `json` da 05-03). Se o teste do Erick no VOSviewer pedir outra coisa, volta para a spec.

## Pronto quando

- [x] Teste: uma lista de exemplo vira um arquivo RIS válido, com um registro por artigo e todos os autores
- [x] Teste: uma lista inexistente devolve `list_not_found`; uma pasta sem permissão devolve `export_folder_not_writable`; um formato desconhecido devolve `invalid_input`
- [ ] Teste manual do Erick: uma busca real de tema pequeno, exportada em RIS, abre no VOSviewer 1.6.21 sem edição manual (primeiro critério de aceite do projeto); o resultado vai para a seção Resultado da entrega e para o T-008
- [ ] O RIS não tem campo padrão para ORCID nem referências; anotar na entrega o que foi para campos livres ou ficou de fora

## Vem de

FR-06, FR-12, UC-01, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-02 integrada. O teste no VOSviewer é feito pelo Erick.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/exporters/base.py`: interface base `Exporter` com atributos `format`, `extension` e método abstrato `render(list_data: dict) -> str` (**FR-06**, **D-002**); e função utilitária `save_export_file(export_dir, filename, content)` que cria a pasta de exportação se não existir, realiza gravação atômica em UTF-8 usando `atomic_write_replace`, e converte `(PermissionError, OSError)` em `RSLError("export_folder_not_writable", ...)` (**FR-06**, **D-007**).
  - `src/rslapp/exporters/ris.py`: exportador `RISExporter` com mapeamento estrito para o padrão RIS (`\r\n`, UTF-8, tags de 2 caracteres seguidas de 2 espaços, hífen e 1 espaço) (**FR-06**, **D-002**, **D-004**). Mapeia `TY` (`JOUR` para artigos, `CONF` para eventos/conferências/proceedings e `GEN` para o restante); `TI` (título limpo de quebras internas); `AU` (um por autor, na ordem exata e sem inversão de sobrenome); `PY` (ano numérico positivo); `JO` (periódico/venue); `AB` (resumo em linha contínua); `KW` (um por palavra-chave); `DO` (DOI); e `ER  - ` ao fim de cada registro. Campos vazios ou nulos são estritamente omitidos ("Campos vazios não são escritos. Nada é inventado").
  - `src/rslapp/exporters/__init__.py`: registro e resolução de exportadores com `get_exporter(format_name)` (atualmente suportando `"ris"`, levantando `RSLError("invalid_input", ...)` para outros formatos); e função de orquestração `run_export(store, list_id, export_format, export_dir)` que recupera a lista salva via `store.get_list` (convertendo `FileNotFoundError` e `ValueError` em `RSLError("list_not_found", ...)`), renderiza e grava `<list_id>.ris`, retornando `{"path": str(dest_path), "format": exporter.format, "count": count}` (**FR-06**, **FR-12**, **UC-01**, **D-002**).
  - `src/rslapp/server.py`: acréscimo da ferramenta `@mcp.tool() export_list(list_id: str, format: str) -> dict[str, Any]` que lê dinamicamente a configuração com `config.load()`, instancia `Store(cfg.data_dir, cfg.cache_days)`, executa `run_export` e converte `RSLError` em `ToolError(f"{e.code}: {e.message}")` (**FR-06**, **FR-12**, **UC-01**, **D-002**).
  - `tests/exporters/test_ris.py`: 34 testes cobrindo renderização linha a linha, preservação de ordem de autores sem inversão, caracteres acentuados e UTF-8, omissão de campos vazios, mapeamento de tipos RIS (`JOUR`, `CONF`, `GEN`), ausência de ORCID/afiliações/referências no arquivo RIS, múltiplos artigos, lista vazia, validação de tipo de entrada, gravação atômica e substituição em reexportação, tratamento de pasta sem permissão (`export_folder_not_writable`), execução de `run_export`, validação de `list_not_found` e rejeição de formatos não suportados com `invalid_input`.
  - `tests/test_server_export_list.py`: 12 testes de integração via `Client(mcp)` em memória cobrindo registro e descoberta da ferramenta `export_list`, exportação bem-sucedida de lista gravada no `Store`, integridade do arquivo gerado (`.ris`, UTF-8, `\r\n`), reexportação com substituição de arquivo, e retorno de erros conforme o contrato (`list_not_found:`, `invalid_input:` e `export_folder_not_writable:`).
- **O que foi assumido:**
  - Em conformidade com a decisão 5 da spec e a ausência de campo padrão na especificação clássica de RIS, ORCID, afiliações e identificadores de referências ficaram fora do arquivo RIS (permanecem salvos na íntegra no JSON da lista e serão exportados no formato JSON completo na tarefa 05-03).
  - Espaços em branco redundantes e quebras de linha internas em títulos, nomes de autor, periódicos, resumos e palavras-chave são normalizados para espaços simples (`" ".join(texto.split())`), prevenindo a quebra de estrutura e de tags no padrão de linhas do RIS.
  - O formato recebido em `export_list` é tratado sem distinção de maiúsculas/minúsculas e sem espaços laterais (`format_name.strip().lower()`).
- **O que não deu para verificar:**
  - O teste manual de abertura direta no software VOSviewer 1.6.21 (item reservado ao Erick conforme a spec e o plano do projeto, teste T-008).

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
2. **O que deve aparecer:**
   - `All checks passed!` no `ruff check .`
   - Todos os testes passando (`110 passed`) no `pytest` para Python 3.10 e Python 3.14.
3. **Onde olhar primeiro (pontos de risco, do mais difícil ao mais simples):**
   1. **Formatação RIS, codificação UTF-8 e quebras `\r\n` (`src/rslapp/exporters/ris.py` — `RISExporter.render`, FR-06, D-004):** conferir que cada linha termina estritamente em `\r\n`, que os registros iniciam em `TY  - ` e encerram em `ER  - \r\n`, que autores preservam a ordem original sem inversões artificiais, que acentuação internacional é gravada intacta em UTF-8 e que campos vazios não geram tags.
   2. **Gravação atômica, substituição e tratamento de permissão (`src/rslapp/exporters/base.py` — `save_export_file`, FR-06, D-007):** verificar que o arquivo de exportação é gravado em `<RSL_EXPORT_DIR>/<list_id>.ris` via `atomic_write_replace`, que reexportar a mesma lista substitui o arquivo sem erro de colisão, e que falhas de escrita/permissão de diretório levantam `RSLError("export_folder_not_writable", ...)`.
   3. **Tratamento de erros e contrato MCP (`src/rslapp/server.py` — `export_list`, D-002, FR-12):** verificar que listas inexistentes ou identificadores malformados voltam com erro iniciado por `list_not_found:`, formatos diferentes de `"ris"` voltam com `invalid_input:`, e falhas de pasta de exportação voltam com `export_folder_not_writable:`.

**Acompanhamentos da revisão (não bloqueiam):** faltam testes de quebra de linha no título e no resumo; o DOI não normaliza espaço interno; `get_exporter` aceita `"RIS"` e `" ris "`; `run_export` ficou em `exporters/` (a arquitetura o põe no miolo); uma lista vazia grava um `.ris` de 0 bytes.
