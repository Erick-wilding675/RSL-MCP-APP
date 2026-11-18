# Interface Desktop e Ferramentas MCP de Protocolo Metodológico

**Fase:** 18 · Versão 2.7 · **Situação:** pronta

## O que faz

Expõe o sistema de **Protocolo Metodológico Pré-Busca Versionado** (FR-30, D-041) no servidor MCP e na interface desktop do RSL.app:

1. **Ferramentas MCP (`src/rslapp/server.py`):**
   - Registra 4 novas ferramentas nos modos stdio e HTTP multiusuário:
     - `save_protocol`: cadastra ou atualiza um protocolo de pesquisa estruturado (com versionamento automático e arquivo de histórico).
     - `get_protocol`: recupera os dados estruturados de um protocolo (versão atual ou versão histórica pontual via `version`). Marcada com `readOnlyHint=True`.
     - `list_protocols`: lista todos os protocolos metodológicos ativos ordenados por data de atualização. Marcada com `readOnlyHint=True`.
     - `export_protocol_markdown`: formata e exporta o protocolo em Markdown rigoroso pronto para PROSPERO, OSF ou anexo de tese.
   - Total de ferramentas no servidor MCP: 24.
   - Atualização do contrato de interface (`docs/interface-contract.md`).

2. **Camada de Serviço Desktop (`src/rslapp/desktop/service.py`):**
   - Expõe `save_protocol`, `get_protocol`, `list_protocols`, `export_protocol_markdown` e `delete_protocol`.

3. **Interface Desktop (`src/rslapp/desktop/pages/protocol_view.py`):**
   - Identidade visual estritamente conservadora: **tema light acadêmico com detalhes verdes discretos** (`#1B4D3E`, fundo suave `#F8FAF9`, bordas nítidas `1px solid #E5E7EB`, cantos de 6px).
   - Item no drawer lateral de navegação: "Protocolos" (ícone `fact_check` / `assignment`).
   - Rota `/protocolos`:
     - Tabela/cartões com protocolos existentes: Título, Framework (badge discreto verde), Versão, Status e Ações (Editar, Ver Markdown, Excluir).
     - Botão destacado "Novo Protocolo".
   - Rota `/protocolo/{protocol_id}` e `/protocolo/novo`:
     - Seleção dinâmica de framework (`PICO`, `PCC`, `PICo`, `SPIDER`, `Narrativo`).
     - Formulário com campos estruturados do framework selecionado.
     - Critérios de elegibilidade (Inclusão e Exclusão) com interface ágil de adição e remoção.
     - Estratégia de busca planejada e seleção de bases pretendidas.
     - Rastro de autoria / auxílio de IA com alternador e campo de modelo.
     - Botão "Salvar Protocolo" (com incremento de versão e aviso amigável).
     - Botão "Copiar Markdown para PROSPERO/OSF".
     - Botão "Exportar Markdown (.md)".

## O que não faz

- Não submete diretamente credenciais privadas para o portal PROSPERO/OSF.
- Não remove versões históricas arquivadas na atualização de uma versão.

## Decisões desta spec

- **Design Acadêmico Sóbrio:** Segue estritamente a diretriz do usuário com tema light, verde discreto `#1B4D3E`, sem dark mode e sem gradientes vistosos.
- **Rastreabilidade de Versão Visível:** O pesquisador vê o histórico de versões e sabe exatamente qual versão do protocolo guiou cada busca.

## Para instituições (D-029)

Permite aos pesquisadores institucionais preparar seus projetos com facilidade em um ambiente gráfico unificado, exportando a documentação completa para aprovação de comitês de ética e registro em plataformas abertas.

## Pronto quando

- [x] 4 ferramentas de protocolo registradas em `src/rslapp/server.py` e validadas nos modos stdio e HTTP.
- [x] Contrato de interface (`docs/interface-contract.md`) atualizado para 24 ferramentas.
- [x] `DesktopService` atualizado com métodos de protocolo.
- [x] Rota `/protocolos` e `/protocolo/{protocol_id}` implementadas com design light e detalhes verdes.
- [x] Drawer lateral atualizado com o link "Protocolos".
- [x] Testes de servidor MCP (`tests/test_server_protocols.py`) passando.
- [x] Testes de suíte de ferramentas MCP (`tests/auth/test_oauth_flow_http.py`, `tests/test_server_http.py`) atualizados para 24 ferramentas e passando.
- [x] Testes de interface desktop (`tests_desktop/test_protocols_page.py`) passando.
- [x] Linter ruff 100% limpo sem avisos.
