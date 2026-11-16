# Modo servidor MCP no executável do app

**Fase:** 12 · Conectar a IA ao app (2.1) · **Situação:** entregue (2026-11-15)

## O que faz

Faz o mesmo programa do app desktop servir também como servidor MCP por stdio (D-028, FR-19). Quem baixou o `.zip` ou o AppImage passa a ter o RSL.app inteiro para a IA, sem instalar Python nem `uv`.

### A opção `--mcp`

- `rslapp-desktop --mcp`, `RSL.app.exe --mcp` e `RSL.app-<versão>.AppImage --mcp` iniciam o servidor MCP por stdio, o mesmo de `rslapp` sem argumentos (`rslapp.server.main()`), e não abrem janela nem servidor web.
- Antes de iniciar, o modo faz o mesmo que o app ao abrir: `capture_system_env_vars()`, `load_settings()` e `apply_to_environ()`. Assim a IA usa a mesma pasta de dados, a mesma pasta de exportação, o mesmo e-mail e as mesmas chaves que a pessoa salvou em Configurações (D-026). Uma variável que já veio do sistema continua valendo.
- **Nada pode ir para o stdout além do protocolo MCP.** Nenhum `print`, aviso ou log no stdout nesse modo; o que precisar sair vai para o stderr.
- `--mcp` e `--check` juntos são erro de uso, com código 2 (o padrão do `argparse` com grupo mutuamente exclusivo).
- `_ensure_stdio_streams()` não pode trocar o stdin e o stdout por `os.devnull` no modo `--mcp`.
  - Se o stdin ou o stdout forem `None`, o modo escreve uma mensagem curta no stderr (se houver) e sai com código 1.
  - Hoje essa função roda antes de interpretar os argumentos; reorganize para que o modo seja conhecido antes.

### O executável do Windows (o ponto mais arriscado)

O `.exe` é gerado com `--windowed`, o subsistema gráfico do Windows. É preciso confirmar que ele recebe o stdin e o stdout quando outro programa o inicia com pipes, como o Claude Desktop faz.

1. **Confirme primeiro.** No workflow `desktop.yml`, no job do Windows, depois do teste `--check`, acrescente um teste de fumaça do modo MCP:
   - um script Python inicia `dist\RSL.app\RSL.app.exe --mcp` com `subprocess.Popen` e pipes no stdin e no stdout;
   - envia a mensagem `initialize` do MCP e lê a resposta;
   - falha o job se não chegar uma resposta JSON-RPC com `result.serverInfo` em até 30 segundos.
   - Use o cliente stdio do SDK `mcp` 2.x, se for simples; senão, JSON-RPC à mão, uma mensagem por linha. Confira na documentação da versão 2 antes de escrever (T-009).
2. **Se o teste falhar no `--windowed`**, monte um segundo executável de console, `rslapp-mcp.exe`, na mesma pasta `dist\RSL.app`:
   - feito com o PyInstaller a partir de um ponto de entrada pequeno que chama o mesmo modo;
   - o `.zip` leva os dois;
   - nesse caso, a 12-02 aponta a IA para o `rslapp-mcp.exe`.

   Registre na spec qual caminho foi usado e por quê.
3. O mesmo teste de fumaça roda no Linux, com o AppImage e `--appimage-extract-and-run --mcp`.

### Teste sem o NiceGUI

- Em `tests/desktop`, sem importar o NiceGUI:
  - a interpretação de `--mcp`;
  - o erro de `--mcp` com `--check`;
  - que o modo carrega as configurações e chama a função do servidor, com o servidor trocado por um dublê;
  - que nada é escrito no stdout.
- Um teste de ponta a ponta em `tests/`: sobe `python -m rslapp.desktop --mcp` (ou o ponto de entrada equivalente) num subprocesso com `RSL_DATA_DIR` e `RSL_DESKTOP_CONFIG` temporários, faz `initialize` e `tools/list`, e confere que `search_works` está na lista.
  - Se esse ponto de entrada exigir o NiceGUI, o teste vai para `tests_desktop`.

