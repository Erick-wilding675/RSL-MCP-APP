# Telas Buscar e Lista

**Fase:** 11 · App desktop (2.0) · **Situação:** para testar

## O que faz

Preenche duas telas do app (FR-16): a tela **Buscar** (`/`) roda uma busca, e a tela **Lista** (`/lista/{list_id}`) mostra e exporta o resultado. As duas usam só o `DesktopService` da 11-01.

### Buscar (`pages/search.py`)

- **Campos do formulário:**
  - **String de busca:** um `ui.textarea` obrigatório. A ajuda abaixo dele diz que a string vai como está para cada base, e que o app não usa IA.
  - **Fontes:** um checkbox para cada fonte de `service.list_sources()`.
    - Marcadas por padrão: OpenAlex, Crossref e Semantic Scholar (o padrão do servidor).
    - PubMed e Europe PMC aparecem desmarcadas, com a nota "saúde e ciências da vida".
    - Scopus e Web of Science aparecem desmarcadas. Sem chave (`status == "missing_key"`), ficam desabilitadas, com o texto "configure a chave em Configurações" e um link para a tela.
  - **Quantidade:** um `ui.number` de 1 a 1000, padrão 100. Use os limites `MIN_MAX_RESULTS` e `MAX_MAX_RESULTS` do núcleo, sem copiar os números.
  - **Pareceres de revisão:** um checkbox "Incluir pareceres de revisão por pares", desmarcado (D-022).
- **Botão Buscar:**
  - Desabilita o formulário e mostra um indicador de progresso enquanto `await service.search(...)` roda. A interface não pode travar: a chamada é assíncrona.
  - Se der certo, navega para `/lista/{list_id}`.
  - Se a lista vier incompleta (fonte que falhou), a tela da lista mostra o aviso.
  - Se der `RSLError`, mostra `ui.notify` com a mensagem, em tipo negativo, e reabilita o formulário. A mensagem nunca leva o valor de uma chave (o núcleo já garante; não acrescente nada).
  - Com a string vazia, avisa sem chamar o serviço.

### Lista (`pages/list_view.py`)

- **Cabeçalho da lista:**
  - mostra a string, a data, o total de artigos e as fontes com o número de resultados de cada uma;
  - se a lista for incompleta, mostra um aviso visível com cada fonte que falhou e o motivo (FR-08).
- **Tabela (`ui.table`):**
  - uma linha por artigo, com as colunas título, autores (os três primeiros e "et al."), ano, periódico, DOI (link para `https://doi.org/...`) e fontes;
  - tem paginação (padrão de 25 por página), busca por texto na tabela e ordenação por ano e título;
  - os dados vêm de `service.get_list(list_id)`. Confira no `Store` e no `run_search` o formato real da lista gravada antes de escrever as colunas.
- **Exportação:** um botão para cada formato (RIS, CSV, BibTeX, JSON, DOIs).
  - O botão chama `service.export(list_id, formato)` e mostra `ui.notify` com o caminho do arquivo gravado.
  - Mostra também um botão "Abrir pasta", que abre a pasta das exportações no gerenciador de arquivos do sistema: `os.startfile` no Windows e `xdg-open` no Linux, por `subprocess` com lista de argumentos e nunca com `shell=True`.
  - Se o arquivo de exportação já existir, vale o que o núcleo já faz; não mude o núcleo.
- **Lista que não existe:** se o `list_id` não existe, mostra "lista não encontrada" e um link para Buscar.

## O que não faz

- Não faz referências e citações, não acha um artigo e não junta listas (fica para depois, D-025).
- Não muda o núcleo, os exportadores nem o servidor.

## Pronto quando

- [x] `tests_desktop`, com o fixture `user` e um `DesktopService` falso:
  - uma busca preenchida navega para a lista e mostra os títulos;
  - a string vazia avisa sem chamar o serviço;
  - um `RSLError` mostra a mensagem;
  - as fontes pagas sem chave aparecem desabilitadas;
  - a lista incompleta mostra o aviso com a fonte que falhou;
  - o botão de exportar chama o serviço com o formato certo e mostra o caminho;
  - um `list_id` inexistente mostra "lista não encontrada".
- [x] Passam os gates normais (3.10, 3.12 e 3.14) e o `tests_desktop` no 3.12.
- [x] Teste à mão com fontes reais: `rslapp-desktop`, uma busca de 20 artigos no OpenAlex e um RIS exportado que aparece na pasta.

## Vem de

FR-16, FR-08, FR-06, FR-12, D-022, D-025.

## Antes de começar

- Leia a 11-01 e o código que ela deixou em `src/rslapp/desktop/`.
- Leia `ui.table`, `ui.number` e `ui.notify` na documentação do NiceGUI 4: https://nicegui.io/documentation. Na 4.0, `table.pagination` passou a mostrar os controles.
- Para injetar o serviço falso, siga o padrão que a 11-01 deixou. Se não houver um, faça `register_pages(service=...)` aceitar o serviço como parâmetro, com padrão `DesktopService()`.
- Tamanho esperado: cerca de 300 linhas com os testes. Um commit.

## Resultado da entrega

