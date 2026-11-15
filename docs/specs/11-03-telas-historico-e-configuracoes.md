# Telas Histórico e Configurações

**Fase:** 11 · App desktop (2.0) · **Situação:** para testar

## O que faz

Preenche as outras duas telas do app. Elas usam só o `DesktopService` e o `settings.py` da 11-01.

### Histórico (`pages/history.py`, FR-17)

- **Tabela das buscas:** mostra as buscas de `service.list_searches()`, da mais recente para a mais antiga.
  - **Colunas:** data, string (cortada em 80 caracteres, com o texto inteiro no tooltip), fontes, número de artigos e se a lista ficou incompleta.
  - **Ações de cada linha:**
    - **Ver lista:** navega para `/lista/{list_id}`.
    - **Repetir:** chama `await service.repeat(search_id)` com indicador de progresso e, ao terminar, navega para a lista nova (FR-11).
- **Botão "Abrir log":** abre o `log.md` (`service.log_path()`) no programa padrão do sistema. Usa o mesmo jeito de abrir da 11-02, sem `shell=True`. Se o log ainda não existe, avisa.
- **Histórico vazio:** mostra "nenhuma busca ainda" e um link para Buscar.
- **Formato dos dados:** confira em `Store.list_searches()` o formato real de cada busca antes de escrever as colunas.

### Configurações (`pages/settings_page.py`, FR-18, D-026, NFR-03)

- **Chaves:** um campo para cada variável de `KEY_VARS`, com nome legível e um link para onde criar a chave.
  - Os links:
    - OpenAlex: https://openalex.org/settings/api;
    - Semantic Scholar: https://www.semanticscholar.org/product/api#api-key-form;
    - NCBI: página de configurações da conta do NCBI;
    - Scopus: https://dev.elsevier.com/apikey/manage;
    - Web of Science Starter: https://developer.clarivate.com/apis/wos-starter.
  - Os campos são do tipo senha (`password=True`, `password_toggle_button=True`).
  - **Valor nunca mostrado:** a tela nunca preenche o campo com o valor salvo. Ela mostra só "configurada" ou "não configurada" e deixa o campo vazio. Digitar um valor troca a chave, e um botão "Remover" ao lado apaga a chave salva.
  - **Chave vinda do sistema:** se a variável já veio do ambiente do sistema, e não do arquivo, a tela diz "definida no sistema; o valor do sistema vale".
  - Scopus e Web of Science mostram a nota de D-023: só funcionam com a assinatura de quem usa ou da instituição.
- **Outros campos:** e-mail de contato (`RSL_CONTACT_EMAIL`), pasta de dados (`RSL_DATA_DIR`) e pasta das exportações (`RSL_EXPORT_DIR`).
  - Os campos de pasta mostram o valor atual de `rslapp.config.load()`.
  - A pasta de dados avisa que trocá-la faz o app e o Claude Desktop olharem pastas diferentes, a menos que o Claude Desktop use a mesma.
- **Salvar:**
  1. grava com `save_settings`;
  2. aplica no processo, para a próxima busca já usar os valores novos. Aqui o valor da tela substitui o anterior, exceto a variável que veio do sistema: guarde no início do `main()` quais nomes vieram do sistema e não os toque;
  3. mostra "salvo" e o caminho do arquivo de configuração.
- **Segurança:** nenhuma chave aparece em `ui.notify`, em log, em print, em exceção mostrada ou no HTML da página depois de salva.

## O que não faz

- Não usa o cofre do sistema (D-026).
- Não muda o servidor nem o núcleo.

## Pronto quando

- [x] `tests_desktop`, com o fixture `user` e um serviço falso:
  - o histórico lista as buscas, e "Repetir" chama o serviço e navega;
  - com o histórico vazio, aparece a mensagem;
  - em Configurações, salvar uma chave grava no arquivo (`RSL_DESKTOP_CONFIG` num `tmp_path`) e aplica no ambiente;
  - **depois de salvar, o valor da chave não aparece em nenhum elemento da página** (procure o texto da chave na página e confira que não está);
  - "Remover" apaga a chave;
  - uma variável vinda do sistema não é sobrescrita e aparece como "definida no sistema".
- [x] Os gates normais e o `tests_desktop` passam.

## Vem de

FR-17, FR-18, FR-11, FR-13, NFR-03, D-023, D-026.

## Antes de começar

- Leia a 11-01 e a 11-02 e o código que elas deixaram em `src/rslapp/desktop/`.
- Leia `ui.input` (com `password`) e `ui.table` (com slots ou botões por linha) na documentação do NiceGUI 4. Na 4.0, o `ui.input` vazio vale `''`.
- Tamanho esperado: cerca de 350 linhas com os testes. Um commit por tela.

## Resultado da entrega

