# Tela "Conectar IA"

**Fase:** 12 · Conectar a IA ao app (2.1) · **Situação:** pronta (testada pelo Erick em 2026-11-16)

## O que faz

Uma tela nova no app, "Conectar IA" (rota `/conectar`, no menu entre Histórico e Configurações), que liga a IA da pessoa ao RSL.app do computador dela (D-028, FR-19). Depois disso, as buscas que a IA faz aparecem no Histórico do app, porque usam a mesma pasta.

### O comando que as IAs vão rodar

Uma função sem o NiceGUI, `mcp_launch_command() -> tuple[str, list[str]]`, em `src/rslapp/desktop/connect.py`, decide o que a IA executa:

- **No executável empacotado** (`sys.frozen`):
  - o caminho absoluto do próprio executável (`sys.executable`), com `["--mcp"]`;
  - o teste de fumaça da 12-01 provou, em 2026-11-15, que o `RSL.app.exe` sem console recebe o stdio, então o `rslapp-mcp.exe` não é preciso.
- **No AppImage:** o caminho do arquivo `.AppImage` (variável de ambiente `APPIMAGE`), com `["--mcp"]`, e não o caminho temporário de dentro dele.
- **Instalado pelo `pip`:** o caminho absoluto do comando `rslapp-desktop` do mesmo ambiente (ao lado de `sys.executable`; no Windows, `Scripts\rslapp-desktop.exe`), com `["--mcp"]`. Se não achar, usa `sys.executable` com `["-m", "rslapp.desktop", "--mcp"]`, que funciona (teste de ponta a ponta da 12-01).
  - **Não use o comando `rslapp`:** ele não lê o `desktop.json`, e a IA buscaria sem as chaves salvas na tela Configurações (correção do Claude em 2026-11-16).
- **Nenhuma chave entra na configuração das IAs.** O modo `--mcp` lê as chaves do `desktop.json` (12-01). Só o `RSL_DESKTOP_CONFIG` vai no `env`, e só quando estiver definido no ambiente do app.

### Um cartão por IA

1. **Claude Desktop**
   - **Onde fica o arquivo:** `%APPDATA%\Claude\claude_desktop_config.json` no Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` no macOS e `~/.config/Claude/claude_desktop_config.json` no Linux (fonte: modelcontextprotocol.io, "Connect to local MCP servers", lida em 2026-11-15).
   - **O botão "Conectar":**
     - lê o arquivo, ou começa de `{}` se ele não existe;
     - se o JSON for ilegível, não mexe nele e mostra o erro com o caminho;
     - mostra numa caixa de confirmação o trecho que vai entrar, `mcpServers.rslapp` com `command` e `args`;
     - se já existe uma entrada `rslapp` diferente, mostra a atual e pergunta se troca.
   - **Ao confirmar:**
     - guarda uma cópia `claude_desktop_config.json.bak-<data e hora>` na mesma pasta;
     - grava com `atomic_write_replace`, mantendo todas as outras chaves e servidores do arquivo;
     - avisa: "Feche e abra o Claude Desktop para ele ver o RSL.app."
   - **"Desconectar":** remove só a entrada `rslapp`, com a mesma cópia antes.
   - **O estado mostrado:** "conectado" quando a entrada existe e aponta para este app; "conectado a outra instalação" quando ela aponta para outro comando; "não conectado" quando não existe.
2. **Cursor**
   - O botão "Instalar no Cursor" abre `cursor://anysphere.cursor-deeplink/mcp/install?name=rslapp&config=<base64>`, que o Cursor confirma (fonte: cursor.com/docs/mcp/install-links, lida em 2026-11-15).
   - O `config` é o objeto do servidor, sem o nome por fora: `{"command": ..., "args": [...]}`, passado por `json.dumps` e depois base64 (o nome vai no parâmetro `name`). Fonte: cursor.com/docs/mcp/install-links, relida em 2026-11-15. Codifique o base64 para a URL (`urllib.parse.quote`), porque ele pode ter `+`, `/` e `=`.
   - Abra o link com o mesmo mecanismo que o app já usa para abrir pastas (`os.startfile` no Windows, `xdg-open` no Linux), sem shell.
3. **VS Code (Copilot)**
   - Não há link de instalação documentado: as páginas oficiais relidas em 2026-11-15 (code.visualstudio.com/docs/copilot/customization/mcp-servers e /docs/agents/reference/mcp-configuration) não descrevem `vscode:mcp/install`. Não use esse link.
   - O cartão mostra o comando oficial, com o botão "Copiar": `code --add-mcp '<JSON>'`, em que o JSON é `{"name": "rslapp", "type": "stdio", "command": ..., "args": [...]}` (mais `env` quando houver). Ele grava no perfil do usuário do VS Code.
   - E um segundo bloco "Ou copie para o `.vscode/mcp.json`", com `{"servers": {"rslapp": {"type": "stdio", "command": ..., "args": [...]}}}`, e o link da página de referência.
   - No Windows, o comando com aspas simples é para o PowerShell; diga isso numa linha abaixo do bloco.
