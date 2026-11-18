# Publicação da Versão 2.6.0 e Roteiro de Teste Real

**Fase:** 17 · Versão 2.6 · **Situação:** pronta

## O que faz

Registra o checklist de empacotamento, qualidade e o roteiro de testes reais da versão 2.6.0 (Fichamento Científico com Rastro de Autoria e Exportação Markdown):

1. **Gates de Qualidade:**
   - 794 testes unitários e de integração do núcleo passando (`uv run pytest tests/`).
   - 68 testes de componentes e páginas do desktop passando (`uv run --extra desktop --extra desktop-dev pytest tests_desktop/ -c tests_desktop/pytest.ini`).
   - Linter ruff 100% limpo sem erros nem avisos (`uv run ruff check .`).
   - Pacote de distribuição construído com sucesso (`dist/rslapp-2.6.0.tar.gz` e `dist/rslapp-2.6.0-py3-none-any.whl`).

2. **Roteiro de Teste Real para o Usuário:**
   - **Passo 1:** Executar `rslapp-desktop` ou abrir o executável.
   - **Passo 2:** Acessar qualquer lista de resultados em `/lista/{list_id}`.
   - **Passo 3:** Clicar no botão "Fichamento" no cabeçalho ou no ícone de ficha ao lado de qualquer artigo na tabela.
   - **Passo 4:** Preencher os campos metodológicos (Objetivo, Método, Amostra, Resultados, Limitações, Citações).
   - **Passo 5:** Selecionar a origem da autoria (ou clicar em "Validar como Revisado") e salvar a ficha.
   - **Passo 6:** Clicar em "Copiar Markdown (Obsidian)" e colar no Obsidian ou editor de texto para verificar frontmatter YAML e formatação de callouts.
   - **Passo 7:** Na tela da lista, clicar em "Fichas (.md)" e "Pacote de Reprodutibilidade (.zip)" para verificar a inclusão de `notes.md` e `notes.json` com seus respectivos hashes SHA-256 no arquivo `.zip`.
