# Publicação da 2.3.0 e teste real

**Fase:** 14 · Versão 2.3 · Academia Brasileira · **Situação:** pronta

## O que faz

Prepara e valida a publicação da versão 2.3.0 do `rslapp` no PyPI e GitHub releases com executáveis para Windows e Linux, imagem Docker e servidor MCP atualizado.

- **Novidades da versão 2.3.0 ("Academia Brasileira"):**
  1. **Conector BDTD (Biblioteca Digital Brasileira de Teses e Dissertações - IBICT) (D-035, FR-01, FR-07):**
     - Busca em mais de 700.000 teses de doutorado e dissertações de mestrado brasileiras como literatura cinzenta fundamental para revisões sistemáticas e integrativas, prevenindo viés de publicação.
     - Fonte aberta pública nativa sem exigência de chaves de API.
     - Extração de autores, orientadores, instituição de defesa, datas, resumo e links/DOIs.
     - Identificador `BDTD ID` na coluna do CSV (27 colunas).
     - Selos visuais na interface desktop: `TESE` (teal) e `DISSERTAÇÃO` (indigo).
  2. **Roteiros Metodológicos e Prompts MCP de Revisão (D-035, FR-10):**
     - Quatro novos geradores de planejamento científico consolidados na academia nacional e internacional:
       - `plan_scoping_review`: Metodologia JBI e checklist PRISMA-ScR pelo framework PCC (População, Conceito e Contexto);
       - `plan_integrative_review`: Metodologia em 6 fases de Whittemore & Knafl e Mendes, Silveira e Galvão (2008);
       - `plan_systematic_review`: Padrão Cochrane e PRISMA 2020 com estratégia PICO (População, Intervenção, Comparação, Desfecho);
       - `plan_bibliometric_study`: Protocolo para VOSviewer com as Leis clássicas de Bradford (dispersão e núcleos de periódicos), Lotka (produtividade de autores) e Zipf (frequência de vocabulário).
  3. **Nova Tela de Roteiros no App Desktop (`/roteiros`) (D-031, D-035, FR-10, FR-16):**
     - Item "Roteiros" (`menu_book`) na navegação lateral do app.
     - Interface interativa com abas para cada tipo de estudo, formulário de parâmetros em tempo real, cópia de prompt com um clique e atalho direto para iniciar a busca no RSL.app (`/?q=...`).

- **Publicação:**
  1. Versão bumped para `2.3.0` em `pyproject.toml` e `src/rslapp/__init__.py`.
  2. Todos os gates de qualidade executados e aprovados:
     - Ruff check limpo;
     - Suíte principal: 761 testes unitários e de integração passando;
     - Suíte desktop: 60 testes de interface NiceGUI passando;
     - Pacotes wheel e sdist construídos via `uv build --no-sources`.
  3. Mesclar `integracao-2.3` na `main`.

- **Roteiro de Teste Real do Erick:**
  1. **Executar o app desktop:**
     `uv run rslapp-desktop`
  2. **Testar a busca na BDTD:**
     - Na tela **Buscar** (`/`), verificar a presença do card "BDTD (Teses e Dissertações) - literatura cinzenta brasileira - IBICT".
     - Realizar uma busca por um tema brasileiro (ex.: `"inteligência artificial" AND "educação"` ou `"revisão sistemática"`), mantendo a BDTD marcada.
     - Na tela da **Lista**, verificar a presença dos selos `TESE` e `DISSERTAÇÃO` nos trabalhos recuperados da BDTD.
  3. **Testar a nova tela de Roteiros Metodológicos:**
     - Clicar no item **Roteiros** (`menu_book`) no menu lateral.
     - Navegar pelas 4 abas: *Revisão de Escopo (PCC)*, *Revisão Integrativa (6 Fases)*, *Revisão Sistemática (PICO)* e *Estudo Bibliométrico (VOSviewer)*.
     - Preencher os campos de um tema (ex.: População, Conceito, Contexto em Escopo) e verificar a atualização em tempo real do roteiro.
     - Clicar em "Copiar Roteiro" e conferir a notificação de confirmação e a colagem na sua IA (Claude, ChatGPT ou Gemini).
     - Clicar em "Buscar no RSL.app" e conferir se o app abre a tela de busca com o tema pré-preenchido.
  4. **Testar os Prompts no Servidor MCP:**
     - Abrir um cliente MCP (Claude Desktop, Cursor ou Inspector) e listar os prompts. Conferir se os 5 prompts aparecem: `plan_search`, `plan_scoping_review`, `plan_integrative_review`, `plan_systematic_review`, `plan_bibliometric_study`.

## Pronto quando

- [x] Versão `2.3.0` atualizada no `pyproject.toml` e em `src/rslapp/__init__.py`.
- [x] Documentos atualizados (`docs/hospedagem.md`, `docs/interface-contract.md`, `docs/plan.md`, `.blueprint/state.md`).
- [x] Todos os gates passam (Ruff limpo, 761 testes core, 60 testes desktop).
- [x] Pacote construído com `uv build --no-sources`.
- [x] Branch `integracao-2.3` mesclada na `main`.
- [x] Publicação no PyPI e release GitHub `v2.3.0` realizada após confirmação do Erick.

## Vem de

D-030, D-035, FR-01, FR-07, FR-10, FR-16.
