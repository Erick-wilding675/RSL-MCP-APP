# Interface Desktop: Telas de Triagem e Fluxograma PRISMA

**Fase:** 15 · Versão 2.4 · **Situação:** pronta

## O que faz

Integra ao aplicativo Desktop (NiceGUI) a experiência completa de triagem ágil e visualização do fluxograma PRISMA 2020 (FR-25, FR-26, FR-27, D-024, D-025, D-036, D-037, D-038):

1. **Acesso a partir da Tela Lista (`src/rslapp/desktop/pages/list_view.py`):**
   - No cartão de ações da lista, adiciona botões destacados:
     - Botão "Triagem" (com ícone `filter_alt` ou `fact_check` e contagem/progresso), direcionando para `/triagem/{list_id}`;
     - Botão "PRISMA 2020" (com ícone `account_tree` ou `schema`), direcionando para `/prisma/{list_id}`.
   - Na tabela de trabalhos da lista, exibe uma coluna ou selo de status de triagem para cada registro (`INCLUÍDO` verde, `EXCLUÍDO` vermelho, `DÚVIDA` âmbar ou `PENDENTE` cinza).

2. **Tela de Triagem Rápida (`src/rslapp/desktop/pages/screening_view.py` em `/triagem/{list_id}`):**
   - Modo de triagem focado trabalho a trabalho com navegação anterior/próximo e atalhos de teclado:
     - `I` para Incluir (`included`);
     - `E` para Excluir (`excluded`) abrindo seletor rápido de motivos;
     - `M` para Dúvida/Talvez (`maybe`);
     - Setas Esquerda/Direita para navegar entre artigos.
   - Exibição de título, ano, autores, periódico, DOI e o Resumo (Abstract) formatado com tipografia confortável para leitura.
   - Identificação do estágio atual (`Fase 1: Título e Resumo` vs. `Fase 2: Texto Completo`).
   - Barra de progresso visual com percentual e contadores de incluídos, excluídos e pendentes.
   - Gravação atômica instantânea e feedback não invasivo.

3. **Tela de Fluxograma PRISMA 2020 e Declaração de IA (`src/rslapp/desktop/pages/prisma_view.py` em `/prisma/{list_id}`):**
   - Visualização interativa do fluxograma vetorial PRISMA 2020 gerado dinamicamente com os números reais da lista e triagem.
   - Botão para Download direto do arquivo SVG diagramado para inclusão em relatórios ou artigos.
   - Aba/seção com o Checklist PRISMA-S preenchido.
   - Aba/seção com o gerador da Declaração Metodológica de IA (COPE/ICMJE/SciELO) com botões para alternar idioma (Português / Inglês) e botão de "Copiar Texto".

4. **Para instituições (D-029):**
   - Os pesquisadores da instituição contam com ambiente local e privado para conduzir a triagem de artigos sem expor dados não publicados para terceiros, cumprindo as exigências de sigilo e ética.

## O que não faz

- Não utiliza classes utilitárias `dark:` do Tailwind (segue o padrão de classes semânticas do app desktop: `rsl-surface-2`, `rsl-title`, `rsl-muted`).
- Não depende de bibliotecas de renderização gráfica em C no cliente (o SVG é injetado diretamente via `ui.html(svg_content)`).

## Pronto quando

- [x] Métodos de fachada em `src/rslapp/desktop/service.py` para obtenção dos dados do fluxograma, SVG e declaração de IA.
- [x] Atualização de `src/rslapp/desktop/pages/list_view.py` com botões e badges de triagem.
- [x] Implementação de `src/rslapp/desktop/pages/screening_view.py` com navegação por teclado e gravação de decisões.
- [x] Implementação de `src/rslapp/desktop/pages/prisma_view.py` com diagrama SVG, download e cópia da declaração.
- [x] Registro das rotas em `src/rslapp/desktop/app.py`.
- [x] Testes do desktop em `tests_desktop/test_screening_page.py`.
- [x] Ruff check limpo.
