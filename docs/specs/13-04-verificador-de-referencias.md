# Verificador de referências contra alucinação (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** a fazer

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

- [ ] Módulo `src/rslapp/core/verify.py` com extração, normalização, consulta assíncrona e cálculo de similaridade/divergência.
- [ ] Testes de unidade em `tests/core/test_verify.py` cobrindo referências reais, com pequenas divergências e completamente inventadas.
- [ ] Ferramenta MCP `verify_references` registrada em `src/rslapp/server.py` com anotação `readOnlyHint=True` e testes em `tests/test_server_verify.py`.
- [ ] Tela `/verificar` no app desktop em `src/rslapp/desktop/pages/verify_view.py` com testes em `tests_desktop/test_verify_page.py`.
- [ ] Os gates passam: testes do desktop, testes do núcleo em 3.10 e 3.14, e linter Ruff limpo.

## Vem de

D-002, D-006, D-029, D-030 (Ideia 5.1), D-031, FR-21.

## Antes de começar

- Criar a branch de tarefa `fase13/13-04-verificador-referencias` a partir de `integracao-2.2`.
- Um commit por requisito/fatia (núcleo, MCP, desktop).
- Seguir as regras de acessibilidade e modo escuro do tema (sem variantes `dark:` de Tailwind).

## Resultado da entrega

(a preencher)

## Como testar

**Onde olhar primeiro:**

1. No MCP: chamar `verify_references` com uma lista contendo uma referência real (ex: "Vaswani et al., Attention is all you need, 2017") e uma referência deliberadamente inventada. A primeira deve sair como `verified` e a segunda como `not_found`.
2. No app desktop: abrir `/verificar`, colar um bloco de texto com referências e conferir os selos e contadores na tabela de resultados.
