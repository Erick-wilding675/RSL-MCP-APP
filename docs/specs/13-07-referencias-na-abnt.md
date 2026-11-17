# Referências na ABNT NBR 6023:2018 (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** em andamento

## O que faz

Gera e exporta referências bibliográficas formatadas segundo a norma técnica brasileira **ABNT NBR 6023:2018** (Informação e documentação — Referências — Elaboração) para listas de revisão sistemática e trabalhos acadêmicos (ideia 4.3, FR-24, D-034).

### 1. Formatador no núcleo (`rslapp.core.abnt`)

- **Função de formatação individual:**
  `format_abnt_reference(work: Work | dict[str, Any], *, markdown: bool = False, access_date: str | None = None) -> str`
- **Regras da NBR 6023:2018:**
  - **Autores:**
    - Converte nomes para `SOBRENOME, Prenomes/Iniciais` em caixa alta no sobrenome principal (`SILVA, Carlos; SANTOS, Maria`).
    - Para mais de 3 autores: preserva todos os autores separados por ponto-e-vírgula (recomendação oficial da edição 2018 para dar crédito a toda a equipe) ou oferece suporte ao formato com `et al.`.
  - **Título e Subtítulo:**
    - O título principal e subtítulo separados por dois pontos (`Título: subtítulo`).
    - Em artigos de periódicos, o destaque (negrito no Markdown ou caixa/destaque em texto) recai sobre o **Título do Periódico**, não sobre o título do artigo.
    - Em livros, o destaque recai sobre o **Título do Livro**.
  - **Ano e Paginação:**
    - Formata o ano de publicação (`2024.`) e, quando presentes, volume, número e páginas (`v. 12, n. 3, p. 45-67, 2024.`).
  - **DOI e Endereço Eletrônico:**
    - Inclui `Disponível em: https://doi.org/<doi>.` quando houver DOI.
  - **Retratação (D-032):**
    - Se `work.is_retracted` for verdadeiro, acrescenta nota de rodapé textual ao final da referência: `[Nota: Artigo retratado ou com expressão de preocupação oficial].`

### 2. Exportador ABNT (`src/rslapp/exporters/abnt.py`)

- Nova classe `ABNTExporter(Exporter)` com formato `abnt` e extensão `txt`:
  - Registrada em `_EXPORTERS` no módulo `rslapp.exporters`.
  - Produz uma lista alfabética (ordenada por sobrenome do primeiro autor e ano) de todas as referências da lista com separação por linha em branco, pronta para inserção direta na seção "Referências" de artigos, dissertações e teses.
- Suportada em `export_list(list_id=..., format="abnt")` via stdio e modo HTTP (com download de link assinado).

### 3. Interface Desktop (`src/rslapp/desktop/pages/list_view.py`)

- **Cartão Exportar:**
  - Adiciona o botão `ABNT` com ícone `format_quote` para exportação direta em um clique.
- **Ficha / Tabela do artigo:**
  - Permite copiar a citação formatada na ABNT diretamente da interface com botão de cópia (`copy_block` ou botão dedicado).

## O que não faz

- Não substitui gerenciadores completos de estilo com centenas de variações de periódicos específicos (Vancouver, APA, Chicago permanecem via BibTeX e RIS nos gerenciadores Zotero/Mendeley).
- Não inventa informações ausentes (se uma fonte não fornecer periódico ou ano, formata com os dados disponíveis de forma graciosa).

## Para instituições

A grande maioria dos programas de pós-graduação, comitês de ética, periódicos científicos nacionais e bancas de mestrado e doutorado no Brasil exige estritamente a norma ABNT NBR 6023. A disponibilização nativa da lista de referências na ABNT elimina o trabalho manual e enfadonho de conversão e atende diretamente à realidade dos pesquisadores brasileiros.

## Pronto quando

- [ ] Módulo `src/rslapp/core/abnt.py` implementado com formatação de obras segundo a ABNT NBR 6023:2018.
- [ ] Exportador `ABNTExporter` implementado em `src/rslapp/exporters/abnt.py` e registrado em `_EXPORTERS`.
- [ ] Ferramenta MCP `export_list(format="abnt")` testada e validada no stdio e HTTP.
- [ ] Botão de exportação "ABNT" adicionado ao cartão Exportar da tela Lista no app desktop.
- [ ] Testes de unidade e integração cobrindo artigos normais, artigos com mais de 3 autores, artigos retratados e listas completas.
- [ ] Todos os gates passam (testes 3.10 e 3.14, testes do desktop, linter Ruff limpo).

## Vem de

Ideia 4.3, FR-24, D-034.

## Antes de começar

- Criar a branch de tarefa `fase13/13-07-referencias-abnt` a partir de `integracao-2.2`.
- Entregar em fatias ordenadas: (1) Formatador no núcleo e exportador `abnt`; (2) Integração no Desktop; (3) Testes e documentação.
- Seguir as regras do projeto.
