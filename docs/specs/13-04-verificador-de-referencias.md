# Verificador de referências contra alucinação (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** integrada

## O que faz

Permite ao pesquisador e à IA verificar se uma lista de referências acadêmicas é real ou se foi inventada/alucinada por um modelo de linguagem (ideia 5.1, D-030, FR-21). O verificador consulta as bases abertas globais (Crossref e OpenAlex) e classifica cada referência em uma de três categorias.

### 1. Categorias de resultado

Para cada referência avaliada:
- **`verified` (confirmada):** o artigo foi encontrado nas bases (por DOI ou por título) e os metadados principais (título, ano e primeiro autor) são consistentes.
- **`divergent` (dados divergentes):** o artigo foi encontrado (pelo DOI ou título coincidente), mas há divergências nos dados fornecidos (ex.: ano citado diferente do ano de publicação oficial, autor inventado ou periódico incorreto). O resultado detalha quais campos divergiram.
- **`not_found` (não encontrada):** nenhuma correspondência foi encontrada após busca por DOI e busca difusa por título/autores nas bases consultadas. Indica forte suspeita de alucinação de IA.

### 2. Módulo do núcleo (`src/rslapp/core/verify.py`)

- **Entrada:** aceita referências em múltiplos formatos comuns:
  - Texto corrido com referências separadas por linhas em branco ou numeração (ABNT, APA, Vancouver, etc.);
  - Bloco em formato BibTeX (`@article{...}`, `@inproceedings{...}`, etc.);
  - Lista de DOIs ou strings de citações.
- **Extração inteligente:**
  - Extrai DOI quando presente (`10.\d{4,9}/[-._;()/:A-Za-z0-9]+`);
  - Extrai ano aproximado quando presente (`(19\d\d|20\d\d)`);
  - Limpa e normaliza títulos para comparação difusa usando `normalize_title` de `dedup.py` e `difflib.SequenceMatcher`.
- **Estratégia de consulta:**
  - Se tem DOI: busca direta por DOI no OpenAlex e no Crossref (`find_by_doi`).
  - Se não tem DOI: busca textual no Crossref (`query.bibliographic` ou `query.title`) e no OpenAlex (`search`).
  - Calcula a similaridade entre o título citado e o título registrado:
    - Similaridade $\ge 0.85$: considerado o mesmo trabalho.
    - Se o ano difere em mais de 1 ano ou o sobrenome do primeiro autor não consta no registro oficial: marca como `divergent` e explica a divergência.
    - Caso contrário: marca como `verified`.
    - Se a melhor similaridade for $< 0.70$: marca como `not_found`.

### 3. Ferramenta MCP (`src/rslapp/server.py`)

- Nova ferramenta: `verify_references(references: list[str] | str, request_summary: str = "")`
- Anotação `readOnlyHint=True` (ferramenta de consulta/inspeção sem efeitos colaterais).
- Resposta estruturada com totais (`total`, `verified`, `divergent`, `not_found`) e lista detalhada `results` com status, DOI oficial, título oficial, autores oficiais, ano e justificativa/divergência.

### 4. Tela no App Desktop (`src/rslapp/desktop/pages/verify_view.py`)

- Rota `/verificar` integrada à casca (`render_shell`) e adicionada à barra lateral (`NAV_ITEMS` com ícone `fact_check` e nome "Verificar").
- Layout baseado nos componentes padronizados da 13-01 e 13-02:
  - `section_card` com campo de texto amplo para colar referências ou BibTeX;
  - Botão "Verificar referências" com barra de progresso durante o processamento;
  - Faixa de resumo com `metric_card` (Total, Confirmadas, Divergentes, Não encontradas);
  - Tabela interativa com `status_badge` semântico (`ok` verde para confirmadas, `warning` amarelo para divergências, `error` vermelho para não encontradas);
  - Tooltips detalhando a divergência ou o link direto para o DOI oficial.

## O que não faz

- Não consulta bases proprietárias pagas (Scopus/WoS), mantendo a verificação 100% gratuita e aberta para qualquer usuário.
- Não substitui a leitura humana nem a revisão metodológica formal.
- Não altera arquivos salvos de buscas nem listas existentes.

## Para instituições

As bibliotecas universitárias e comitês de ética em pesquisa podem recomendar e utilizar o verificador como triagem rápida de trabalhos acadêmicos (TCCs, dissertações e artigos), combatendo o uso descuidado ou fraudulento de referências inventadas por IA generativa.

