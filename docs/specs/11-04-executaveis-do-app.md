# Executáveis do app para Windows e Linux

**Fase:** 11 · App desktop (2.0) · **Situação:** para testar

## O que faz

Monta o app desktop como executáveis pelo GitHub Actions (D-025) e documenta o app no README.

### Workflow `.github/workflows/desktop.yml`

- **Quando roda:** a cada tag `v*` e à mão (`workflow_dispatch`).
- **Windows** (`windows-latest`, Python 3.12):
  - instala o projeto com o extra `desktop` e o `pyinstaller`;
  - gera com `nicegui-pack --windowed --onedir --name RSL.app <ponto de entrada>`, com `--onedir` porque abre mais rápido que `--onefile`;
  - compacta a pasta em `RSL.app-<versão>-windows-x64.zip`.
- **Linux** (`ubuntu-22.04`, Python 3.12, a base mais antiga para o executável valer em mais sistemas):
  - instala o extra `desktop` **sem** a janela nativa: `nicegui`, sem o `[native]`, mais as dependências do `rslapp`;
  - o app detecta que não há janela e abre no navegador (11-01);
  - gera com `nicegui-pack --onedir --name RSL.app` e empacota como AppImage com o `appimagetool`, com o arquivo `.desktop` e um ícone simples em SVG ou PNG no repositório;
  - o resultado é `RSL.app-<versão>-linux-x86_64.AppImage`.
- **Destino:**
  - na tag, os dois arquivos vão para a release da tag com `gh release upload`. Se a release ainda não existe quando o job termina, ele a espera ou a cria como rascunho; escolha o caminho mais simples e explique na spec;
  - no `workflow_dispatch`, os dois ficam só como artifacts da execução.
- **Teste de fumaça:** em cada sistema, depois de gerar, roda o executável em modo de verificação por alguns segundos e confere que ele sobe.
  - Crie uma opção `--check` no `main()` que inicia, confirma que importou tudo e sai com código 0, sem abrir a janela.
  - O teste de fumaça chama essa opção.
- **Ações do GitHub:** use versões de ações que rodem em Node 24, como no `docker.yml`.

### README

Uma seção "App desktop", que explica:
- como baixar o `.zip` (Windows) ou o AppImage (Linux) na página de releases;
- que o Windows pode avisar que o app não é assinado, e como seguir;
- que no Linux o app abre no navegador;
- como instalar pelo `pip`: `pip install "rslapp[desktop]"` e `rslapp-desktop`, com Python 3.11+;
- que o app usa a mesma pasta de dados do servidor (as mesmas listas e o mesmo log) e onde ficam as chaves (D-026).

## O que não faz

- Não assina o executável do Windows (custa dinheiro; fica para quando houver motivo).
- Não monta para macOS.
- Não publica nada no PyPI.

## Pronto quando

- [ ] Uma execução manual (`workflow_dispatch`) gera os dois arquivos como artifacts, e o teste de fumaça passa nos dois sistemas
- [ ] Os gates normais passam (a opção `--check` tem teste em `tests/desktop`, sem o NiceGUI)
- [ ] README com a seção "App desktop"

## Vem de

FR-16, D-024, D-025, D-026.

## Antes de começar

- Leia a seção de empacotamento do NiceGUI 4: https://nicegui.io/documentation/section_configuration_deployment.
- Leia a página do `appimagetool`: https://github.com/AppImage/appimagetool.
- Leia o `docker.yml`, para seguir o estilo dos workflows.
- O teste do workflow é feito pelo Claude, que dispara o `workflow_dispatch` depois da integração. Quem escreve o código não precisa disparar.
- Tamanho esperado: cerca de 200 linhas. Um commit.

## Resultado da entrega

