# Base do app desktop

**Fase:** 11 · App desktop (2.0) · **Situação:** para testar

## O que faz

Cria o esqueleto do app desktop (D-024, D-025, D-026). Ele usa o mesmo núcleo, a mesma pasta de dados (`~/RSL.app` ou `RSL_DATA_DIR`) e o mesmo log do servidor. Ao fim desta tarefa, `rslapp-desktop` abre uma janela com a navegação entre as quatro telas, e cada tela traz só o título e um texto curto. O conteúdo das telas vem na 11-02 e na 11-03.

### Pacote

- Um extra novo no `pyproject.toml`: `desktop = ["nicegui[native]>=4,<5"]`. O NiceGUI 4 exige Python 3.11+, e o servidor continua aceitando 3.10. Não mude `requires-python`.
- Outro extra novo, só para os testes do app: `desktop-dev = ["pytest-asyncio"]`.
- Um comando novo em `[project.scripts]`: `rslapp-desktop = "rslapp.desktop.app:main"`.
- O sdist passa a levar também a pasta `tests_desktop`.

### Módulos (em `src/rslapp/desktop/`)

Só `app.py` e `pages/*.py` importam o `nicegui`. `settings.py` e `service.py` não podem importá-lo, nem direta nem indiretamente, porque são testados no Python 3.10 sem o NiceGUI instalado.