## Pronto quando

- [x] Módulo `src/rslapp/core/verify.py` com extração, normalização, consulta assíncrona e cálculo de similaridade/divergência.
- [x] Testes de unidade em `tests/core/test_verify.py` cobrindo referências reais, com pequenas divergências e completamente inventadas.
- [x] Ferramenta MCP `verify_references` registrada em `src/rslapp/server.py` com anotação `readOnlyHint=True` e testes em `tests/test_server_verify.py`.
- [x] Tela `/verificar` no app desktop em `src/rslapp/desktop/pages/verify_view.py` com testes em `tests_desktop/test_verify_page.py`.
- [x] Os gates passam: testes do desktop, testes do núcleo em 3.10 e 3.14, e linter Ruff limpo.

## Vem de

D-002, D-006, D-029, D-030 (Ideia 5.1), D-031, FR-21.

## Antes de começar

- Criar a branch de tarefa `fase13/13-04-verificador-referencias` a partir de `integracao-2.2`.
- Um commit por requisito/fatia (núcleo, MCP, desktop).
- Seguir as regras de acessibilidade e modo escuro do tema (sem variantes `dark:` de Tailwind).

## Resultado da entrega

Entregue em três fatias limpas com testes cobrindo todas as camadas:

1. **Núcleo (`rslapp.core.verify`, commit `895ff1d`):**
   - Implementado parser flexível `parse_references` capaz de extrair metadados estruturados de blocos BibTeX (`@article{...}` etc.), texto livre no padrão ABNT/APA/Vancouver ou listas de dicionários.
   - Algoritmo de verificação assíncrona `run_verify_references` e `_evaluate_match` com extração e normalização de DOI, busca difusa por título e tolerância de 1 ano para preprints.
   - Classificação precisa em `verified`, `divergent` e `not_found`, reportando detalhamento de divergências de ano ou autor.
   - Testes de unidade em `tests/core/test_verify.py` (3 testes cobrindo todos os cenários de correspondência e alucinação).

2. **Servidor MCP (`rslapp.server`, commit `211e00a`):**
   - Ferramenta MCP `@mcp.tool(annotations=_READ_ONLY_ANNOTATIONS)` adicionada como `verify_references(references: list[Any] | str, request_summary: str = "") -> dict[str, Any]`.
   - Registrada no modo stdio e no modo Streamable HTTP (`_build_http_mcp_server`).
   - Testes de integração em `tests/test_server_verify.py` e atualização de testes existentes de listagem de ferramentas (`test_server.py`, `test_server_http.py`, `test_server_new_sources.py`).

3. **Interface Desktop (`rslapp.desktop`, commit `071a3bb`):**
   - Adicionado item "Verificar" (`fact_check`, `/verificar`) à lista de navegação lateral `NAV_ITEMS`.
   - Adicionada fachada `verify_references` em `DesktopService`.
   - Criado componente reaproveitável `metric_card` em `rslapp.desktop.components`.
   - Criada a tela `verify_view.py` com área de entrada para referências/BibTeX, feedback de carregamento com `ui.linear_progress`, resumo métrico e tabela Quasar com filtros e badges semânticos de status (`ok` verde, `warning` amarelo, `error` vermelho).
   - Suíte de testes desktop em `tests_desktop/test_verify_page.py` e atualização em `tests_desktop/test_shell.py` (50 testes desktop passando).

## Como testar

**Onde olhar primeiro:**

1. **No servidor MCP:**
   - Executar: `uv run --python 3.10 --extra dev python -m pytest tests/test_server_verify.py -v`
   - Deve executar e passar com referências BibTeX e texto livre divididas em confirmadas e não encontradas.
2. **Na interface desktop:**
   - Executar: `uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -c tests_desktop/pytest.ini tests_desktop/test_verify_page.py -v`
   - Todos os 4 cenários de teste da tela passam (abertura, aviso de campo vazio, exibição de métricas e tabela de resultados, e tratamento de falhas).
3. **No aplicativo interativo:**
   - Rodar `uv run rslapp-desktop`
   - Clicar em **Verificar** no menu lateral esquerdo.
   - Colar referências conhecidas e clicar em **Verificar referências**. Conferir os cards de métricas e a tabela de resultados com os badges coloridos.
