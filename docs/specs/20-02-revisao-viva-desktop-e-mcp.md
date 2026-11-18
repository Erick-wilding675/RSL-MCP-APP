# Ferramentas MCP e Interface Desktop para Revisão Viva (v2.9)

**Fase:** 20 · Versão 2.9 · **Situação:** pronta

## O que faz

1. **Servidor MCP (`src/rslapp/server.py`):**
   - Ferramenta MCP `compare_search_versions(base_list_id: str, new_list_id: str)`:
     - Compara duas listas e retorna contagens de novos artigos, mantidos e relatório textual formatado.
   - Ferramenta MCP `update_search_differential(list_id: str)`:
     - Executa novamente a mesma estratégia de busca gravada no log da lista base, gera a nova lista atualizada e devolve o resumo diferencial completo.
   - Totalizando 27 ferramentas especializadas no servidor MCP stdio e HTTP multiusuário.

2. **Interface Desktop (`src/rslapp/desktop/`):**
   - Método `compare_lists` e `update_search_live` no serviço `DesktopService`.
   - Botão "Revisão Viva (Atualizar Busca)" na tela de Detalhes da Lista (`/lista/{list_id}`).
   - Modal / Diálogo visual comparativo mostrando:
     - Total anterior de artigos;
     - Novos artigos indexados desde a última busca;
     - Opção de visualizar e filtrar a nova lista com badge `NOVO NA BUSCA`.
   - Botão de atualização rápida também na tabela da tela Histórico (`/historico`).

## O que não faz

- Não altera as triagens ou fichamentos dos artigos já existentes.
- Não força o usuário a atualizar se desejar manter a busca congelada.

## Decisões desta spec

- **Experiência Visual Sóbria com Detalhes Verdes (D-031):** O badge `NOVO NA BUSCA` utiliza fundo sutil `#F0FDF4`, borda `#BBF7D0` e texto `#166534`, perfeitamente alinhado com a identidade acadêmica do app.

## Para instituições (D-029)

Facilita o acompanhamento institucional de revisões sistemáticas em andamento nos grupos de pesquisa da universidade.

## Pronto quando

- [x] Ferramentas MCP `compare_search_versions` e `update_search_differential` registradas no stdio e HTTP.
- [x] Interface desktop atualizada com botão e diálogo comparativo de Revisão Viva.
- [x] Testes do servidor e testes do desktop passando.
- [x] Linter ruff limpo.