1. **`settings.py`** (D-026, FR-18, NFR-03)
   - `settings_path() -> Path`:
     - `RSL_DESKTOP_CONFIG`, se estiver definida e não vazia;
     - senão, no Windows, `%APPDATA%\RSL.app\desktop.json`;
     - senão, `$XDG_CONFIG_HOME/rslapp/desktop.json`, e sem `XDG_CONFIG_HOME`, `~/.config/rslapp/desktop.json`.
   - `KEY_VARS`: a tupla `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `NCBI_API_KEY`, `SCOPUS_API_KEY`, `SCOPUS_INSTTOKEN`, `WOS_STARTER_API_KEY`.
   - `OTHER_VARS`: a tupla `RSL_CONTACT_EMAIL`, `RSL_DATA_DIR`, `RSL_EXPORT_DIR`.
   - `DesktopSettings`: uma dataclass com `values: dict[str, str]`, só com as variáveis acima. O `__repr__` mascara os valores de `KEY_VARS` (`"***"`).
   - `load_settings() -> DesktopSettings`:
     - se o arquivo não existe, devolve vazio;
     - se o JSON está ilegível ou não é um objeto, devolve vazio e não levanta exceção;
     - ignora nomes fora das duas tuplas e valores que não sejam texto.
   - `save_settings(settings)`:
     - cria a pasta e grava com `atomic_write_replace` (`rslapp.store._atomic`);
     - fora do Windows, deixa o arquivo com permissão `0o600`;
     - não grava nomes desconhecidos e não grava valores vazios, que equivalem a apagar.
   - `apply_to_environ(settings, environ=os.environ) -> list[str]`:
     - para cada nome com valor, põe no `environ` só se ele **não estiver já definido e não vazio** ali;
     - devolve os nomes aplicados;
     - nunca registra valores em log nem em print.
2. **`service.py`** (FR-16, FR-17)
   - `DesktopService`, sem estado global, com os métodos abaixo. Cada um lê a configuração na hora (`rslapp.config.load()`) e monta o `Store` como o servidor faz no stdio: `Store(cfg.data_dir, cfg.cache_days)`. Confira em `server.py` como o stdio monta o store e repita o mesmo.
     - `list_sources() -> list[dict]`: o mesmo formato do `list_sources` do servidor no stdio, com as 7 fontes.
     - `async search(query: str, sources: list[str] | None, max_results: int, include_peer_review: bool) -> dict`: chama `run_search`, com `request_summary="app desktop"`.
     - `get_list(list_id: str) -> dict`
     - `export(list_id: str, export_format: str) -> dict`: chama `run_export` com `cfg.export_dir` e devolve o caminho do arquivo.
     - `list_searches() -> list[dict]`
     - `async repeat(search_id: str) -> dict`: chama `run_repeat`.
     - `log_path() -> Path`
   - Os erros do núcleo (`RSLError`) sobem como estão. A tela decide como mostrá-los.
3. **Fontes num lugar só:** a montagem das fontes passa para `rslapp/sources/__init__.py`, como `build_sources(include_paid: bool) -> list[Source]`, com as 5 abertas e, se `include_paid`, Scopus e Web of Science.
   - O `_build_sources()` do servidor continua existindo, porque há testes que o trocam com `monkeypatch`, e passa a chamar `build_sources(include_paid=not _is_http_mode())`.
   - O serviço usa `build_sources(include_paid=True)`.
   - Faça o mesmo com o `list_sources`: a lógica sai de `server.py` para uma função compartilhada que os dois chamam, sem mudar a resposta do servidor.
4. **`app.py`** (D-024, D-025)
   - `register_pages()`:
     - registra as páginas `/` (Buscar), `/lista/{list_id}` (Lista), `/historico` (Histórico) e `/configuracoes` (Configurações);
     - cada página fica no seu módulo em `src/rslapp/desktop/pages/` (`search.py`, `list_view.py`, `history.py`, `settings_page.py`), com uma função `build(service)`;
     - todas usam um cabeçalho comum com o nome "RSL.app" e os links Buscar, Histórico e Configurações.
   - `main()`:
     1. `load_settings()` e depois `apply_to_environ()`;
     2. `register_pages()`;
     3. `ui.run(...)` com `host="127.0.0.1"` (**obrigatório**: o app nunca escuta na rede), `reload=False`, `title="RSL.app"`, `native=True` e `window_size=(1200, 800)`;
     4. se a janela nativa não puder abrir (falta o `pywebview` ou o backend do sistema), roda com `native=False` e `show=True`, abrindo o navegador padrão no endereço local.
   - Siga a seção de empacotamento da documentação do NiceGUI: `freeze_support()` e as opções de `app.native` fora do bloco `if __name__ ...`.
   - `src/rslapp/desktop/__main__.py` chama `main()`, para `python -m rslapp.desktop` funcionar.

### Testes

- `tests/desktop/` roda no gate normal (3.10, 3.12, 3.14) e não importa o `nicegui`:
  - `settings`: caminho por plataforma e por `RSL_DESKTOP_CONFIG`, arquivo ilegível, nomes desconhecidos, valor vazio apaga, `0o600` (pule no Windows), `apply_to_environ` não sobrescreve, `repr` mascarado;
  - `service`: com fontes falsas, troque `build_sources` e use `RSL_DATA_DIR` num `tmp_path`;
  - um teste que importa `rslapp.desktop.settings` e `rslapp.desktop.service` e confere que `"nicegui"` não entrou em `sys.modules`.
- `tests_desktop/` só roda com o extra `desktop`, no Python 3.11+. Ela tem o próprio `pytest.ini`, com `asyncio_mode = auto`, `main_file =` vazio e `addopts = -p nicegui.testing.user_plugin`.
  - Use o fixture `user` (sem navegador): `register_pages()` e depois `user.open('/')`, `/historico` e `/configuracoes`; cada tela mostra o título e o cabeçalho com os três links.
  - Comando: `uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -c tests_desktop/pytest.ini tests_desktop`.

## O que não faz

- Não faz o conteúdo das telas (11-02, 11-03).
- Não monta executáveis (11-04).
- Não muda nenhuma resposta do servidor MCP.

## Pronto quando

- [ ] `uv run --python 3.12 --extra desktop rslapp-desktop` abre a janela com o cabeçalho e as quatro rotas
- [ ] O app escuta só em `127.0.0.1` (teste ou conferência no código: `host="127.0.0.1"` explícito)
- [ ] Testes de `settings` e `service` passam em 3.10, 3.12 e 3.14, sem o NiceGUI instalado
- [ ] `tests_desktop` passa no 3.12
- [ ] Os testes do servidor continuam passando sem mudança de comportamento (`_build_sources` e `list_sources`)
- [ ] ruff limpo

## Vem de

FR-16, FR-17, FR-18, NFR-03, D-024, D-025, D-026. São os ids que o código leva como âncoras.

## Antes de começar

- **Leia a documentação do NiceGUI 4** antes de escrever. Os exemplos que você conhece são da 1.x a 3.x, e a 4.0 mudou coisas:
  - https://nicegui.io/documentation/section_configuration_deployment (modo nativo, `ui.run`, empacotamento);
  - https://nicegui.io/documentation/section_testing (fixture `user`);
  - https://nicegui.io/documentation/section_pages_routing (`@ui.page`, páginas com parâmetro);
  - as notas da 4.0.0 em https://github.com/zauberzeug/nicegui/releases/tag/v4.0.0. Pontos da 4.0: Python 3.11+, o `ui.input` vazio vale `''`, os ids viraram `ng-12` e o `httpx` não vem mais junto (o RSL.app já declara o dele).
- Leia `src/rslapp/server.py` (`list_sources`, `_build_sources`, `_build_tool_store` e o caminho do stdio), `src/rslapp/config.py`, `src/rslapp/store/__init__.py` e `src/rslapp/store/_atomic.py`.
- Tamanho esperado: cerca de 400 linhas com os testes. Faça um commit para a refatoração das fontes (`build_sources`, sem mudar o comportamento) e outro para o app.

## Resultado da entrega

- **Refatoração das fontes (`src/rslapp/sources/__init__.py` e `src/rslapp/server.py`):** centralizados `build_sources(include_paid: bool)` e `list_sources_info(include_paid: bool, cfg: Config | None)` em `rslapp.sources`. Em `server.py`, `_build_sources()` e `list_sources()` delegam para as funções compartilhadas mantendo a assinatura, o docstring e o suporte a `monkeypatch`.
- **Configuração persistente do app (`src/rslapp/desktop/settings.py`):** implementados `settings_path()`, `KEY_VARS`, `OTHER_VARS`, `DesktopSettings` (com `__repr__` mascarando `KEY_VARS` como `"***"`), `load_settings()`, `save_settings()` (gravação atômica via `atomic_write_replace` e permissão `0o600` fora do Windows) e `apply_to_environ()` (sem sobrescrever variáveis já definidas e não vazias no ambiente e sem imprimir valores).
- **Serviço sobre o núcleo (`src/rslapp/desktop/service.py`):** implementado `DesktopService` sem estado global e sem importar o `nicegui`, expondo `list_sources`, `search` (`request_summary="app desktop"`), `get_list`, `export`, `list_searches`, `repeat` e `log_path`, propagando `RSLError` diretamente.
- **Janela, roteamento e páginas (`src/rslapp/desktop/app.py`, `__main__.py` e `pages/*.py`):** implementados `register_pages()` (rotas `/`, `/lista/{list_id}`, `/historico` e `/configuracoes`, cabeçalho comum com `RSL.app` e os três links) e `main()` com `freeze_support()`, `host="127.0.0.1"`, `reload=False`, `title="RSL.app"`, `native=True`, `window_size=(1200, 800)` e recuo automático para `native=False` e `show=True` (sem `window_size`, pois no NiceGUI 4 `window_size` força `native=True` em `ui.run`).
- **Pacote e testes (`pyproject.toml`, `tests/desktop/` e `tests_desktop/`):** adicionados os extras `desktop` e `desktop-dev`, o script `rslapp-desktop`, a pasta `tests_desktop` no `sdist`, 11 testes em `tests/desktop/` (sem `nicegui`, rodando em 3.10, 3.12 e 3.14) e 2 testes em `tests_desktop/` com o fixture `user` do NiceGUI 4.
- **Observação sobre a spec (`pyproject.toml`):** na declaração do extra `desktop`, foi usado `"nicegui[native]>=4,<5; python_version >= '3.11'"` porque o `uv lock` resolve todos os extras contra `requires-python = ">=3.10"` e falha na resolução universal para Python 3.10 sem o marcador `python_version >= '3.11'`.

### Onde olhar primeiro (por ordem de risco)

1. **Gravação e proteção de chaves de API (`src/rslapp/desktop/settings.py`):** `DesktopSettings.__repr__` mascara todos os nomes de `KEY_VARS` com `"***"`; `save_settings` ignora chaves desconhecidas, descarta valores vazios, grava com `atomic_write_replace` fora da pasta de dados e aplica `0o600` fora do Windows; `apply_to_environ` nunca sobrescreve variáveis já definidas no ambiente nem escreve valores em log ou stdout.
2. **Escuta restrita ao loopback e recuo de janela nativa (`src/rslapp/desktop/app.py`):** `main()` passa `host="127.0.0.1"` explicitamente tanto no modo nativo quanto no fallback para navegador (`native=False, show=True`), omitting `window_size` no fallback para evitar que o NiceGUI 4 reative `native=True`.
3. **Isolamento de importação do NiceGUI (`src/rslapp/desktop/settings.py` e `service.py`):** nenhum módulo fora de `app.py` e `pages/*.py` importa `nicegui`, garantindo que o pacote base e a suíte principal rodem em Python 3.10 sem a dependência instalada.

## Como testar

1. **Suíte principal sem NiceGUI (Python 3.10 e 3.14):**
   ```powershell
   uv run --python 3.10 --extra dev python -m pytest -q
   uv run --python 3.14 --extra dev python -m pytest -q
   ```
   Deve passar com `685 passed, 1 skipped` (os 675 testes anteriores mais os 11 de `tests/desktop/`, sendo o teste de `0o600` pulado no Windows).

2. **Suíte do app desktop com o fixture `user` do NiceGUI 4 (Python 3.12):**
   ```powershell
   uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -c tests_desktop/pytest.ini tests_desktop -q
   ```
   Deve passar com `2 passed`.

3. **Lint (Ruff):**
   ```powershell
   uv run --extra dev python -m ruff check .
   ```
   Deve exibir `All checks passed!`.

4. **Abertura manual da janela do app:**
   ```powershell
   uv run --python 3.12 --extra desktop rslapp-desktop
   ```
   Deve abrir a janela `RSL.app` (1200×800) escutando apenas em `127.0.0.1`, com o cabeçalho contendo `RSL.app` e os links **Buscar**, **Histórico** e **Configurações** navegando entre as telas.

**Revisão do Claude (2026-11-14):** duas rodadas com o Gemini 4 Argon pelo `agy`. A primeira deixou no código de produção dois desvios que só existiam para os testes (`_ORIG_BUILD_SOURCES` com `_resolve_sources` e `ui.run is _ORIG_UI_RUN`), tirados na segunda. Conferido à mão no Windows 11: `rslapp-desktop` abre a janela nativa "RSL.app", escuta só em `127.0.0.1:8000`, e ao fechar a janela o processo encerra, sem reabrir no navegador (o NiceGUI sai por `os._exit`). Gates: 685 testes em 3.10 e 3.14, `tests_desktop` no 3.12, ruff limpo.