4. **Claude Code**
   - Mostra o comando pronto, com um botão "Copiar": `claude mcp add --transport stdio --scope user rslapp -- "<command>" <args>`.
   - Com `RSL_DESKTOP_CONFIG`: `claude mcp add --env RSL_DESKTOP_CONFIG=<caminho> --transport stdio --scope user rslapp -- ...`. O `--env` não pode vir logo antes do nome (a documentação avisa), por isso o `--transport` fica entre eles.
   - Fonte: code.claude.com/docs/en/mcp, relida em 2026-11-15: as opções vêm antes do nome, e tudo depois do `--` vai para o servidor sem mudança.
5. **Outras IAs**
   - Um bloco com o trecho JSON genérico (`command` e `args`) e o botão "Copiar", para qualquer cliente que aceite MCP local.
6. **ChatGPT**
   - Um texto curto: o ChatGPT só se liga a servidores na internet, não ao computador da pessoa. A forma de usá-lo é pela instituição, com o link para o guia de hospedagem, seção "ChatGPT" (12-03).

### Textos

- Português do Brasil, frases curtas.
- No topo: "Ligue a sua IA ao RSL.app deste computador. As buscas que ela fizer ficam na sua pasta de dados e aparecem no Histórico."

## O que não faz

- Não instala nenhuma IA nem verifica se ela está instalada, além de olhar se o arquivo ou a pasta de configuração existe para mostrar o estado.
- Não grava chave em arquivo de outro programa.
- Não cria extensão `.mcpb` (fica para depois, D-028).

## Para instituições

- Uma instituição pode distribuir o executável aos seus pesquisadores (laboratórios, máquinas da biblioteca), e cada pessoa conecta a própria IA por esta tela.
- Para quem prefere não instalar nada, a instituição oferece o servidor hospedado, e a pessoa conecta pelo link e pelo código pessoal (guia de hospedagem, 12-03).
- A entrega acrescenta ao `docs/hospedagem.md` uma seção curta "Distribuir o app aos pesquisadores", com essas duas formas.

## Pronto quando

- [x] A tela mostra os seis cartões e o estado do Claude Desktop
- [x] "Conectar" e "Desconectar" no Claude Desktop preservam o resto do arquivo e deixam a cópia `.bak`
- [x] Testes sem o NiceGUI em `tests/desktop` para `connect.py`:
  - o comando em cada caso: executável, AppImage e pip;
  - juntar com um arquivo existente e com outros servidores;
  - arquivo ilegível;
  - remover;
  - o link do Cursor decodificado de volta ao mesmo JSON;
  - o JSON do `code --add-mcp` e o comando do Claude Code, com e sem `RSL_DESKTOP_CONFIG`, e com caminho que tem espaço;
  - nenhuma chave na saída, mesmo com chaves no ambiente.
- [x] Teste da tela em `tests_desktop`
- [x] Os gates passam
- [x] O guia de hospedagem tem a seção "Distribuir o app aos pesquisadores"

## Vem de

FR-19, D-026, D-028, D-029.

## Antes de começar

- 12-01 integrada.
- Leia `src/rslapp/desktop/pages/settings_page.py` e `history.py`, para seguir o estilo, e `src/rslapp/store/_atomic.py`.
- Leia as páginas oficiais citadas acima, por inteiro, antes de escrever cada cartão (T-001).
- Tamanho esperado: cerca de 350 linhas com os testes. Divida em dois commits: `connect.py` com os testes, depois a tela.

## Resultado da entrega

Entregue pelo Gemini (`agy`) em 2026-11-15:

- **`src/rslapp/desktop/connect.py` e `src/rslapp/__main__.py`** (sem importar o NiceGUI):
  - `mcp_launch_command()` devolve `(os.path.abspath(APPIMAGE), ["--mcp"])` no AppImage, `(os.path.abspath(sys.executable), ["--mcp"])` no executável empacotado (`sys.frozen`), o caminho absoluto do comando `rslapp` ao lado de `sys.executable` sem argumentos quando instalado pelo `pip`, ou `(os.path.abspath(sys.executable), ["-m", "rslapp"])` como recuo. Foi criado `src/rslapp/__main__.py` chamando `rslapp.cli:main` para que `python -m rslapp` funcione.
  - `mcp_env()` e `mcp_server_entry()` incluem apenas `RSL_DESKTOP_CONFIG` quando definido no ambiente; nenhuma chave de `KEY_VARS` ou outra variável entra nas saídas.
  - `claude_desktop_config_path()`, `read_claude_desktop_config()`, `inspect_claude_desktop()`, `claude_desktop_status()`, `connect_claude_desktop()` e `disconnect_claude_desktop()` leem, validam, juntam e removem apenas `mcpServers.rslapp`, preservando todas as outras chaves e servidores, gravando antes uma cópia `claude_desktop_config.json.bak-<YYYYMMDD-HHMMSS>` na mesma pasta e escrevendo o arquivo final com `atomic_write_replace`. Se o JSON for ilegível, levantam `ClaudeConfigError` com o caminho sem tocar no arquivo.
  - `cursor_install_url()` e `open_cursor_link()` geram o link `cursor://anysphere.cursor-deeplink/mcp/install?name=rslapp&config=<base64 codificado com urllib.parse.quote(safe="")>` e abrem via `os.startfile` (Windows) ou `xdg-open` (Linux) sem `shell=True`.
  - `vscode_add_mcp_json()`, `vscode_add_mcp_command()` e `vscode_mcp_config_json()` geram o comando `code --add-mcp '<JSON>'` e o trecho `servers.rslapp` para `.vscode/mcp.json`.
  - `claude_code_command()` monta `claude mcp add [--env RSL_DESKTOP_CONFIG=...] --transport stdio --scope user rslapp -- "<command>" <args>`, mantendo `--env` antes de `--transport stdio` e tratando caminhos com espaço.
  - `generic_mcp_json()` devolve o trecho `mcpServers.rslapp` para outros clientes MCP.
