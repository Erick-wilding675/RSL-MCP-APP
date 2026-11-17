# Retratações nas listas (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** integrada

## O que faz

Identifica automaticamente artigos acadêmicos que foram formalmente retratados (retractions) ou que receberam expressões de preocupação (expressions of concern) pelas editoras e comunidades científicas, marcando-os nas buscas, nas listas salvas e nas exportações (ideia 5.2, FR-22, D-032).

### 1. Identificação nas fontes acadêmicas

- **OpenAlex:**
  - Extrai o atributo nativo `is_retracted: bool` de cada objeto de trabalho (OpenAlex integra a base Retraction Watch via Crossref).
- **Crossref:**
  - Analisa o campo `updated-by` retornado na API de works.
  - Detecta se há atualização do tipo `retraction` ou `expression-of-concern` (comprovando a procedência do Retraction Watch ou da própria editora).
  - Extrai os detalhes da retratação (tipo, rótulo, data e DOI do comunicado de retratação, se houver).
- **Europe PMC e PubMed:**
  - Europe PMC: verifica `isRetracted == "y"` ou publicações do tipo retratação.
  - PubMed: verifica se `pubtype` contém `Retracted Publication` ou `Retraction of Publication`.

### 2. Modelo de dados e unificação (`rslapp.core`)

- No modelo `Work` (`src/rslapp/core/models.py`):
  - Adiciona `is_retracted: bool = False` e `retraction_details: dict[str, Any] | None = None`.
  - Serialização (`to_dict`) e desserialização (`from_dict`) com valores padrão, garantindo total retrocompatibilidade com listas salvas em versões anteriores.
- Na deduplicação (`dedup.py`) e fusão de listas (`merge.py`):
  - Ao fundir registros duplicados de fontes diferentes, se qualquer fonte sinalizar que o artigo foi retratado, o registro unificado preserva `is_retracted = True` e os detalhes da retratação.

### 3. Exportações (`rslapp.exporters`)

- **RIS (`ris.py`):**
  - Para artigos retratados, adiciona a tag de nota `N1  - [AVISO] Artigo retratado ou com expressao de preocupacao oficial` (legível no VOSviewer, Zotero, Mendeley e EndNote).
- **BibTeX (`bibtex.py`):**
  - Para artigos retratados, inclui o campo `note = {AVISO: Artigo retratado ou com expressao de preocupacao}`.
- **CSV / TSV (`csv_tsv.py`):**
  - Inclui coluna `is_retracted` (`Sim` / `Não`) e `retraction_details`.

### 4. Interface Desktop (`rslapp.desktop.pages.list_view`)

- **Tabela de artigos (`ui.table`):**
  - Quando um artigo estiver retratado, exibe um badge de destaque vermelho (`<q-badge color="negative">RETRATADO</q-badge>`) ao lado do título, com tooltip orientando o pesquisador.
- **Resumo métrico:**
  - Se a lista contiver artigos retratados, exibe um cartão métrico de alerta na faixa superior (`metric_card(retracted_count, "Artigos retratados", color_class="text-negative")`).
- **Ficha / Visualização do artigo:**
  - Alerta em destaque (`.rsl-warning-box`) explicando que o trabalho foi retratado, com a fonte da informação.

## O que não faz

- Não exclui ou oculta artigos retratados da lista (na metodologia científica e no diagrama PRISMA, o pesquisador precisa saber que o artigo foi localizado pela busca e registrar sua condição de retratação na triagem).
- Não faz download de PDFs ou comunicados na íntegra.

## Para instituições

Bibliotecas universitárias, núcleos de evidências em saúde e comitês de integridade acadêmica contam com alerta imediato nas buscas para barrar a inclusão acidental de artigos com fraudes, erros metodológicos graves ou dados falsificados em revisões sistemáticas e diretrizes institucionais.

## Pronto quando

- [x] Campo `is_retracted` e `retraction_details` adicionados a `Work` em `src/rslapp/core/models.py` com retrocompatibilidade total.
- [x] Conectores OpenAlex e Crossref (e Europe PMC/PubMed) extraindo os dados de retratação.
- [x] Deduplicação (`dedup.py`) e unificação (`merge.py`) preservando a sinalização de retratação entre fontes.
- [x] Exportadores (RIS, BibTeX, CSV/TSV) incluindo aviso explícito de retratação.
- [x] Tela de Lista no app desktop (`list_view.py`) exibindo badge de retratação, cartão métrico de alerta quando houver retratados e aviso detalhado.
- [x] Testes do núcleo e desktop cobrindo artigos normais e artigos retratados.
- [x] Todos os gates passam (testes do núcleo em 3.10 e 3.14, testes do desktop, linter Ruff limpo).

