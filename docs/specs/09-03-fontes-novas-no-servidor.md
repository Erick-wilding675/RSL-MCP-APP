# PubMed e Europe PMC no servidor

**Fase:** 9 · Versão 1.2 · **Situação:** a fazer

## O que faz

Liga os dois conectores novos (09-01 e 09-02) ao servidor, sem mudar o que já existe para quem não pedir as fontes novas (D-020).

- **Nomes:** `pubmed` e `europe_pmc` passam a valer em `sources` de `search_works` e `repeat_search`. Sem `sources`, a busca continua nas três de hoje (`openalex`, `crossref`, `semantic_scholar`); as fontes novas só entram quando pedidas.
- **`list_sources`:** passa a listar as cinco. `pubmed` diz `needs_key: false`, `configured: true`, `status: "ok"`. A chave `NCBI_API_KEY` é opcional, como a da Semantic Scholar. `europe_pmc` diz o mesmo e não tem chave. A descrição da ferramenta diz que as duas são bases de saúde e ciências da vida e que entram quando pedidas.
- **`find_work` e `get_related_works`:** não usam as fontes novas. Se alguém pedir `pubmed` ou `europe_pmc` nelas, a ferramenta responde `invalid_input` com a mensagem `fonte não suportada nesta ferramenta: <nome>`, antes de chamar qualquer fonte.
- **Deduplicação:** `SOURCE_PRECEDENCE` em `core/dedup.py` passa a `("openalex", "crossref", "semantic_scholar", "europe_pmc", "pubmed")`. Os artigos das fontes novas se juntam aos das outras pelo DOI ou pelo título e ano, como já acontece. A junção guarda os `source_ids` e as `citations` de todas as fontes.
- **CSV:** três colunas novas **no fim** (`PubMed ID`, `Europe PMC ID`, `Citations Europe PMC`). As colunas de hoje não mudam de nome nem de ordem, porque o VOSviewer lê o CSV no formato do Scopus.
- **Configuração:** a leitura de `NCBI_API_KEY` (opcional) entrou em `config.py` na 09-01. Aqui ela só é usada por `list_sources`, sem mostrar o valor.
- **Orientação à IA:** o prompt `plan_search` e a descrição de `search_works` passam a dizer que, quando o tema for de saúde, medicina ou biologia, vale pedir também `pubmed` e `europe_pmc` em `sources`.
- **Guia e exemplo de configuração:** `deploy/.env.example` ganha `NCBI_API_KEY=` vazio, com um comentário curto. O README e o guia são do Claude.

## O que não faz

- Não muda as respostas das ferramentas para quem não pede as fontes novas.
- Não acrescenta as fontes novas a `find_work` nem a `get_related_works`: isso fica para depois, se o uso pedir.
- Não muda o contrato por conta própria: o Claude atualiza `docs/interface-contract.md`.

## Pronto quando

- [ ] Teste: `search_works` com `sources=["pubmed", "europe_pmc"]` (fontes falsas) grava a lista com o estado das duas, e sem `sources` consulta só as três de antes
- [ ] Teste: um artigo que vem do OpenAlex e do PubMed com o mesmo DOI vira um só, com `source_ids` das duas fontes e os campos da fonte de maior precedência
- [ ] Teste: `repeat_search` de uma busca feita com `pubmed` repete com `pubmed`
- [ ] Teste: `find_work` e `get_related_works` com `sources=["pubmed"]` respondem `invalid_input`, sem chamar fonte nenhuma
- [ ] Teste: `list_sources` lista as cinco, e com `NCBI_API_KEY` definida o valor não aparece em lugar nenhum da resposta
- [ ] Teste: o CSV tem as três colunas novas no fim, e as colunas antigas continuam iguais
- [ ] Teste: no modo HTTP, as ferramentas continuam as mesmas (a lista do `_build_http_mcp_server` não muda)
- [ ] Os três gates passam

## Vem de

D-020, FR-01, FR-03, FR-04, FR-06, FR-07, NFR-03. São os ids que o código leva como âncoras.

## Antes de começar

09-01 e 09-02 integradas. Ler `src/rslapp/server.py` (`SourceName`, `list_sources`, `_build_sources`, `search_works`, `find_work`, `get_related_works`), `src/rslapp/core/search.py` (`_select_sources`), `src/rslapp/core/find.py`, `src/rslapp/core/related.py`, `src/rslapp/core/dedup.py`, `src/rslapp/exporters/csv.py`, `src/rslapp/config.py` e `src/rslapp/prompts.py`.

Cerca de 300 linhas. Um commit para o servidor e a configuração, outro para a deduplicação e o CSV, outro para o prompt, com D-020 no comentário e no nome dos testes.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
