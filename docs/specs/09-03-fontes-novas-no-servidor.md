# PubMed e Europe PMC no servidor

**Fase:** 9 · Versão 1.2 · **Situação:** para testar

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

Liguei os conectores `pubmed` e `europe_pmc` ao servidor MCP e suas ferramentas, preservando o comportamento para quem não solicitar as fontes novas (D-020):
- **Ferramentas MCP:** `search_works` e `repeat_search` passam a aceitar `pubmed` e `europe_pmc` em `sources`. Sem `sources`, continuam consultando exclusivamente as três fontes padrão (`openalex`, `crossref`, `semantic_scholar`).
- **`list_sources`:** lista as cinco fontes acadêmicas. `pubmed` e `europe_pmc` com `needs_key: false`, `configured: true`, `status: "ok"`. Chave `NCBI_API_KEY` opcional tratada sem expor seu valor. Docstring orienta sobre as bases de saúde e ciências da vida.
- **Bloqueio em `find_work` e `get_related_works`:** respondem `invalid_input: fonte não suportada nesta ferramenta: <nome>` se `pubmed` ou `europe_pmc` forem solicitadas, sem acionar fontes nem rede.
- **Deduplicação:** `SOURCE_PRECEDENCE` atualizada para `("openalex", "crossref", "semantic_scholar", "europe_pmc", "pubmed")`. Artigos com mesmo DOI unem `source_ids` e `citations` de todas as fontes mantendo os campos da fonte de maior prevalência.
- **Exportador CSV:** inclusão das três colunas no fim (`PubMed ID`, `Europe PMC ID`, `Citations Europe PMC`), preservando a ordem e integridade das 19 colunas originais do Scopus para o VOSviewer.
- **Prompt e orientações:** `render_plan_search` e a descrição de `search_works` orientam a inclusão de `pubmed` e `europe_pmc` quando o tema envolver saúde, medicina ou biologia. Exemplo adicionado em `deploy/.env.example`.
- **Modo HTTP:** o servidor `_build_http_mcp_server` mantém exatamente as 8 ferramentas registradas.

## Como testar

Onde olhar primeiro (pontos mais arriscados):
1. **Não-exposição de segredos e chaves de API:** rodar `pytest tests/test_server_new_sources.py -k test_d020_list_sources_lista_cinco_e_nao_vaza_ncbi_key` para conferir que `NCBI_API_KEY` não vaza em nenhuma serialização da resposta de `list_sources`.
2. **Exportação CSV e compatibilidade com VOSviewer:** rodar `pytest tests/exporters/test_csv.py -k test_d020_csv_tres_colunas_novas_no_fim_e_colunas_antigas_iguais` para certificar que as 19 primeiras colunas do Scopus permanecem intactas e as 3 novas ficam estritamente no final.
3. **Bloqueio de fontes não suportadas antes de chamadas de rede:** rodar `pytest tests/test_server_new_sources.py -k test_d020_find_work_e_get_related_works_recusam_fontes_novas`.

Para rodar a suíte completa de testes das fontes novas:
```bash
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/test_server_new_sources.py -v
```
Deve exibir 6 testes passando com sucesso.

**Revisão do Claude (2026-11-11, run `b20261111-144701` do Playmaker):** uma rodada (Gemini 3.8 Flash), aprovada pelo agente revisor e integrada com os gates refeitos pelo `board integrate`. Conferido:
- sem `sources`, a busca chama só as três fontes de antes;
- uma busca antiga repetida usa as mesmas três, e uma busca com `pubmed` repete com `pubmed`;
- `find_work` e `get_related_works` recusam as fontes novas antes de chamar qualquer fonte;
- a precedência está na ordem pedida, e Europe PMC mais PubMed sem DOI se juntam por título e ano, guardando os dois ids;
- as colunas antigas do CSV não mudaram;
- o servidor HTTP continua com 8 ferramentas.

Acompanhamentos, não bloqueiam:
- `sources/__init__.py` ganhou exportações fora do escopo (inofensivas);
- a recusa das fontes novas está duplicada em `server.py` e no miolo;
- as colunas de id do CSV (as antigas e as novas) não passam pela proteção contra fórmula;
- o teste `test_d020_modo_http_mantem_mesmas_ferramentas` conta 8 ferramentas e muda na 09-05;
- `list_sources` não usa `ncbi_key_configured`, porque a spec manda `configured: true` para o PubMed.

O Claude corrigiu uma linha do contrato que trocava o padrão de `sources` em `get_related_works`.
