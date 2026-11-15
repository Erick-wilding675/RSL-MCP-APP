# Publicação da 2.0.0 e teste real

**Fase:** 11 · App desktop (2.0) · **Situação:** a fazer (espera o ok do Erick para publicar)

## O que faz

Publica a fase 11 como `rslapp` 2.0.0 e faz o teste real do app.

- **Publicação** (pede o ok do Erick antes):
  1. versão `2.0.0` no `pyproject.toml` e no `__init__.py`;
  2. os gates e o sdist conferido;
  3. `uv publish` pelo Lore;
  4. `gh release create v2.0.0` com a nota "app desktop para Windows e Linux; o servidor não muda" **antes** de enviar a tag (ou com `--target main`, que cria a tag junto). Se o workflow do app terminar antes e não achar a release, ele a cria como rascunho e o `gh release create` falharia;
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

- [x] `rslapp` 2.0.0 no PyPI, conferida com `uvx`
- [x] Release `v2.0.0` com o `.zip` do Windows e o AppImage
- [x] Imagem `2.0.0` no ghcr.io e o servidor de teste atualizado
- [ ] Os passos do Erick passam; o que o teste achar vira item desta spec ou uma tarefa nova

## Vem de

FR-16, FR-17, FR-18, D-008, D-024, D-025, D-026.

## Antes de começar

11-01 a 11-04 integradas, e o ok do Erick para publicar.

## Resultado da entrega

`rslapp` 2.0.0 publicada em 2026-11-15, com o ok do Erick (commit `196c0b9`).

- Gates antes de publicar: 689 passaram e 1 pulado em 3.10 e 3.14; `tests_desktop` 19 passaram; ruff limpo. O sdist leva só `src`, `tests`, `tests_desktop`, README, licença e `pyproject.toml`, sem arquivo de chave.
- PyPI pelo Lore; conferida com `uvx --from rslapp==2.0.0` (mostra 2.0.0).
- Release [`v2.0.0`](https://github.com/Erick-wilding675/RSL-MCP-APP/releases/tag/v2.0.0) criada com `gh release create --target main` (a tag nasceu junto). O workflow do app ([43743792231](https://github.com/Erick-wilding675/RSL-MCP-APP/actions/runs/43743792231)) passou nos dois sistemas e anexou `RSL.app-2.0.0-windows-x64.zip` (38 MB) e `RSL.app-2.0.0-linux-x86_64.AppImage` (51 MB); a release não ficou como rascunho.
- Imagem Docker pelo Actions; servidor de teste atualizado com `docker compose pull && up -d`, e `/health` responde 2.0.0.

### Onde olhar primeiro

1. **O `.exe` baixado da release** (passo 1 do teste): é o primeiro executável que chega a quem não é desenvolvedor, e o Windows avisa que não é assinado.
2. **As chaves em Configurações** (passo 2): ficam em `desktop.json`, fora da pasta de dados, e a tela nunca mostra o valor salvo.

## Como testar

Os passos do Erick, na seção "O que faz". Para conferir a publicação:

1. `curl https://rsl.sinteselabs.com/health` deve responder `"version":"2.0.0"`.
2. `uvx --from rslapp==2.0.0 python -c "import rslapp; print(rslapp.__version__)"` deve mostrar `2.0.0`.
3. A página da release `v2.0.0` deve ter o `.zip` e o AppImage.
