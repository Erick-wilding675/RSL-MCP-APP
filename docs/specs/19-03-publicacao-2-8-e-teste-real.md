# Publicação da 2.8.0 e Teste Real

**Fase:** 19 · Versão 2.8 · **Situação:** pronta

## O que faz

Fecha a **Fase 19 (Versão 2.8.0)**, consolida as entregas das Redes Bibliométricas Nativas para VOSviewer (`.map` e `.network`) e Gephi (`.gexf`) (FR-31, D-042, ideia 3.1), gera o pacote `rslapp` 2.8.0 no PyPI, tag `v2.8.0` no GitHub com executáveis desktop (.zip Windows x64 e AppImage Linux) e imagem OCI no GHCR.

## Como testar

1. **Exportação de Redes Bibliométricas no Desktop (`rslapp-desktop`):**
   - Abrir o app e consultar qualquer lista com múltiplos artigos e autores (ex.: `/lista/l-0001`).
   - No cartão **Exportar**:
     - Clicar em **VOSviewer (.map/.net)**: verificar notificação de sucesso informando total de autores/nós e colaborações/arestas geradas. Os arquivos `network_{list_id}_coauthorship.map` e `network_{list_id}_coauthorship.network` são salvos na pasta de exportações.
     - Abrir o software VOSviewer: menu *Create -> Create a map based on network data -> Read VOSviewer map and network files* e selecionar os arquivos gerados. Verificar que a rede abre instantaneamente com nós, rótulos e densidades calibradas, sem necessidade de configuração manual.
     - Clicar em **Gephi (.gexf)**: verificar geração do arquivo XML GEXF válido e abrir no Gephi, confirmando a correta importação de nós e arestas com pesos.
     - Clicar em **Pacote de Reprodutibilidade (.zip)**: abrir o zip gerado e constatar os arquivos `vosviewer_coauthorship.map`, `vosviewer_coauthorship.network` e `gephi_coauthorship.gexf` auditados no manifesto `checksums.sha256`.

2. **Ferramenta MCP (`export_network`):**
   - Chamar `export_network` com `network_type="coauthorship"`, `source_coupling` e `keyword_cooccurrence`.
   - Testar formatos `vosviewer`, `gephi` e `json`.

## Verificação dos Gates

- [x] Linter ruff sem nenhum aviso em todo o repositório.
- [x] 809 testes do núcleo passando (`uv run pytest tests/`).
- [x] 71 testes da interface desktop passando (`uv run --extra desktop --extra desktop-dev pytest tests_desktop/ -c tests_desktop/pytest.ini`).
- [x] Build do pacote gerando wheel e tarball (`uv build --no-sources`).
- [x] Publicação no PyPI via token seguro no Lore (`rslapp-2.8.0`).
- [x] Tag `v2.8.0` enviada ao GitHub e release publicada com executáveis.
