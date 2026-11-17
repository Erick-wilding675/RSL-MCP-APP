# Importar exportações de fora: RIS, BibTeX, Scopus e Web of Science (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** em andamento

## O que faz

Permite que o pesquisador importe listas bibliográficas e resultados de busca exportados de outras bases e gerenciadores de referência (como Scopus, Web of Science, Portal de Periódicos CAPES, Zotero, Mendeley e Google Scholar), incorporando-os como uma nova lista no RSL.app (ideia 7, FR-23, D-033).

### 1. Parsers de formatos no núcleo (`rslapp.core.importers`)

- **RIS (`.ris`):**
  - Compatível com os padrões de RIS do Scopus, Web of Science, PubMed, Zotero, Mendeley e EndNote.
  - Reconhece tags essenciais: `TY` (tipo), `TI`/`T1` (título), `AU`/`A1` (autores), `PY`/`Y1` (ano), `DO` (DOI), `AB`/`N2` (resumo), `KW` (palavras-chave), `JF`/`JO`/`T2` (periódico/evento), `SN` (ISSN/ISBN), `UR` (URL), `ER` (fim do registro).
- **BibTeX (`.bib`):**
  - Reconhece blocos padrão `@article`, `@book`, `@inproceedings`, `@misc`, `@phdthesis`, etc.
  - Extrai os campos `title`, `author`, `year`, `doi`, `journal`, `booktitle`, `abstract`, `keywords`, `note`.
- **Scopus CSV:**
  - Compatível com o formato CSV de exportação padrão do Scopus.
  - Mapeia as colunas: `Authors`, `Author full names`, `Title`, `Year`, `Source title`, `DOI`, `Abstract`, `Author Keywords`, `Index Keywords`, `References`, `Cited by`, `Affiliations`, `Document Type`, `EID`.
- **Web of Science Tab-delimited e Tagged (`.txt`, `.tsv`):**
  - Compatível com exportações "Tab-delimited" e "Plain text" do Web of Science.
  - Mapeia as tags WoS: `PT` (tipo de publicação), `AU` (autores), `TI` (título), `SO` (fonte/revista), `DT` (tipo de documento), `DE`/`ID` (palavras-chave do autor e keywords plus), `AB` (resumo), `C1` (afiliações), `CR` (referências citadas), `TC` (vezes citado), `PY` (ano), `DI` (DOI), `UT` (identificador único WOS).

### 2. Detecção automática de formato (`auto_detect_format`)

- Identifica automaticamente o formato do conteúdo com base nas assinaturas do texto:
  - `ris`: presença de linhas iniciadas com `TY  - ` e `ER  - `.
  - `bibtex`: presença de blocos `@\w+\s*\{`.
  - `scopus_csv`: arquivo CSV com cabeçalhos reconhecíveis do Scopus (`Authors` e `Source title` ou `DOI`).
  - `wos`: arquivo delimitado por tabulação com cabeçalho WoS ou texto com tags `PT ` e `UT WOS:`.

### 3. Integração e armazenamento no núcleo (`rslapp.core.importers`)

- Converte os dados estruturados em instâncias válidas de `Work`.
- Normaliza títulos e DOIs.
- Salva os artigos como uma nova lista no `Store` (`store.save_list(list_id, list_data)`).
- Registra metadados da importação: `source: "import"`, `import_format`, `filename`, `total_imported`.
- A lista criada ganha ID único no formato `list_imp_<timestamp>_<hash>` e fica imediatamente disponível para navegação, verificação contra alucinação, detecção de retratações e exportação para o VOSviewer.

### 4. Ferramenta MCP (`src/rslapp/server.py`)

- Adiciona a ferramenta `@mcp.tool()`:
  - `import_works(content: str, format: str = "auto", list_name: str = "") -> dict[str, Any]`
  - Registrada no modo stdio e no servidor HTTP.
  - Retorna o resumo da importação (`list_id`, `total_imported`, `detected_format`, `sample_titles`).

### 5. Interface Desktop (`src/rslapp/desktop/pages/import_view.py`)

- Item "Importar" (`file_upload`, `/importar`) adicionado à casca lateral `NAV_ITEMS`.
- Na tela `/importar`:
  - Upload de arquivos (`.ris`, `.bib`, `.csv`, `.tsv`, `.txt`).
  - Área alternativa de colar texto diretamente.
  - Opção de seleção manual de formato ou detecção automática.
  - Campo opcional de nome/descrição da lista.
  - Botão "Processar Importação" com indicador visual.
  - Cartões métricos de confirmação (Artigos importados, com DOI, autores).
  - Botão de acesso rápido para abrir a lista recém-importada em `/lista/{list_id}`.

## O que não faz

- Não realiza web scraping de telas autenticadas do Scopus ou Web of Science.
- Não baixa PDFs integrais automaticamente.

## Para instituições

Pesquisadores que possuem acesso ao Portal de Periódicos CAPES, Scopus ou Web of Science via CAFe (login institucional da universidade) frequentemente realizam buscas manuais e baixam seus resultados em RIS, BibTeX ou CSV. Com a importação do RSL.app, a universidade viabiliza o uso pleno de ferramentas avançadas (VOSviewer, checagem de retratações e auditoria contra alucinações de IA) sem depender de contratação de APIs institucionais de alto custo.

## Pronto quando

- [ ] Módulo `src/rslapp/core/importers/` implementado com suporte a RIS, BibTeX, Scopus CSV e Web of Science TSV/Tagged.
- [ ] Função `auto_detect_format` identifica confiavelmente cada um dos formatos suportados.
- [ ] Função `import_records` gera instâncias válidas de `Work` e grava a lista no `Store`.
- [ ] Ferramenta MCP `import_works` exposta no stdio e HTTP com anotações adequadas.
- [ ] Tela `/importar` implementada no desktop com suporte a upload de arquivo e colagem de texto.
- [ ] Testes de unidade e integração cobrindo cada formato com exemplos reais/sintéticos fiéis.
- [ ] Testes da interface desktop validando a navegação e o fluxo de importação.
- [ ] Todos os gates passam (testes 3.10 e 3.14, desktop, ruff limpo).

## Vem de

Ideia 7, FR-23, D-033.

## Antes de começar

- Criar a branch de tarefa `fase13/13-06-importar-exportacoes` a partir de `integracao-2.2`.
- Entregar em fatias ordenadas: (1) Parsers de formatos e modelo no núcleo; (2) Ferramenta MCP e persistência no Store; (3) Interface Desktop.
- Seguir as regras de acessibilidade e tema do projeto (sem variantes `dark:` de Tailwind).
