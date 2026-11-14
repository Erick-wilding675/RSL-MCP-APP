# Telas Buscar e Lista

**Fase:** 11 · App desktop (2.0) · **Situação:** a fazer

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

- [ ] `tests_desktop`, com o fixture `user` e um `DesktopService` falso:
  - uma busca preenchida navega para a lista e mostra os títulos;
  - a string vazia avisa sem chamar o serviço;
  - um `RSLError` mostra a mensagem;
  - as fontes pagas sem chave aparecem desabilitadas;
  - a lista incompleta mostra o aviso com a fonte que falhou;
  - o botão de exportar chama o serviço com o formato certo e mostra o caminho;
  - um `list_id` inexistente mostra "lista não encontrada".
- [ ] Passam os gates normais (3.10, 3.12 e 3.14) e o `tests_desktop` no 3.12.
- [ ] Teste à mão com fontes reais: `rslapp-desktop`, uma busca de 20 artigos no OpenAlex e um RIS exportado que aparece na pasta.

## Vem de

FR-16, FR-08, FR-06, FR-12, D-022, D-025.

## Antes de começar

- Leia a 11-01 e o código que ela deixou em `src/rslapp/desktop/`.
- Leia `ui.table`, `ui.number` e `ui.notify` na documentação do NiceGUI 4: https://nicegui.io/documentation. Na 4.0, `table.pagination` passou a mostrar os controles.
- Para injetar o serviço falso, siga o padrão que a 11-01 deixou. Se não houver um, faça `register_pages(service=...)` aceitar o serviço como parâmetro, com padrão `DesktopService()`.
- Tamanho esperado: cerca de 300 linhas com os testes. Um commit.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
