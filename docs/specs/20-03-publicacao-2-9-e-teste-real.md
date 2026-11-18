# Publicação da Versão 2.9.0 e Teste Real (Revisão Viva)

**Fase:** 20 · Versão 2.9 · **Situação:** pronta

## O que faz

1. Sobe a versão para `2.9.0` em `pyproject.toml` e `src/rslapp/__init__.py`.
2. Executa a suíte de testes completa do núcleo (`pytest tests/`) e do desktop (`pytest tests_desktop/`).
3. Constrói o pacote wheel e tarball (`uv build --no-sources`).
4. Publica a versão `2.9.0` no PyPI.
5. Cria e envia a tag git `v2.9.0` ao GitHub e publica o GitHub Release correspondente com binários executáveis.

## Como testar

1. **Pelo app desktop:**
   - Acesse o app e abra uma lista salva anteriormente (ou execute uma busca).
   - Clique em "Revisão Viva (Atualizar Busca)".
   - Observe o diálogo comparativo informando os artigos prévios e os novos artigos encontrados.
   - Navegue para a nova lista e verifique os novos artigos destacados com o selo `NOVO NA BUSCA`.
2. **Pelo servidor MCP:**
   - Execute a ferramenta `compare_search_versions` com dois identificadores de listas para visualizar o relatório metodológico em Markdown e estatísticas comparativas.

## Onde olhar primeiro

1. `src/rslapp/core/differential.py`: lógica de deduplicação e detecção de diferenças entre corpus de busca.
2. `src/rslapp/server.py`: registro das ferramentas MCP 26 e 27.
3. `src/rslapp/desktop/pages/list_view.py`: integração visual da Revisão Viva na interface.

## Pronto quando

- [x] Versão 2.9.0 configurada.
- [x] Testes passando 100%.
- [x] Pacote publicado no PyPI e release gerada no GitHub.
