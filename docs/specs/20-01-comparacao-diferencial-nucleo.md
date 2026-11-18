# Comparação Diferencial de Buscas no Núcleo e Armazenamento (Revisão Viva)

**Fase:** 20 · Versão 2.9 · **Situação:** pronta

## O que faz

Implementa no núcleo do RSL.app o motor de **Revisão Sistemática Viva e Comparação Diferencial de Buscas** (FR-32, D-043, ideia 1.6):

1. **Módulo Diferencial (`src/rslapp/core/differential.py`):**
   - Função `compute_search_difference(old_works: list[Work], new_works: list[Work]) -> DifferentialResult`:
     - Identifica com precisão:
       - `retained_works`: trabalhos que já existiam na busca anterior e permanecem na busca atualizada (preservando todas as decisões prévias de triagem e notas).
       - `added_works`: artigos inéditos encontrados e indexados pelas bases após a busca original.
       - `missing_works`: artigos que não constam na nova busca (se houver, por exemplo, alteração de filtros).
     - Estatísticas: contagem anterior, contagem adicionada, contagem mantida, total atual.
   - Gerador de Relatório Metodológico (`format_differential_markdown`):
     - Gera relatório em Markdown com resumo cronológico da atualização (data anterior vs. data atual), contagens numéricas, lista detalhada de novas publicações com autores, periódico, ano e DOI/URL.

2. **Armazenamento no Store (`src/rslapp/store/__init__.py`):**
   - Método `save_differential_update(original_list_id: str, new_list_id: str, diff_data: dict) -> Path`:
     - Grava atomicamente em `differential/{original_list_id}_{timestamp}.json`.
   - Método `list_differential_updates(list_id: str) -> list[dict]`.

3. **Integração no Pacote de Reprodutibilidade (`src/rslapp/core/reproducibility.py`):**
   - Se a lista tiver atualizações diferenciais, inclui `differential_updates.json` e `differential_report.md` no `.zip` auditados no manifesto `checksums.sha256`.

## O que não faz

- Não apaga nem sobrescreve a lista original (princípio da imutabilidade e rastreabilidade científica D-009).
- Não altera decisões humanas de triagem já realizadas em artigos prévios.

## Decisões desta spec

- **Imutabilidade e Rastreabilidade (D-009, D-043):** Toda atualização gera uma nova rodada de busca com link formal para a lista base, permitindo auditar o crescimento do corpus da revisão ao longo do tempo.

## Para instituições (D-029)

Permite que pesquisadores mantenham suas revisões permanentemente atualizadas entre a qualificação e a defesa de mestrado/doutorado, ou durante o processo de submissão a periódicos (que exigem buscas atualizadas nos últimos 6 meses).

## Pronto quando

- [x] Módulo `src/rslapp/core/differential.py` implementado com cálculo diferencial e gerador de relatório Markdown.
- [x] Métodos de armazenamento implementados no `Store`.
- [x] Testes unitários em `tests/core/test_differential.py` passando 100%.
- [x] Linter ruff limpo sem avisos.
