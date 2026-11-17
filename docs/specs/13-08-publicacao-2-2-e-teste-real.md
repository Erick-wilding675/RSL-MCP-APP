# Publicação da 2.2.0 e teste real

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** pronta

## O que faz

Publica a versão 2.2.0 do `rslapp` no PyPI e GitHub releases com executáveis para Windows e Linux, imagem Docker e servidor MCP atualizado.

- **Novidades da versão 2.2.0:**
  1. **Visual Novo:**
     - Casca responsiva com drawer lateral recolhível e alternador de tema claro/automático/escuro persistido (D-031).
     - Telas redesenhadas: Buscar, Lista, Histórico, Configurações e Conectar IA.
  2. **Verificador de Referências contra Alucinação (ideia 5.1, FR-21, D-030):**
     - Ferramenta MCP `verify_references` e tela `/verificar` para validação cruzada contra Crossref e OpenAlex.
  3. **Retratações nas Listas (ideia 5.2, FR-22, D-032):**
     - Detecção automática de retratações via base Retraction Watch (Crossref) e OpenAlex.
     - Sinalização em RIS (`N1`), BibTeX (`note`), Scopus CSV (`Document Type`), tela da Lista com badge `RETRATADO` e métricas de alerta.
  4. **Importar Exportações de Fora (ideia 7, FR-23, D-033):**
     - Importador para RIS, BibTeX, Scopus CSV e Web of Science TSV/Tagged.
     - Ferramenta MCP `import_works` e tela desktop `/importar`.
  5. **Referências na ABNT NBR 6023:2018 (ideia 4.3, FR-24, D-034):**
     - Formatação segundo as normas da ABNT e novo formato de exportação `abnt` (`.txt`) em ordem alfabética.
     - Botão de exportação `ABNT` na tela da Lista.

- **Publicação:**
  1. Atualizar versão para `2.2.0` no `pyproject.toml` e `src/rslapp/__init__.py`.
  2. Rodar gates e conferir `uv build --no-sources` e sdist.
  3. Mesclar `integracao-2.2` na `main`.
  4. `lore secrets run --env prod -- uv publish dist/*`.
  5. `gh release create v2.2.0 --target main`.
  6. Workflow do app anexa o `.zip` do Windows e o AppImage Linux, e publica imagem no ghcr.io.

- **Roteiro de Teste Real do Erick:**
  1. Abrir a versão 2.2.0 (ou executável baixado da release).
  2. Testar alternância de tema no drawer lateral (claro, escuro, automático).
  3. Abrir a tela "Importar", carregar um arquivo exportado do Scopus ou colar entradas BibTeX e processar. Conferir se a nova lista abre corretamente.
  4. Abrir a tela "Verificar", colar referências e verificar correspondências reais vs. alucinações.
  5. Na tela Lista, testar exportação no novo formato "ABNT".

## Pronto quando

- [x] Versão `2.2.0` atualizada no `pyproject.toml` e em `src/rslapp/__init__.py`.
- [x] Todos os gates passam (testes 3.10 e 3.14, testes do desktop, linter Ruff).
- [x] Pacote construído com `uv build --no-sources`.
- [x] Branch `integracao-2.2` mesclada na `main`.
- [x] Pacote publicado no PyPI e release `v2.2.0` criada no GitHub com executáveis.

## Vem de

D-030 a D-034, FR-21 a FR-24.
