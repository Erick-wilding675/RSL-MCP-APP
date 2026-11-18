# Publicação da 2.7.0 e Teste Real

**Fase:** 18 · Versão 2.7 · **Situação:** pronta

## O que faz

Fecha a **Fase 18 (Versão 2.7.0)**, consolida as entregas do Protocolo Metodológico Pré-Busca Versionado (PICO, PCC, PICo, SPIDER, Narrativo) compatível com PROSPERO e OSF (FR-30, D-041), gera o pacote `rslapp` 2.7.0 no PyPI, tag `v2.7.0` no GitHub com executáveis desktop (.zip Windows x64 e AppImage Linux) e imagem OCI no GHCR.

## Como testar

1. **Protocolo Metodológico no Desktop (`rslapp-desktop`):**
   - Abrir o app: no menu lateral, clicar em **Protocolos** (`/protocolos`).
   - Clicar em **Novo Protocolo**:
     - Preencher título: `Efetividade de Agentes Autônomos de IA em Revisões Sistemáticas de Saúde`.
     - Selecionar Framework: `PICO (População, Intervenção, Comparação, Desfecho)`.
     - Observar o ajuste dinâmico dos componentes (População, Intervenção, Comparação, Desfecho, Desenho de Estudo).
     - Preencher critérios de inclusão e exclusão.
     - Marcar auxílio de IA e informar modelo (`Claude 3.5 Sonnet` ou `Gemini 1.5 Pro`).
     - Clicar em **Salvar Protocolo**.
     - Verificar badge de versão `v1` e notificação de sucesso.
     - Clicar em **Copiar Markdown (PROSPERO/OSF)** e colar em editor de texto; verificar formatação acadêmica rigorosa, tabelas de framework e critérios, e declaração de transparência de IA.
     - Fazer alteração e salvar novamente; verificar incremento para versão `v2` e histórico arquivado.

2. **Ferramentas MCP de Protocolo (via stdio ou cliente MCP):**
   - Chamar `save_protocol`, `get_protocol`, `list_protocols` e `export_protocol_markdown`.

3. **Pacote de Reprodutibilidade com Protocolo:**
   - Realizar uma busca vinculando o `protocol_id`.
   - Baixar o pacote `.zip` de reprodutibilidade e constatar a presença de `protocol.md` e `protocol.json`, além dos hashes no manifesto `checksums.sha256`.

## Verificação dos Gates

- [x] Linter ruff sem nenhum aviso.
- [x] 801 testes do núcleo passando (`uv run pytest tests/`).
- [x] 71 testes da interface desktop passando (`uv run --extra desktop --extra desktop-dev pytest tests_desktop/ -c tests_desktop/pytest.ini`).
- [x] Build do pacote gerando wheel e tarball (`uv build --no-sources`).
- [x] Publicação no PyPI via token seguro no Lore.
- [x] Tag `v2.7.0` enviada ao GitHub e release publicada com binários.