## Vem de

D-004, D-030 (Ideia 5.2), D-032, FR-22.

## Antes de começar

- Criar a branch de tarefa `fase13/13-05-retratacoes-nas-listas` a partir de `integracao-2.2`.
- Entregar em fatias ordenadas: (1) Core models, conectores e dedup; (2) Exportadores; (3) Interface Desktop.
- Seguir as regras de acessibilidade e tema do projeto (sem variantes `dark:` de Tailwind).

## Resultado da entrega

Entregue em três fatias limpas e testadas em todas as camadas:

1. **Núcleo, Conectores e Deduplicação (commit `e040664`):**
   - Campos `is_retracted: bool = False` e `retraction_details: dict[str, Any] | None = None` adicionados ao modelo `Work` em `src/rslapp/core/models.py`, com suporte retrocompatível para dicionários legados em `from_dict`.
   - Conector `openalex.py`: extração direta de `is_retracted: bool` (parceria OpenAlex + Retraction Watch via Crossref).
   - Conector `crossref.py`: extração a partir do campo `updated-by` (detectando tipos `retraction` e `expression-of-concern` da base Retraction Watch / Crossmark).
   - Conectores `europe_pmc.py` e `pubmed.py`: detecção via `isRetracted` e `PublicationType` de retratação.
   - Deduplicação (`dedup.py` / `merge.py`): fusão preserva `is_retracted = True` e os metadados de retratação se qualquer uma das fontes o sinalizar.
   - Resumo de busca (`search.py` / `views.py`): inclui `is_retracted: True` em respostas MCP quando o artigo for retratado.
   - Testes de unidade em `tests/core/test_retractions.py` (6 testes passando).

2. **Exportadores (commit `4d9f9f1`):**
   - RIS (`ris.py`): adiciona tag `N1  - [AVISO] Artigo retratado ou com expressao de preocupacao oficial (Fonte: ...)` aos registros retratados.
   - BibTeX (`bibtex.py`): inclui aviso de retratação no campo `note = {...}`.
   - CSV Scopus (`csv.py`): sinaliza no `Document Type` como `Retracted (tipo)` ou `Retracted` mantendo as 26 colunas padronizadas do Scopus para compatibilidade total com o VOSviewer.
   - Testes em `tests/exporters/test_retractions_export.py` (83 testes de exportadores passando).

3. **Interface Desktop (commit `d53d568`):**
   - Roteamento do app desktop (`app.py`): desacoplamento do serviço ativo em variável de escopo para roteamento dinâmico sem conflitos de fechamento de escopo no NiceGUI.
   - Tela Lista (`list_view.py`):
     - Resumo métrico: adicionado cartão de alerta `card-retracted` em vermelho na faixa superior (`Artigo(s) retratado(s)`) quando a lista possuir artigos retratados.
     - Tabela de artigos: inserido badge de destaque `<q-badge color="negative">RETRATADO</q-badge>` ao lado do título com tooltip orientativo.
   - Testes da interface desktop em `tests_desktop/test_retractions_ui.py` (51 testes desktop passando).

## Como testar

**Onde olhar primeiro:**

1. **No núcleo:**
   - Executar: `uv run --python 3.10 --extra dev python -m pytest tests/core/test_retractions.py -v`
   - Deve executar e passar com cobertura de desserialização, conectores e fusão de duplicatas.
2. **Nas exportações:**
   - Executar: `uv run --python 3.10 --extra dev python -m pytest tests/exporters/test_retractions_export.py -v`
   - Verifica avisos de retratação em RIS (`N1`), BibTeX (`note`) e CSV (`Document Type`).
3. **No app desktop:**
   - Executar: `uv run --python 3.12 --extra desktop --extra desktop-dev --extra dev python -m pytest -c tests_desktop/pytest.ini tests_desktop/test_retractions_ui.py -v`
   - Ambos os cenários (lista com artigos retratados e lista sem artigos retratados) passam.
4. **No aplicativo interativo:**
   - Executar `uv run rslapp-desktop`.
   - Abrir uma lista contendo artigos com retratação conhecida.
   - Conferir o cartão métrico vermelho de alerta no topo e o badge vermelho `RETRATADO` com tooltip na tabela.
