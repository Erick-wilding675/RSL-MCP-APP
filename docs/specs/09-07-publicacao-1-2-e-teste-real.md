# Publicação da 1.2.0 e teste real

**Fase:** 9 · Versão 1.2 · **Situação:** a fazer

## O que faz

Publica a fase 9 como `rslapp` 1.2.0 (só acrescenta, então é uma versão menor), atualiza o servidor de teste e faz o teste de ponta a ponta.

- **Publicação** (Claude Code, como na 1.1.0):
  - `version` no `pyproject.toml` e `__version__` em `src/rslapp/__init__.py`;
  - os gates;
  - `uv build --no-sources` e conferência do sdist;
  - `lore secrets run --env prod -- uv publish`, só com os arquivos da 1.2.0;
  - tag `v1.2.0`, que gera a imagem no ghcr.io;
  - `gh release create`;
  - conferência com `uvx` e com a imagem.
- **Servidor de teste:** `docker compose pull && docker compose up -d` na máquina `rsl-app` (D-019), e `/health` respondendo `1.2.0`.
- **Teste real do Erick:**
  1. No Claude Desktop (stdio, pelo PyPI), uma busca de saúde com `pubmed` e `europe_pmc`. A lista mostra as cinco fontes, sem duplicatas visíveis.
  2. Exportar essa lista em BibTeX e importar no Zotero.
  3. Fazer duas buscas do mesmo assunto com strings diferentes, juntar com `merge_lists`, exportar em RIS e abrir no VOSviewer.
  4. No conector de `rsl.sinteselabs.com`, pedir o log de buscas e baixar o `log.md` pelo link.

## O que não faz

- Não anuncia o modo hospedado (espera a LGPD, T-007).

## Pronto quando

- [ ] `rslapp` 1.2.0 no PyPI, conferida com `uvx`
- [ ] Imagem `1.2.0` e `latest` no ghcr.io, e o servidor de teste atualizado
- [ ] Tag e release `v1.2.0` no GitHub
- [ ] Os quatro passos do Erick passam
- [ ] O que o teste achar vira item desta spec ou uma tarefa nova

## Vem de

D-008, D-019, D-020, D-021.

## Antes de começar

09-01 a 09-06 integradas. O contrato, o README e o guia de hospedagem atualizados pelo Claude.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
