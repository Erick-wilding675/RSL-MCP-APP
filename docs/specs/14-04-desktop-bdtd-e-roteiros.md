# Interface Desktop: BDTD e Roteiros Metodológicos

**Fase:** 14 · Versão 2.3 · **Situação:** pronta

## O que faz

Atualiza a interface gráfica desktop (NiceGUI) do RSL.app para incorporar as novidades da versão 2.3 voltadas à Academia Brasileira:
1. **BDTD na tela Buscar (`/`):**
   - Disponibiliza o checkbox da BDTD ("BDTD (Teses e Dissertações) - literatura cinzenta brasileira - IBICT") na grade de seleção de fontes abertas.
   - Como é uma fonte aberta pública, inicia configurada e pronta para busca sem requerer chave.
   - Suporta parâmetro `initial_query` (ou query string `/?q=...`) para pré-preencher a caixa de busca a partir de outras telas do app.
2. **Selos de Teses e Dissertações na Lista de Resultados (`/lista/{list_id}`):**
   - Na tabela de trabalhos, renderiza selos visuais distintivos quando o trabalho for tese (`thesis` -> `TESE`) ou dissertação (`dissertation` -> `DISSERTAÇÃO`), além de tooltips explicativos indicando defesa acadêmica brasileira.
3. **Nova Tela de Roteiros Metodológicos (`/roteiros`):**
   - Adiciona o item "Roteiros" (`menu_book`) à barra lateral de navegação (drawer), entre "Importar" e "Histórico".
   - Apresenta de forma estruturada e interativa os 4 tipos consolidados de revisão acadêmica:
     - **Revisão de Escopo (Scoping Review):** metodologia JBI e diretrizes PRISMA-ScR com framework PCC (População, Conceito, Contexto);
     - **Revisão Integrativa (Integrative Review):** metodologia de Whittemore & Knafl / Mendes, Silveira e Galvão em 6 fases de rigor metodológico;
     - **Revisão Sistemática (Systematic Review):** metodologia Cochrane e PRISMA 2020 com estrutura PICO (População, Intervenção, Comparação, Desfecho);
     - **Estudo Bibliométrico (Bibliometric Study):** análise de redes e mapeamento científico com VOSviewer, orientando sobre as Leis de Bradford, Lotka e Zipf.
   - Permite ao pesquisador preencher os parâmetros do seu estudo e:
     - Gerar o roteiro metodológico pronto com recomendações de busca e seleção;
     - Copiar o prompt com um clique para colar em sua IA (Claude, ChatGPT, Gemini);
     - Iniciar a busca diretamente no RSL.app com o tema preenchido (levando à tela Buscar com a string inicial).

## O que não faz

- Não realiza chamadas para IAs externas a partir do app (o app continua sem intermediar IA, mantendo soberania e privacidade do pesquisador).
- Não quebra as rotas e componentes já existentes do app desktop.

## Decisões desta spec

1. **Classes Semânticas do Tema RSL:** seguir rigorosamente o padrão visual do app (`rsl-surface-2`, `rsl-title`, `rsl-muted`, etc.), sem usar variantes `dark:` do Tailwind, garantindo compatibilidade perfeita tanto em modo claro quanto escuro.
2. **Navegação fluida entre Roteiros e Buscar:** a tela de roteiros oferece tanto a cópia do prompt pronto para a IA do usuário quanto um atalho para abrir o formulário de busca (`/?q=...`), preenchendo automaticamente a query com o tema do estudo.

## Para instituições (D-029)

A tela de Roteiros Metodológicos oferece aos programas de pós-graduação e bibliotecas universitárias um instrumento pedagógico padronizado para capacitar orientadores e discentes na formulação de buscas reprodutíveis e revisões alinhadas aos padrões internacionais (JBI, Cochrane, PRISMA) e nacionais (Mendes, Silveira e Galvão; BDTD/IBICT).

## Pronto quando

- [x] `src/rslapp/desktop/pages/search.py` inclui BDTD nas fontes disponíveis com rótulo e descrição amigáveis.
- [x] `src/rslapp/desktop/pages/search.py` e `src/rslapp/desktop/app.py` suportam preenchimento da busca via parâmetro `initial_query`.
- [x] `src/rslapp/desktop/pages/list_view.py` exibe selos para `thesis` e `dissertation`.
- [x] `src/rslapp/desktop/pages/__init__.py` inclui "Roteiros" em `NAV_ITEMS`.
- [x] Nova página `src/rslapp/desktop/pages/guidelines_view.py` criada e registrada em `src/rslapp/desktop/app.py` na rota `/roteiros`.
- [x] Testes da suíte desktop (`tests_desktop/`) cobrem BDTD, rota `/roteiros`, selos e navegação, passando 100%.
- [x] Ruff check limpo.
