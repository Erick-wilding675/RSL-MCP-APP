# Publicação da 2.0.0 e teste real

**Fase:** 11 · App desktop (2.0) · **Situação:** a fazer (espera o ok do Erick para publicar)

## O que faz

Publica a fase 11 como `rslapp` 2.0.0 e faz o teste real do app.

- **Publicação** (pede o ok do Erick antes):
  1. versão `2.0.0` no `pyproject.toml` e no `__init__.py`;
  2. os gates e o sdist conferido;
  3. `uv publish` pelo Lore;
  4. tag `v2.0.0` e `gh release create` com a nota "app desktop para Windows e Linux; o servidor não muda";
  5. o workflow do app anexa o `.zip` e o AppImage à release, e o do Docker publica a imagem;
  6. conferência com `uvx` e o servidor de teste atualizado.
- **Teste real do Erick:**
  1. No Windows 11, baixar o `.zip` da release, abrir o `RSL.app.exe` e conferir que a janela abre.
  2. Em Configurações, pôr a chave do OpenAlex e salvar. Fechar e abrir de novo: aparece "configurada", sem mostrar o valor.
  3. Buscar um tema com OpenAlex, Crossref e Semantic Scholar e conferir que a lista aparece.
  4. Exportar em RIS e abrir no VOSviewer.
  5. No Histórico, a busca aparece. Repetir gera uma lista nova, e "Abrir log" abre o `log.md` com as duas buscas.
  6. No Claude Desktop, `get_search_log` mostra a busca feita pelo app (mesma pasta de dados).
  7. Opcional: num Linux, o AppImage abre no navegador.

## O que não faz

- Não anuncia o modo hospedado (espera a LGPD, T-007).

## Pronto quando

- [ ] `rslapp` 2.0.0 no PyPI, conferida com `uvx`
- [ ] Release `v2.0.0` com o `.zip` do Windows e o AppImage
- [ ] Imagem `2.0.0` no ghcr.io e o servidor de teste atualizado
- [ ] Os passos do Erick passam; o que o teste achar vira item desta spec ou uma tarefa nova

## Vem de

FR-16, FR-17, FR-18, D-008, D-024, D-025, D-026.

## Antes de começar

11-01 a 11-04 integradas, e o ok do Erick para publicar.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