- **Tela Histórico (`src/rslapp/desktop/pages/history.py`):** implementada em `/historico` listando as buscas de `service.list_searches()` da mais recente para a mais antiga, com colunas para data, string de busca (cortada em 80 caracteres com a string completa no tooltip `q-tooltip`), fontes consultadas, número de artigos (reconciliado com a lista salva quando existente) e indicação de lista incompleta (`"Sim"`/`"Não"`). Inclui ações por linha **"Ver lista"** (navega para `/lista/{list_id}`) e **"Repetir"** (chama `await service.repeat(search_id)` com `ui.spinner` e navega para a nova lista, FR-11), botão **"Abrir log"** (abre `service.log_path()` via `os.startfile` no Windows e `subprocess.run(["xdg-open", ...], check=False)` no Linux sem `shell=True`, avisando quando `log.md` não existe) e estado vazio com `"nenhuma busca ainda"` e link para `/`.
- **Proteção de variáveis do sistema (`src/rslapp/desktop/settings.py` e `src/rslapp/desktop/app.py`):** adicionadas `capture_system_env_vars()`, `get_system_env_vars()`, `set_app_env_var()` e `remove_app_env_var()`. No início de `main()`, antes de `apply_to_environ(settings)`, `capture_system_env_vars()` registra o `frozenset` de variáveis de `KEY_VARS` e `OTHER_VARS` que já vieram do ambiente do sistema para que a tela as identifique e nunca as sobrescreva nem remova.
- **Tela Configurações (`src/rslapp/desktop/pages/settings_page.py`):** implementada em `/configuracoes` com um campo de senha (`password=True`, `password_toggle_button=True`, sempre inicializado vazio e limpo imediatamente ao salvar) para cada variável de `KEY_VARS`, acompanhado do link para criação da chave (OpenAlex, Semantic Scholar, página de configurações da conta do NCBI, Scopus/Elsevier e Web of Science Starter), indicador de situação (`"configurada"`, `"não configurada"` ou `"definida no sistema; o valor do sistema vale"`), botão **"Remover"** (apaga do arquivo e de `os.environ`, exceto se veio do sistema) e nota de D-023 para Scopus e Web of Science. Inclui os campos `RSL_CONTACT_EMAIL`, `RSL_DATA_DIR` (com o aviso sobre o Claude Desktop) e `RSL_EXPORT_DIR` preenchidos com os valores atuais de `rslapp.config.load()`, e o botão **"Salvar"** que grava com `save_settings`, atualiza `os.environ` (exceto variáveis do sistema) e exibe `"salvo"` com o caminho do arquivo.
- **Testes (`tests_desktop/test_history_and_settings.py` e `tests/desktop/test_settings.py`):** adicionados 7 testes cobrindo a listagem e repetição no Histórico, histórico vazio, abertura de `log.md` sem `shell=True`, gravação e aplicação de chaves em Configurações com verificação de que o texto da chave não aparece em nenhum elemento/propriedade/notificação da página após salvar ou reabrir, remoção de chave salva e preservação de variáveis vindas do sistema.
- **Revisão do Claude (2026-11-15):** entregue em duas rodadas (a primeira caiu por erro de rede depois do Histórico). Conferido que o campo de chave nunca recebe o valor salvo, que nenhuma mensagem leva o valor e que as variáveis do sistema não são tocadas. Gates: `tests_desktop` 18 passaram; 686 passaram e 1 pulado em 3.10 e 3.14; ruff limpo. Dívidas aceitas, para uma tarefa futura: (1) `settings.py` tem caminhos diferentes para `os.environ` e para um ambiente de teste (`environ is os.environ`); o comportamento erra para o lado seguro (não sobrescrever), mas o código pode ficar mais simples; (2) o Histórico lê a lista inteira de cada busca para contar os artigos, o que fica lento com centenas de buscas.

### Onde olhar primeiro (por ordem de risco)

1. **Não exposição de chaves de API e preservação de variáveis do sistema (`src/rslapp/desktop/pages/settings_page.py` e `src/rslapp/desktop/settings.py`):** os inputs de `KEY_VARS` nunca recebem o valor salvo (`value=""`) e são limpos imediatamente no clique de Salvar (`key_inputs[var_name].value = ""`); nenhuma chave vai para `ui.notify`, logs, stdout ou mensagens de exceção; e variáveis capturadas do sistema (`get_system_env_vars()`) nunca são tocadas por `on_save`, `set_app_env_var` ou `remove_app_env_var`.
2. **Gravação do arquivo de configuração e atualização do ambiente do processo (`src/rslapp/desktop/pages/settings_page.py`, `on_save` e `_make_remove_handler`):** o salvamento persiste atomicamente em `desktop.json` via `save_settings` e reflete imediatamente os novos valores (ou remoções) em `os.environ` para que a próxima busca na mesma sessão já utilize as chaves, o e-mail e as pastas atualizadas.
3. **Abertura de `log.md` no programa padrão sem `shell=True` (`src/rslapp/desktop/pages/history.py`, `open_log_in_default_app`):** usa `os.startfile` no Windows e `subprocess.run(["xdg-open", str(log_file)], check=False)` no Linux com lista de argumentos, verificando antes se o arquivo existe.

## Como testar

1. **Testes do app desktop com o fixture `user` do NiceGUI 4 (Python 3.12):**
   ```powershell
   uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -c tests_desktop/pytest.ini tests_desktop -q
   ```
   Deve passar com `18 passed`.

2. **Suíte principal sem NiceGUI (Python 3.10):**
   ```powershell
   uv run --python 3.10 --extra dev python -m pytest -q
   ```
   Deve passar com `686 passed, 1 skipped`.

3. **Lint (Ruff):**
   ```powershell
   uv run --extra dev python -m ruff check .
   ```
   Deve exibir `All checks passed!`.