- **Modo de verificação `--check` e ponto de entrada (`src/rslapp/desktop/app.py` e `src/rslapp/desktop/__main__.py`):** implementados `build_parser()`, `parse_args()` (sem importar `nicegui`), `_ensure_stdio_streams()` (redireciona `sys.stdout` e `sys.stderr` para `os.devnull` quando são `None` no executável Windows gerado com `--windowed`, evitando falha de `sys.stdout.isatty()` no `uvicorn`) e `_run_check()`. Em `main(["--check"])`, o app carrega `desktop.json`, importa o núcleo, as fontes, o NiceGUI e as quatro páginas, registra as rotas e sai com código `0` sem chamar `ui.run`.
- **Testes de `--check` (`tests/desktop/test_check.py` e `tests_desktop/test_app.py`):** 3 testes em `tests/desktop/test_check.py` (rodando em Python 3.10 sem o `nicegui` instalado, validando `parse_args`, `main(["--check"])` com `register_pages` isolado e `_ensure_stdio_streams`) e 1 teste em `tests_desktop/test_app.py` (com o NiceGUI real em Python 3.12, validando que `main(["--check"])` registra as páginas reais e sai com `0` sem chamar `ui.run`).
- **Workflow `.github/workflows/desktop.yml` e arquivos de empacotamento (`packaging/rslapp.desktop`, `packaging/rslapp.png` e `packaging/rslapp.svg`):**
  - Dispara em tags `v*` e manualmente (`workflow_dispatch`), usando actions que rodam em Node 24 (`actions/checkout@v5`, `actions/setup-python@v6`, `actions/upload-artifact@v6` e `actions/download-artifact@v7`).
  - **Windows (`windows-latest`, Python 3.12):** instala `.[desktop]` e `pyinstaller`, empacota `src/rslapp/desktop/__main__.py` com `nicegui-pack --windowed --onedir --noconfirm --name RSL.app`, roda o teste de fumaça (`dist\RSL.app\RSL.app.exe --check` via `subprocess.run` para aguardar o processo GUI e conferir o código `0`) e compacta em `RSL.app-<versão>-windows-x64.zip`.
  - **Linux (`ubuntu-22.04`, Python 3.12):** instala `.`, `"nicegui>=4,<5"` (sem `[native]`, para abrir no navegador sem depender de WebKitGTK/PyGObject do sistema) e `pyinstaller`, empacota com `nicegui-pack --onedir --noconfirm --name RSL.app`, monta a `RSL.app.AppDir` com `packaging/rslapp.desktop`, `packaging/rslapp.png` (PNG 256×256 exigido pelo `appimagetool` para `.DirIcon`) e `AppRun`, gera `RSL.app-<versão>-linux-x86_64.AppImage` com `appimagetool --appimage-extract-and-run` e executa o teste de fumaça com `./RSL.app-<versão>-linux-x86_64.AppImage --appimage-extract-and-run --check` (sem exigir FUSE no runner).
  - **Escolha para envio à release nas tags (`publish-release`):** um terceiro job (`publish-release`, com `needs: [build-windows, build-linux]` e `if: startsWith(github.ref, 'refs/tags/v')`) baixa os dois artifacts e executa `gh release view "$TAG" >/dev/null 2>&1 || gh release create "$TAG" --draft --title "$TAG"` seguido de `gh release upload "$TAG" ... --clobber`. Centralizar em um único job dependente dos dois builds evita condição de corrida entre Windows e Linux ao criar a release e garante que nenhum arquivo seja anexado se o teste de fumaça falhar em uma das plataformas; em `workflow_dispatch`, o job é pulado e os arquivos ficam apenas como artifacts da execução.
