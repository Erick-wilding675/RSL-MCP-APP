# Fichamento Científico Estruturado com Marcação de Autoria e Exportação Markdown

**Fase:** 17 · Versão 2.6 · **Situação:** pronta

## O que faz

Implementa no núcleo do RSL.app, no armazenamento, no servidor MCP e na interface desktop o sistema de **Fichamento Científico Estruturado com Marcação de Autoria** (FR-29, D-040, ideia 2.1):

1. **Modelo de Ficha Científica (`src/rslapp/core/notes.py`):**
   - Estrutura `WorkNote`:
     - `list_id: str` e `work_id: str`: chaves identificadoras.
     - `title: str | None`: título do artigo.
     - `authors: list[str]`: autores.
     - `year: int | None`: ano.
     - `doi: str | None`: DOI.
     - `abnt_reference: str | None`: citação pronta no padrão ABNT NBR 6023:2018.
     - `objective: str | None`: objetivo da pesquisa.
     - `methodology: str | None`: desenho metodológico e procedimentos.
     - `sample: str | None`: amostra, participantes e contexto empírico.
     - `results: str | None`: principais achados e resultados.
     - `limitations: str | None`: limitações declaradas pelos autores.
     - `personal_keywords: list[str]`: palavras-chave próprias atribuídas pelo pesquisador.
     - `synthesis: str | None`: síntese crítica, comentários e reflexões do pesquisador.
     - `direct_quotes: list[WorkNoteQuote]`: citações diretas textuais com indicação de página (`page`) e comentário (`comment`).
     - `source: Literal["human_created", "ai_suggested", "human_reviewed"]`: rastreabilidade de autoria (uma sugestão de IA fica explicitamente marcada como tal até que o pesquisador a valide).
     - `ai_model: str | None`: modelo de IA responsável pela sugestão (ex.: "Claude 3.5 Sonnet", "Gemini 1.5 Pro").
     - `created_at: str` e `updated_at: str`: timestamps ISO 8601.
     - `reviewed_by: str | None`: nome ou identificador do revisor humano.

2. **Armazenamento no Store (`src/rslapp/store/`):**
   - Diretório estruturado: `notes/{list_id}/{work_id}.json`.
   - Operações atômicas com substituição segura:
     - `save_work_note(note: WorkNote) -> None`
     - `get_work_note(list_id: str, work_id: str) -> WorkNote | None`
     - `list_work_notes(list_id: str) -> list[WorkNote]`
     - `delete_work_note(list_id: str, work_id: str) -> bool`

3. **Exportador Markdown para Obsidian e Logseq (`export_notes_markdown`):**
   - Gera notas individuais ou arquivo compilado com frontmatter YAML (`title`, `authors`, `year`, `doi`, `source`, `tags`), seções estruturadas com callouts e citações em bloco (`> ...`), ideal para ferramentas de gestão de conhecimento pessoal (PKM).
   - Integração automática com o Pacote de Reprodutibilidade (`reproducibility_{list_id}.zip`), incluindo `notes.md` e `notes.json` quando houver fichas salvas.

4. **Ferramentas MCP:**
   - `save_work_note`: registra ou atualiza uma ficha analítica com suporte a autoria (`ai_suggested` vs `human_reviewed`).
   - `get_work_note`: recupera a ficha científica de um artigo específico.
   - `list_work_notes`: lista todas as fichas associadas a uma lista de busca.
   - `export_notes_markdown`: exporta as fichas em formato Markdown.

5. **Interface Desktop (`rslapp.desktop`):**
   - Na tela Lista (`/lista/{list_id}`):
     - Indicador visual (badge) na tabela sinalizando artigos fichados ("Ficha IA" ou "Ficha OK").
     - Botão de ação "Ficha" para abrir a visualização e edição.
     - Botão no cabeçalho "Exportar Fichas (.md)".
   - Tela/modal de fichamento:
     - Formulário elegante com os campos acadêmicos.
     - Badge destacado indicando autoria ("Sugerido por IA" vs "Revisado por Humano").
     - Botão "Marcar como Revisado por Humano" em um clique.
     - Citação no padrão ABNT pré-preenchida.

## O que não faz

- Não faz chamadas de IA diretamente no servidor MCP (o preenchimento assistido por IA é executado pelo cliente MCP do pesquisador ou pelo usuário).
- Não altera os arquivos de lista imutáveis originais (`lists/{list_id}.json`).

## Decisões desta spec

1. **Rastreabilidade de Autoria Obrigatória (D-040):** campos preenchidos pela IA nunca devem se passar por trabalho humano não conferido. A categorização `ai_suggested` vs `human_reviewed` protege a integridade acadêmica do pesquisador e atende aos princípios de ética científica.
2. **Compatibilidade com Obsidian e PKM:** o formato Markdown gerado adota o padrão de metadados YAML amplamente utilizado por pesquisadores que usam Obsidian, Logseq e Zettlr.

## Para instituições (D-029)

Programas de pós-graduação e laboratórios de pesquisa ganham um padrão institucional de fichamento que pode ser compartilhado entre orientadores e orientandos, com clareza cristalina sobre o papel da IA no processo de leitura e extração.

## Pronto quando

- [x] Modelos `WorkNote` e `WorkNoteQuote` implementados e validados no núcleo.
- [x] Métodos de persistência no `Store` implementados com gravação atômica.
- [x] Exportador de Markdown para Obsidian e relatório compilado implementados.
- [x] Módulo de reprodutibilidade atualizado para incluir notas no `.zip`.
- [x] Ferramentas MCP `save_work_note`, `get_work_note`, `list_work_notes` e `export_notes_markdown` expostas no stdio e HTTP.
- [x] Interface desktop atualizada com badges, tela/diálogo de fichamento e botão de exportação.
- [x] Testes unitários do núcleo, testes do servidor MCP e testes desktop passando 100%.
- [x] Linter ruff limpo sem avisos.