- **Páginas oficiais relidas (T-001):** `modelcontextprotocol.io/docs/develop/connect-local-servers.md`, `cursor.com/docs/mcp/install-links.md`, `code.visualstudio.com/docs/copilot/customization/mcp-servers`, `code.visualstudio.com/docs/agents/reference/mcp-configuration` e `code.claude.com/docs/en/mcp.md`. Nenhuma divergência em relação à spec.
- **Tela `/conectar` (`src/rslapp/desktop/pages/connect_page.py`), rota em `app.py` e link no cabeçalho (`pages/__init__.py`):**
  - Item "Conectar IA" no cabeçalho entre "Histórico" e "Configurações".
  - Seis cartões (Claude Desktop, Cursor, VS Code (Copilot), Claude Code, Outras IAs e ChatGPT) com confirmação antes de gravar no Claude Desktop, exibição da entrada atual quando aponta para outra instalação e botões "Copiar".
- **Guia de hospedagem (`docs/hospedagem.md`):** acrescentada a subseção "Distribuir o app aos pesquisadores" dentro de "Para instituições de ensino".
- **Testes:** 9 testes em `tests/desktop/test_connect.py` (sem NiceGUI) e 2 testes de página em `tests_desktop/test_connect_page.py` (além da verificação da rota `/conectar` em `tests_desktop/test_app.py`).
- **Revisão do Claude (2026-11-16):** gates passaram na worktree (`tests_desktop` 21; suíte principal 703 passaram e 1 pulado no 3.10; ruff limpo). Conferido: a gravação preserva as outras chaves e servidores, faz a cópia `.bak` antes, cria a pasta do Claude se faltar, e nenhuma chave entra em nenhuma saída. Dois achados, que viraram itens da 12-05:
  - o caso `pip` aponta para `rslapp` sem argumentos, que não lê o `desktop.json` (a correção da spec chegou depois de o Gemini escrever);
  - no Windows, o `code --add-mcp '<JSON>'` perde as aspas no PowerShell 5.1 (testado com um `.cmd` que imita o `code.cmd`); o Prompt de Comando com `\"` funciona.

## Como testar

**Onde olhar primeiro (do mais arriscado para o menos arriscado):**

1. **`src/rslapp/desktop/connect.py` — `connect_claude_desktop()`, `disconnect_claude_desktop()` e `read_claude_desktop_config()`:** gravação no arquivo de outro programa (`claude_desktop_config.json`). Confira que um JSON corrompido levanta `ClaudeConfigError` sem tocar no arquivo nem criar `.bak`, que a cópia `.bak-<data e hora>` é criada na mesma pasta antes da escrita com `atomic_write_replace`, e que outras chaves de topo e outros servidores em `mcpServers` permanecem intactos.
2. **`src/rslapp/desktop/connect.py` — `mcp_env()` e `mcp_server_entry()`:** isolamento das chaves de API (FR-19, D-026, NFR-03). Confira que apenas `RSL_DESKTOP_CONFIG` pode entrar em `env` quando definido, e que nenhuma chave de `KEY_VARS` vai para o arquivo do Claude Desktop, para o link do Cursor ou para os blocos copiáveis.
3. **`src/rslapp/desktop/connect.py` — `open_cursor_link()` e `mcp_launch_command()`:** abertura do link `cursor://` sem `shell=True` e precedência de `APPIMAGE` antes de `sys.frozen` (para não gravar o caminho temporário `/tmp/.mount_...` do AppImage).

**Comandos para rodar:**

```bash
uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -c tests_desktop/pytest.ini tests_desktop -q
uv run --python 3.10 --extra dev python -m pytest -q
uv run --extra dev python -m ruff check .
```

**Na janela do app (`rslapp-desktop`):**

1. Abra o app e clique em **Conectar IA** no topo (entre **Histórico** e **Configurações**).
2. Veja os seis cartões, o estado atual do Claude Desktop e o comando/JSON de cada IA sem nenhuma chave exposta.
3. No cartão **Claude Desktop**, clique em **Conectar**, confira o trecho exibido na caixa de confirmação e clique em **Confirmar**: o estado muda para `conectado`, aparece o aviso *"Feche e abra o Claude Desktop para ele ver o RSL.app."* e a pasta `%APPDATA%\Claude` passa a ter a cópia `claude_desktop_config.json.bak-<data e hora>`.
