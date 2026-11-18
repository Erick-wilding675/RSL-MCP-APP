# Ferramenta MCP e Interface Desktop para Redes Bibliométricas Nativas

**Fase:** 19 · Versão 2.8 · **Situação:** pronta

## O que faz

Expõe a geração de **Redes Bibliométricas Nativas** (VOSviewer e Gephi) no servidor MCP e na interface desktop do RSL.app (FR-31, D-042):

1. **Ferramenta MCP (`src/rslapp/server.py`):**
   - Adiciona a ferramenta `export_network` aos transportes stdio e HTTP:
     - Parâmetros: `list_id` (obrigatório), `network_type` (`coauthorship`, `source_coupling`, `keyword_cooccurrence`, padrão `coauthorship`), `format` (`vosviewer`, `gephi`, `json`, padrão `vosviewer`), `min_node_weight` (padrão 1), `min_edge_weight` (padrão 1), `max_nodes` (padrão 500), `output_path` (opcional).
     - Quando `format="vosviewer"`, gera o par de arquivos `.map` e `.network` pronto para abertura direta no VOSviewer.
     - Quando `format="gephi"`, gera o arquivo `.gexf` compatível com Gephi.
     - Quando `format="json"`, devolve a estrutura completa de nós e arestas.
   - Total de ferramentas MCP no servidor: 25.

2. **Serviço Desktop (`src/rslapp/desktop/service.py`):**
   - Adiciona `export_network(list_id, network_type, format)` que grava os arquivos na pasta de exportações e devolve caminhos e contagens.

3. **Interface Desktop (`src/rslapp/desktop/pages/list_view.py`):**
   - Na tela Lista (`/lista/{list_id}`):
     - Botões dedicados no card de ações / exportações:
       - **VOSviewer (.map/.net)**: exporta e baixa o arquivo de rede nativo de coautoria.
       - **Gephi (.gexf)**: exporta e baixa o arquivo GEXF.
     - Cartão informativo no topo da tela indicando a densidade de rede (autores e colaborações detectadas).

## O que não faz

- Não altera as chamadas clássicas de exportação em RIS (`export_list(format="ris")`).

## Decisões desta spec

- **Acesso em 1 Clique:** O pesquisador não precisa de comandos de terminal ou scripts em R/Python para obter a rede VOSviewer perfeitamente formatada; um único clique na tela da lista entrega os arquivos prontos.

## Para instituições (D-029)

Permite aos pesquisadores e pós-graduandos integrar seus resultados diretamente a softwares visuais líderes de bibliometria (VOSviewer e Gephi) para teses, dissertações e relatórios institucionais.

## Pronto quando

- [x] Ferramenta `export_network` registrada em `src/rslapp/server.py` e incluída em `_build_http_mcp_server`.
- [x] Testes MCP stdio e HTTP atualizados para 25 ferramentas.
- [x] Método `export_network` implementado em `DesktopService`.
- [x] Botões de exportação de rede implementados na tela Lista do desktop.
- [x] Testes da tela Lista e do servidor passando 100%.
- [x] Linter ruff limpo sem avisos.