- **Documentação (`README.md`):** adicionada a seção "App desktop" explicando o download do `.zip` (Windows, com orientação sobre o aviso do SmartScreen para executável não assinado) e do AppImage (Linux, abrindo no navegador em `127.0.0.1`), a instalação via `pip install "rslapp[desktop]"` e `rslapp-desktop` (Python 3.11+) e o compartilhamento da pasta de dados com o servidor MCP, mantendo as chaves fora dela em `desktop.json` (D-026).
- **Revisão do Claude (2026-11-15):** entregue em duas rodadas (a primeira caiu por falta de memória no computador). Gates: `tests_desktop` 19 passaram; 689 passaram e 1 pulado em 3.10 e 3.14; ruff limpo; `rslapp-desktop --check` sai com 0. Primeira execução manual do workflow ([43722651448](https://github.com/Erick-wilding675/RSL-MCP-APP/actions/runs/43722651448)): Linux passou, Windows falhou no passo da versão (aspas do `python -c` no `pwsh`); corrigido rodando o passo em `bash` (c25bbad). Segunda execução ([43723048965](https://github.com/Erick-wilding675/RSL-MCP-APP/actions/runs/43723048965)): os dois jobs passaram, com o teste de fumaça; artifacts: `.zip` do Windows (38 MB, 80 MB aberto) e AppImage (51 MB). Teste à mão do `.exe` baixado, no Windows 11, com pasta de dados temporária: a janela "RSL.app" abre, o app escuta só em `127.0.0.1:8000`, `/historico` responde 200, e fechar a janela encerra os dois processos. Falta: abrir o AppImage num Linux (opcional, passo 7 da 11-05).

### Onde olhar primeiro (por ordem de risco)

1. **Permissões, publicação na release e teste de fumaça no workflow (`.github/workflows/desktop.yml`):** os jobs de build (`build-windows` e `build-linux`) têm apenas `contents: read` e só publicam artifacts após o executável gerado retornar código `0` com `--check`; o job `publish-release` (`contents: write`) só roda em tags `v*` quando ambos os builds passam, usa `GITHUB_TOKEN` do próprio GitHub Actions e cria a release como `--draft` caso ainda não exista.
2. **Inicialização segura do executável Windows `--windowed` e modo `--check` (`src/rslapp/desktop/app.py` e `__main__.py`):** `_ensure_stdio_streams()` evita que `sys.stdout`/`sys.stderr` nulos no subsistema GUI do Windows derrubem a configuração de log do `uvicorn`, `freeze_support()` roda antes de `parse_args()` e `--check` valida importações e registro de rotas sem iniciar servidor nem abrir janela.
3. **Empacotamento AppImage sem janela nativa no Linux (`.github/workflows/desktop.yml` e `packaging/rslapp.desktop`):** instala `nicegui>=4,<5` sem `[native]` (acionando o recuo para navegador em `127.0.0.1`), normaliza finais de linha LF em `rslapp.desktop`, usa ícone PNG 256×256 compatível com a validação de `.DirIcon` do `appimagetool` e executa o AppImage com `--appimage-extract-and-run --check`.

## Como testar

1. **Testes do app desktop com NiceGUI 4 (Python 3.12):**
   ```powershell
   uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -c tests_desktop/pytest.ini tests_desktop -q
   ```
   Deve passar com `19 passed`.

2. **Suíte principal sem NiceGUI, incluindo `tests/desktop/test_check.py` (Python 3.10):**
   ```powershell
   uv run --python 3.10 --extra dev python -m pytest -q
   ```
   Deve passar com `689 passed, 1 skipped`.

3. **Lint (Ruff):**
   ```powershell
   uv run --extra dev python -m ruff check .
   ```
   Deve exibir `All checks passed!`.

4. **Verificação direta da opção `--check` pelo ponto de entrada:**
   ```powershell
   uv run --python 3.12 --extra desktop python src/rslapp/desktop/__main__.py --check
   ```
   Deve encerrar imediatamente com código de saída `0`, sem abrir janela nem iniciar servidor.

5. **Execução manual do workflow (`workflow_dispatch`, pelo Claude após a integração):**
   Disparar `.github/workflows/desktop.yml` via `workflow_dispatch`; conferir que `build-windows` e `build-linux` passam no passo `Executar teste de fumaça (--check)`, geram os artifacts `RSL.app-<versão>-windows-x64.zip` e `RSL.app-<versão>-linux-x86_64.AppImage` e que `publish-release` fica pulado fora de tags `v*`.