- **Tela Buscar (`src/rslapp/desktop/pages/search.py`):** implementado o formulário completo em `/` com `ui.textarea` obrigatório e texto de ajuda informando que a string vai diretamente para cada base sem uso de IA; checkboxes dinâmicos a partir de `service.list_sources()` com OpenAlex, Crossref e Semantic Scholar marcados por padrão (`DEFAULT_SEARCH_SOURCES`), nota `"saúde e ciências da vida"` em PubMed e Europe PMC, e Scopus e Web of Science desmarcados e desabilitados quando `status == "missing_key"` (com o aviso `"configure a chave em Configurações"` e link para `/configuracoes`); `ui.number` usando `MIN_MAX_RESULTS`, `MAX_MAX_RESULTS` e `DEFAULT_MAX_RESULTS` do núcleo; checkbox `"Incluir pareceres de revisão por pares"` desmarcado por padrão (D-022); e execução assíncrona com desabilitação do formulário, indicador de progresso (`ui.spinner`), navegação para `/lista/{list_id}` em caso de sucesso e `ui.notify(..., type="negative")` em `RSLError` ou string vazia.
- **Tela Lista (`src/rslapp/desktop/pages/list_view.py`):** implementada a visualização em `/lista/{list_id}` com cabeçalho exibindo string de busca, data, total de artigos e contagem por fonte (resolvendo metadados da lista e da busca correspondente via `service.list_searches()` quando gravada pelo `Store`); cartão de aviso visível quando a lista está incompleta (`status == "incomplete"` ou fonte com status diferente de `"ok"`), listando cada fonte que falhou e o motivo (FR-08); botões de exportação para `RIS`, `CSV`, `BibTeX`, `JSON` e `DOIs` chamando `service.export(list_id, formato)` e exibindo o caminho do arquivo gravado via `ui.notify`; botão `"Abrir pasta"` abrindo o diretório de exportações com `os.startfile` no Windows e `subprocess.run(["xdg-open", ...], check=False)` no Linux (nunca `shell=True`); `ui.table` com paginação de 25 itens por página (`PAGE_SIZE`), busca por texto vinculada a `table.filter`, ordenação por título e ano, autores formatados com os três primeiros e `"et al."`, e coluna DOI renderizada como link externo para `https://doi.org/...`; e tratamento de `list_id` inexistente exibindo `"lista não encontrada"` e link para `/`.
- **Testes (`tests_desktop/test_search_and_list.py`):** adicionados 8 testes cobrindo busca preenchida e navegação com conferência das linhas da tabela, bloqueio de string vazia sem chamar o serviço, exibição de `RSLError` e reabilitação do formulário, fontes pagas desabilitadas sem chave, aviso de lista incompleta com fonte e motivo, exportação nos formatos com notificação do caminho, abertura da pasta no Windows e no Linux sem `shell=True`, e `list_id` inexistente.

### Onde olhar primeiro (por ordem de risco)

1. **Exportação de arquivos e abertura da pasta no sistema (`src/rslapp/desktop/pages/list_view.py`, `open_folder_in_file_manager` e `_make_export_handler`):** a abertura da pasta das exportações usa `os.startfile` no Windows e `subprocess.run(["xdg-open", str(folder)], check=False)` no Linux com lista de argumentos e sem `shell=True`, evitando injeção de comandos por caminho de diretório.
2. **Exibição de erros e bloqueio de fontes pagas sem chave (`src/rslapp/desktop/pages/search.py`, `on_search`):** os erros `RSLError` do núcleo têm apenas `err.message` repassado a `ui.notify(..., type="negative")` (sem interpolar variáveis de ambiente ou chaves), e as bases pagas (`scopus` e `web_of_science`) ficam desabilitadas quando `status == "missing_key"`.
3. **Formatação de dados de autores e fontes para `ui.table` (`src/rslapp/desktop/pages/list_view.py`, `_format_authors`, `_format_work_sources` e `_resolve_search_metadata`):** converte listas de autores (`dict` no `Store` ou `str`) e dicionários `source_ids` em strings planas (os três primeiros autores + `"et al."`) antes de popular `table.rows`, evitando listas em células do Quasar `QTable` e reconciliando os dados de `lists/l-NNNN.json` com `searches/s-NNNN.json`.

## Como testar

1. **Testes das telas Buscar e Lista com o fixture `user` do NiceGUI 4 (Python 3.12):**
   ```powershell
   uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -c tests_desktop/pytest.ini tests_desktop -q
   ```
   Deve passar com `10 passed`.

2. **Suíte principal (Python 3.10, 3.12 e 3.14):**
   ```powershell
   uv run --python 3.10 --extra dev python -m pytest -q
   uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -q
   uv run --python 3.14 --extra dev python -m pytest -q
   ```
   Deve passar com `685 passed, 1 skipped` nas três versões.

3. **Lint (Ruff):**
   ```powershell
   uv run --extra dev python -m ruff check .
   ```
   Deve exibir `All checks passed!`.

4. **Teste real com OpenAlex (20 artigos) e exportação RIS:**
   ```powershell
   lore secrets run --env prod -- uv run --python 3.12 --extra desktop rslapp-desktop
   ```
   Na janela do app (`/`), digite uma string de busca (ex.: `bibliometrics VOSviewer`), mantenha apenas **OpenAlex** marcada, ajuste **Quantidade** para `20` e clique em **Buscar**. A tela deve navegar para `/lista/l-0001` exibindo 20 artigos na tabela; ao clicar em **RIS**, uma notificação mostra o caminho do arquivo `l-0001.ris` gravado na pasta de exportações, e **Abrir pasta** abre o diretório no Explorer.