## O que não faz

- Não cria a tela que liga as IAs (12-02).
- Não muda o servidor MCP, as ferramentas ou o modo HTTP.

## Para instituições

Nada muda para quem hospeda: o modo hospedado continua sendo `rslapp serve` na imagem Docker (D-011). O `--mcp` é só para o computador de cada pesquisador.

## Pronto quando

- [x] `RSL.app.exe --mcp` (ou `rslapp-mcp.exe`) responde ao `initialize` no teste de fumaça do workflow, no Windows e no Linux
- [x] O modo `--mcp` usa as chaves e a pasta salvas em Configurações
- [x] Os gates passam: `tests_desktop`, a suíte principal em 3.10 e 3.14, e o ruff
- [x] Nada além do protocolo vai para o stdout no modo `--mcp`

## Vem de

FR-19, D-026, D-027, D-028.

## Antes de começar

- Leia `src/rslapp/desktop/app.py`, `src/rslapp/desktop/__main__.py`, `src/rslapp/cli.py` e o fim de `src/rslapp/server.py`.
- Leia o `desktop.yml` (11-04).
- Leia a documentação do transporte stdio do SDK `mcp` 2.x e do cliente stdio, se for usá-lo no teste (T-009).
- Tamanho esperado: cerca de 200 linhas, com o workflow. Um commit por parte que dê para revisar.

## Resultado da entrega

Código pelo Gemini (`agy`), revisão e workflow pelo Claude, em 2026-11-15.

- **Commits:**
  - `62e2719` modo `--mcp` com os testes: grupo mutuamente exclusivo com `--check`; o modo é decidido antes de `_ensure_stdio_streams()`; carrega o `desktop.json` como o app e chama `rslapp.server.main()`; o `__main__.py` não importa o NiceGUI no `--mcp`.
  - `29db82b` teste de fumaça no workflow (`packaging/smoke_mcp.py`, JSON-RPC à mão por Popen e pipes), no Windows e no Linux.
  - `4c39559` correção: o script usa o caminho absoluto do executável (no Linux, `./X.AppImage` virava `X.AppImage` e o sistema procurava no PATH).
- **O caminho usado no Windows:** o próprio `RSL.app.exe --mcp`. O teste de fumaça do workflow (run 43794342508) mostrou que o `.exe` feito com `--windowed` recebe o stdin e o stdout por pipes e responde ao `initialize`. O `rslapp-mcp.exe` de console não foi preciso.
- **Gates na worktree:** `tests_desktop` 19 passaram; suíte principal 694 passaram e 1 pulado no 3.10 e no 3.14; ruff sem achados.
- **Teste de ponta a ponta** em `tests/desktop/test_check.py`: sobe `python -m rslapp.desktop --mcp` com o cliente stdio do SDK 2.x, lista as ferramentas e chama `list_sources`, conferindo que a chave do `desktop.json` vale e não aparece na resposta.
- **Pequeno, sem efeito:** o `__main__.py` envolve os imports do NiceGUI em `contextlib.suppress(ImportError)`; sem o NiceGUI, a janela falha logo depois do mesmo jeito.

## Como testar

**Onde olhar primeiro:**

1. `src/rslapp/desktop/app.py`, `main()`: no `--mcp`, nada pode escrever no stdout antes de `server.main()`, e as chaves vêm do `desktop.json` sem sobrescrever as do sistema.
2. `src/rslapp/desktop/__main__.py`: os imports do NiceGUI só acontecem fora do `--mcp`.
3. `.github/workflows/desktop.yml` e `packaging/smoke_mcp.py`: o teste que garante o stdio no `.exe`.

**Para conferir:**

- `uv run --extra dev python -m pytest tests/desktop/test_check.py -q` passa.
- No Windows, com o `.zip` da próxima release: `RSL.app.exe --mcp` num terminal fica esperando (é o protocolo), sem abrir janela; Ctrl+C sai.
- O uso real vem com a tela "Conectar IA" (12-02).
