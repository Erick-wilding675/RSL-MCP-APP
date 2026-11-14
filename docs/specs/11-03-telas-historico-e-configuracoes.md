# Telas Histórico e Configurações

**Fase:** 11 · App desktop (2.0) · **Situação:** a fazer

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

- [ ] `tests_desktop`, com o fixture `user` e um serviço falso:
  - o histórico lista as buscas, e "Repetir" chama o serviço e navega;
  - com o histórico vazio, aparece a mensagem;
  - em Configurações, salvar uma chave grava no arquivo (`RSL_DESKTOP_CONFIG` num `tmp_path`) e aplica no ambiente;
  - **depois de salvar, o valor da chave não aparece em nenhum elemento da página** (procure o texto da chave na página e confira que não está);
  - "Remover" apaga a chave;
  - uma variável vinda do sistema não é sobrescrita e aparece como "definida no sistema".
- [ ] Os gates normais e o `tests_desktop` passam.

## Vem de

FR-17, FR-18, FR-11, FR-13, NFR-03, D-023, D-026.

## Antes de começar

- Leia a 11-01 e a 11-02 e o código que elas deixaram em `src/rslapp/desktop/`.
- Leia `ui.input` (com `password`) e `ui.table` (com slots ou botões por linha) na documentação do NiceGUI 4. Na 4.0, o `ui.input` vazio vale `''`.
- Tamanho esperado: cerca de 350 linhas com os testes. Um commit por tela.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
