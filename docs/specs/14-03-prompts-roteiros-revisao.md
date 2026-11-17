# Roteiros e Prompts para Tipos de Revisão Acadêmica

**Fase:** 14 · Versão 2.3 · **Situação:** pronta

## O que faz

Adiciona prompts especializados ao servidor MCP (`plan_scoping_review`, `plan_integrative_review`, `plan_systematic_review`, `plan_bibliometric_study`), conectando a IA do pesquisador às metodologias científicas rigorosas consolidadas e exigidas na academia brasileira:
1. **Revisão de Escopo (JBI / PRISMA-ScR):** estruturação pelo mnemônico PCC (População, Conceito, Contexto), critérios de elegibilidade para mapear a extensão da literatura e inclusão indispensável de literatura cinzenta (BDTD).
2. **Revisão Integrativa (Whittemore & Knafl / Mendes, Silveira e Galvão):** protocolo em 6 fases para síntese de estudos empíricos e teóricos, modelo predominante nos programas de pós-graduação em saúde e enfermagem no Brasil.
3. **Revisão Sistemática (PRISMA 2020 / Cochrane):** pergunta PICO (População, Intervenção, Comparação, Desfechos), plano de busca em bases abertas e literatura cinzenta, dupla triagem e prevenção de viés de publicação.
4. **Estudo Bibliométrico (VOSviewer / Leis Bibliométricas):** delineamento de mapa de redes (coautoria, acoplamento bibliográfico, cocitação, coocorrência de termos) e leis clássicas (Bradford, Lotka, Zipf).

## O que não faz

- Não altera as ferramentas de busca ou exportação existentes.
- Não substitui o prompt original `plan_search` (que continua disponível para buscas gerais).

## Decisões desta spec

1. **Parâmetros estruturados nos prompts MCP:** cada prompt recebe parâmetros semânticos opcionais (ex: `population`, `concept`, `context` em escopo; `intervention`, `comparison`, `outcome` em sistemática) com valores padrão vazios, permitindo tanto chamadas diretas com preenchimento granular quanto perguntas abertas em linguagem natural.
2. **Tratamento de texto como dado:** todo texto vindo do pesquisador é encapsulado dentro de tags semânticas (`<pedido_pesquisador>`) com aviso de não execução, mantendo conformidade com as diretrizes de segurança contra injeção de prompt (NFR-03, FR-10).
3. **Disponibilidade uniforme:** os 4 prompts são registrados tanto no servidor stdio (`server.py`) quanto no servidor HTTP (`_build_http_mcp_server`).

## Pronto quando

- [x] Módulo `src/rslapp/prompts.py` contém os geradores:
  - `render_plan_scoping_review`
  - `render_plan_integrative_review`
  - `render_plan_systematic_review`
  - `render_plan_bibliometric_study`
- [x] Prompts `@mcp.prompt()` registrados em `src/rslapp/server.py` e em `_build_http_mcp_server`.
- [x] Testes unitários em `tests/test_prompts_review_types.py` validando estrutura, metodologias citadas, parâmetros opcionais e proteção contra injeção.
- [x] Testes de integração em `tests/test_server_review_prompts.py` garantindo que os 4 prompts são listados e executados via cliente MCP stdio e HTTP.
- [x] Todos os gates passam (Ruff limpo, testes em Python 3.10 e 3.14).
