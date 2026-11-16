# Tela "Conectar IA"

**Fase:** 12 · Conectar a IA ao app (2.1) · **Situação:** a fazer

## O que faz

Uma tela nova no app, "Conectar IA" (rota `/conectar`, no menu entre Histórico e Configurações), que liga a IA da pessoa ao RSL.app do computador dela (D-028, FR-19). Depois disso, as buscas que a IA faz aparecem no Histórico do app, porque usam a mesma pasta.

### O comando que as IAs vão rodar

Uma função sem o NiceGUI, `mcp_launch_command() -> tuple[str, list[str]]`, em `src/rslapp/desktop/connect.py`, decide o que a IA executa:

- **No executável empacotado** (`sys.frozen`):
  - o caminho absoluto do próprio executável (`sys.executable`), com `["--mcp"]`;
  - o teste de fumaça da 12-01 provou, em 2026-11-15, que o `RSL.app.exe` sem console recebe o stdio, então o `rslapp-mcp.exe` não é preciso.
- **No AppImage:** o caminho do arquivo `.AppImage` (variável de ambiente `APPIMAGE`), com `["--mcp"]`, e não o caminho temporário de dentro dele.
- **Instalado pelo `pip`:** o caminho absoluto do comando `rslapp` do mesmo ambiente (ao lado de `sys.executable`), sem argumentos. Se não achar, usa `sys.executable` com `["-m", "rslapp"]`, desde que `python -m rslapp` funcione; confira e, se não funcionar, ajuste.
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

- [ ] A tela mostra os seis cartões e o estado do Claude Desktop
- [ ] "Conectar" e "Desconectar" no Claude Desktop preservam o resto do arquivo e deixam a cópia `.bak`
- [ ] Testes sem o NiceGUI em `tests/desktop` para `connect.py`:
  - o comando em cada caso: executável, AppImage e pip;
  - juntar com um arquivo existente e com outros servidores;
  - arquivo ilegível;
  - remover;
  - o link do Cursor decodificado de volta ao mesmo JSON;
  - o JSON do `code --add-mcp` e o comando do Claude Code, com e sem `RSL_DESKTOP_CONFIG`, e com caminho que tem espaço;
  - nenhuma chave na saída, mesmo com chaves no ambiente.
- [ ] Teste da tela em `tests_desktop`
- [ ] Os gates passam
- [ ] O guia de hospedagem tem a seção "Distribuir o app aos pesquisadores"

## Vem de

FR-19, D-026, D-028, D-029.

## Antes de começar

- 12-01 integrada.
- Leia `src/rslapp/desktop/pages/settings_page.py` e `history.py`, para seguir o estilo, e `src/rslapp/store/_atomic.py`.
- Leia as páginas oficiais citadas acima, por inteiro, antes de escrever cada cartão (T-001).
- Tamanho esperado: cerca de 350 linhas com os testes. Divida em dois commits: `connect.py` com os testes, depois a tela.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
