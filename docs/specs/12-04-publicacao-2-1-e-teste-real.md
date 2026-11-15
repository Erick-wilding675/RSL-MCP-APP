# Publicação da 2.1.0 e teste real

**Fase:** 12 · Conectar a IA ao app (2.1) · **Situação:** a fazer (espera o ok do Erick para publicar)

## O que faz

Publica a fase 12 como `rslapp` 2.1.0 e faz o teste real.

- **Publicação** (pede o ok do Erick antes):
  1. versão `2.1.0` no `pyproject.toml` e no `__init__.py`, com `uv lock`;
  2. os gates e o sdist conferido;
  3. `uv publish` pelo Lore;
  4. `gh release create v2.1.0 --target main`, com a nota: "Conectar IA: ligue o Claude, o Cursor e o VS Code ao RSL.app do seu computador com um clique; guia para instituições, com o ChatGPT";
  5. o workflow do app anexa o `.zip` e o AppImage, e o do Docker publica a imagem;
  6. conferência com `uvx` e o servidor de teste atualizado.
- **Teste real do Erick:**
  1. Baixar o `.zip` da release, abrir o app e, em "Conectar IA", conectar o Claude Desktop. Fechar e abrir o Claude Desktop.
  2. No Claude Desktop, pedir uma busca. Ela aparece no Histórico do app.
  3. Conferir que o `claude_desktop_config.json` manteve os outros servidores e que há a cópia `.bak`.
  4. Opcional: instalar no Cursor ou no VS Code pelo botão.
  5. "Desconectar" remove só a entrada do RSL.app.

## O que não faz

- Não anuncia o modo hospedado antes da LGPD (T-007).

## Para instituições

A nota da release aponta para o guia de hospedagem, seção "Para instituições de ensino".

## Pronto quando

- [ ] `rslapp` 2.1.0 no PyPI, conferida com `uvx`
- [ ] Release `v2.1.0` com o `.zip` e o AppImage
- [ ] Imagem no ghcr.io e servidor de teste atualizado
- [ ] Os passos do Erick passam; o que o teste achar vira item desta spec ou tarefa nova

## Vem de

FR-19, FR-20, D-028, D-029.

## Antes de começar

12-01 a 12-03 integradas, e o ok do Erick para publicar.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
