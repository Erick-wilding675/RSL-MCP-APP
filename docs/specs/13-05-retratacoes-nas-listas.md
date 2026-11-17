# Retratações nas listas (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** a fazer

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

- [ ] Campo `is_retracted` e `retraction_details` adicionados a `Work` em `src/rslapp/core/models.py` com retrocompatibilidade total.
- [ ] Conectores OpenAlex e Crossref (e Europe PMC/PubMed) extraindo os dados de retratação.
- [ ] Deduplicação (`dedup.py`) e unificação (`merge.py`) preservando a sinalização de retratação entre fontes.
- [ ] Exportadores (RIS, BibTeX, CSV/TSV) incluindo aviso explícito de retratação.
- [ ] Tela de Lista no app desktop (`list_view.py`) exibindo badge de retratação, cartão métrico de alerta quando houver retratados e aviso detalhado.
- [ ] Testes do núcleo e desktop cobrindo artigos normais e artigos retratados.
- [ ] Todos os gates passam (testes do núcleo em 3.10 e 3.14, testes do desktop, linter Ruff limpo).

## Vem de

D-004, D-030 (Ideia 5.2), D-032, FR-22.

## Antes de começar

- Criar a branch de tarefa `fase13/13-05-retratacoes-nas-listas` a partir de `integracao-2.2`.
- Entregar em fatias ordenadas: (1) Core models, conectores e dedup; (2) Exportadores; (3) Interface Desktop.
- Seguir as regras de acessibilidade e tema do projeto (sem variantes `dark:` de Tailwind).

## Resultado da entrega

(a preencher)

## Como testar

**Onde olhar primeiro:**

1. **No núcleo:** buscar ou consultar um artigo com retratação conhecida (ex: no Crossref com `updated-by` do Retraction Watch, ou no OpenAlex com `is_retracted: true`). O objeto `Work` resultante deve ter `is_retracted == True`.
2. **Nas exportações:** exportar uma lista contendo artigo retratado em RIS, BibTeX e CSV/TSV e verificar se o aviso de retratação consta no arquivo gerado.
3. **No app desktop:** abrir uma lista com artigo retratado em `/lista/{list_id}` e conferir o badge `RETRATADO` e o cartão métrico de alerta.
