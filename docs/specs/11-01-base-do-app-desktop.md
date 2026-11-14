# Base do app desktop

**Fase:** 11 · App desktop (2.0) · **Situação:** a fazer

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

(preenche quem entrega)

## Como testar

(preenche quem entrega)
