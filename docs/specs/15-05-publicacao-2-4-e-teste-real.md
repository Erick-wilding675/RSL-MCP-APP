# Publicação da 2.4.0 e Teste Real

**Fase:** 15 · Versão 2.4 · **Situação:** pronta

## O que faz

Fecha a Fase 15 (versão 2.4 · Triagem com Rastro e Fluxograma PRISMA 2020), consolida a documentação técnica e de usuário, valida a suíte completa de testes (núcleo e desktop), gera os pacotes de distribuição no padrão do repositório e prepara o lançamento oficial no PyPI e GitHub Releases:

1. **Subida de versão:**
   - `pyproject.toml` atualizado para `2.4.0`.
   - `src/rslapp/__init__.py` atualizado para `2.4.0`.

2. **Documentação atualizada:**
   - `docs/interface-contract.md`: contrato formal das 4 novas ferramentas (`screen_work`, `get_screening_status`, `get_prisma_flow`, `get_ai_disclosure`).
   - `docs/hospedagem.md`: seção institucional (D-029) cobrindo triagem isolada e auditoria ética de IA.
   - `README.md`: destaques da versão 2.4 com triagem, PRISMA 2020 e declaração de integridade acadêmica.
   - `.blueprint/state.md`: estado do projeto atualizado.

3. **Verificação de Gates:**
   - Linting com `ruff check .` sem erros nem avisos.
   - Suíte do núcleo: 780 testes passando limpos.
   - Suíte do app desktop: 65 testes passando limpos.
   - Empacotamento com `uv build --no-sources` gerando sdist (`.tar.gz`) e wheel (`.whl`).

## Roteiro de Teste Real para o Erick

Após a publicação ou no ambiente local (`rslapp-desktop`), você pode testar o fluxo completo da 2.4:

1. **Triagem Rápida na Interface:**
   - Abra uma lista salva ou faça uma busca nova na tela Buscar (`/`).
   - Na tela da lista (`/lista/{list_id}`), veja o novo cartão métrico de triagem e clique no botão **"Iniciar Triagem"**.
   - Na tela de triagem (`/triagem/{list_id}`), navegue com as setas do teclado e use os atalhos:
     - Tecla **I**: inclui o trabalho e avança;
     - Tecla **E**: exclui o trabalho com o motivo selecionado;
     - Tecla **M**: marca como dúvida / talvez.
   - Observe a barra de progresso e os contadores atualizando instantaneamente.

2. **Fluxograma PRISMA 2020 Vetorial:**
   - Clique em **"Fluxograma PRISMA 2020"** ou acesse `/prisma/{list_id}`.
   - Veja o diagrama diagramado com os números exatos das bases, duplicatas removidas, artigos triados, excluídos e incluídos.
   - Clique em **"Baixar Diagrama SVG"** e abra no navegador ou Inkscape para conferir a qualidade vetorial.
   - Veja a aba **Checklist PRISMA-S** e confira a tabela preenchida com a estratégia e rastreabilidade.

3. **Declaração Ética de IA (COPE/ICMJE/SciELO):**
   - Na aba **"Declaração de Uso de IA"**, alterne entre Português e Inglês.
   - Observe o rastro de quantas decisões foram humanas vs assistidas por IA.
   - Clique em **"Copiar Declaração"** para uso direto na seção de Metodologia do manuscrito.

4. **Ferramentas MCP:**
   - No Claude Desktop ou Claude Code, chame:
     - `screen_work(list_id="l-0001", work_id="...", decision="included", notes="Estudo chave")`
     - `get_screening_status(list_id="l-0001")`
     - `get_prisma_flow(list_id="l-0001")`
     - `get_ai_disclosure(list_id="l-0001", language="pt")`

## Pronto quando

- [x] Versão 2.4.0 definida em `pyproject.toml` e `src/rslapp/__init__.py`.
- [x] Documentos (`README.md`, `docs/hospedagem.md`, `docs/interface-contract.md`, `.blueprint/state.md`) atualizados.
- [x] `ruff check .` 100% limpo.
- [x] `uv run pytest` e `uv run pytest tests_desktop/ -c tests_desktop/pytest.ini` 100% passando.
- [x] `uv build --no-sources` bem-sucedido.
- [x] Branch de integração mesclada na `main`.
