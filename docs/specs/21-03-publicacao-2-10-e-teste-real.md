# Publicação da Versão 2.10.0 e Teste Real (DeCS/MeSH Trilíngue)

**Fase:** 21 · Versão 2.10 · **Situação:** pronta

## O que faz

1. Sobe a versão para `2.10.0` em `pyproject.toml` e `src/rslapp/__init__.py`.
2. Executa a suíte de testes completa do núcleo (`pytest tests/`) e do desktop (`pytest tests_desktop/`).
3. Constrói o pacote wheel e tarball (`uv build --no-sources`).
4. Publica a versão `2.10.0` no PyPI.
5. Cria e envia a tag git `v2.10.0` ao GitHub e publica o GitHub Release correspondente com binários executáveis.

## Como testar

1. **Pelo servidor MCP:**
   - Chamar `lookup_descriptors(query="inteligencia artificial")` e conferir se retorna os descritores em PT, EN e ES com sinônimos.
   - Chamar `build_multilingual_search_query(descriptors=["Inteligência Artificial", "Atenção Primária à Saúde"])` e verificar as strings booleanas geradas.
2. **Pelo app desktop:**
   - Na tela Buscar (`/`), clicar no assistente "Descritores DeCS/MeSH", digitar um termo, selecionar os descritores e verificar a inserção automática da string na caixa de busca.

## Onde olhar primeiro

1. `src/rslapp/core/decs.py`: catálogo curado e motor booleano.
2. `src/rslapp/server.py`: ferramentas MCP 28 e 29.
3. `src/rslapp/desktop/pages/search.py`: assistente visual de descritores.

## Pronto quando

- [x] Versão 2.10.0 configurada.
- [x] Gates de testes 100% passando.
- [x] Pacote publicado no PyPI e release gerada no GitHub.
