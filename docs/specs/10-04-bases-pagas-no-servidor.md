# Scopus e Web of Science no servidor

**Fase:** 10 · Bases pagas e filtros (1.3) · **Situação:** a fazer

## O que faz

Liga os conectores da 10-02 e da 10-03 ao servidor, com as regras da D-023: as bases pagas só funcionam com as chaves de quem usa, e só no modo stdio.

- **Nomes:** `scopus` e `web_of_science` passam a valer em `sources` de `search_works` e `repeat_search`. Sem `sources`, a busca continua nas três de sempre. As bases pagas só entram quando pedidas.
- **`list_sources` no stdio:** lista as sete.
  - `scopus` e `web_of_science` dizem `needs_key: true`, e `configured` e `status` (`ok` ou `missing_key`) conforme `SCOPUS_API_KEY` e `WOS_STARTER_API_KEY`.
  - A descrição da ferramenta diz que as duas são bases pagas e que só funcionam com a chave e a assinatura do próprio usuário ou da instituição dele.
  - Nenhum valor de chave aparece na resposta.
- **No modo hospedado:**
  - `list_sources` não lista as duas;
  - `search_works` e `repeat_search` com `scopus` ou `web_of_science` respondem `invalid_input`, antes de chamar qualquer fonte, com a mensagem: `scopus e web_of_science só funcionam no RSL.app instalado no seu computador, com a sua chave e o acesso da sua instituição (D-023)`;
  - `_build_sources` não cria os dois conectores.
- **`find_work` e `get_related_works`:** recusam `scopus` e `web_of_science` com `invalid_input` (`fonte não suportada nesta ferramenta: <nome>`), como fazem com `pubmed`.
- **Deduplicação:** `SOURCE_PRECEDENCE` passa a `("openalex", "crossref", "semantic_scholar", "scopus", "web_of_science", "europe_pmc", "pubmed")`.
- **CSV:** quatro colunas novas **no fim**: `Scopus EID`, `Web of Science UID`, `Citations Scopus` e `Citations Web of Science`. As colunas de hoje não mudam.
- **Crédito à fonte:** a entrada do `log.md` de uma busca que trouxe dados de uma base paga termina com uma linha de crédito: "Dados do Scopus (Elsevier)" e/ou "Source: Clarivate Analytics (Web of Science)".
- **Pareceres (10-01):** valem para as duas fontes novas como para as outras: um artigo com `type` `peer-review` sai quando `include_peer_review` é falso.
- **Limpeza da 10-01** (achados da revisão):
  - em `core/search.py`, tirar o `try/except TypeError` em volta de `cache_query` e `search`. `include_peer_review` vai só às fontes que o aceitam: hoje só o OpenAlex, conferido uma vez pela assinatura ou por um atributo da classe. Assim, um `TypeError` de dentro de uma fonte não fica escondido nem repete a busca;
  - em `core/repeat.py`, `include_peer_review = orig_params.get("include_peer_review") is True`, e o registro novo grava o valor de fato usado.
- **Orientação à IA:** o prompt `plan_search` e a descrição de `search_works` dizem que `scopus` e `web_of_science` entram quando a pessoa pedir e tiver configurado as chaves (`list_sources` mostra), e que o Web of Science não traz resumo nem afiliações.

## O que não faz

- Não muda as respostas para quem não pede as bases pagas.
- Não escreve o README nem o contrato: são do Claude.
- Não guarda chave em arquivo nenhum.

## Pronto quando

- [ ] Teste: `search_works` com `sources=["scopus", "web_of_science"]` (fontes falsas) grava a lista com o estado das duas, e sem `sources` consulta só as três de sempre
- [ ] Teste: um artigo do OpenAlex e do Scopus com o mesmo DOI vira um só, com os `source_ids` e as `citations` das duas fontes
- [ ] Teste: `list_sources` no stdio lista as sete, com `missing_key` sem as chaves e `ok` com elas, sem mostrar valor de chave
- [ ] Teste: no modo HTTP, `list_sources` não lista as duas, e `search_works` com `scopus` responde `invalid_input` com a mensagem acima, sem chamar fonte nenhuma
- [ ] Teste: `find_work` e `get_related_works` com `sources=["scopus"]` respondem `invalid_input`
- [ ] Teste: `repeat_search` de uma busca com `scopus` repete com `scopus`
- [ ] Teste: o CSV tem as quatro colunas novas no fim, e as antigas continuam iguais
- [ ] Teste: o `log.md` tem a linha de crédito quando a busca trouxe dados do Scopus ou do Web of Science, e não tem quando não trouxe
- [ ] Teste: uma fonte falsa que levanta `TypeError` dentro de `search` dá `failed` para aquela fonte, com um pedido só (sem repetir)
- [ ] Os três gates passam

## Vem de

D-023, D-022, FR-01, FR-03, FR-04, FR-06, FR-07, NFR-03. São os ids que o código leva como âncoras.

## Antes de começar

10-01, 10-02 e 10-03 integradas. Ler:
- `src/rslapp/server.py`: `SourceName`, `list_sources`, `_build_sources`, `search_works`, `repeat_search`, `find_work`, `get_related_works` e `_is_http_mode`;
- `src/rslapp/core/search.py` (`_select_sources`);
- `src/rslapp/core/find.py` e `src/rslapp/core/related.py`;
- `src/rslapp/core/dedup.py` e `src/rslapp/exporters/csv.py`;
- `src/rslapp/store/log.py`, `src/rslapp/config.py` e `src/rslapp/prompts.py`;
- a spec da 09-03, que fez o mesmo com o PubMed e o Europe PMC.

Cerca de 350 linhas. Um commit para o servidor e a configuração, outro para a deduplicação, o CSV e o log, outro para o prompt, com D-023 no comentário e no nome dos testes.

## Resultado da entrega

Liguei os conectores das bases pagas `scopus` (10-02) e `web_of_science` (10-03) ao servidor MCP e suas ferramentas, com as regras estritas da D-023:
- **Ferramentas MCP:** `search_works` e `repeat_search` aceitam `scopus` e `web_of_science` em `sources`. Sem `sources`, continuam consultando exclusivamente as três fontes abertas padrão (`openalex`, `crossref`, `semantic_scholar`).
- **`list_sources`:** no transporte stdio lista as 7 fontes acadêmicas. `scopus` e `web_of_science` dizem `needs_key: true`, com `configured` e `status` (`ok` ou `missing_key`) conforme `SCOPUS_API_KEY` e `WOS_STARTER_API_KEY`. Nenhum valor de chave é exposto. A docstring esclarece que as duas são bases pagas e só funcionam com a chave e assinatura do próprio usuário ou instituição.
- **Modo hospedado (HTTP):** `list_sources` não lista as bases pagas (mantém apenas as 5 fontes abertas); `search_works` e `repeat_search` com `scopus` ou `web_of_science` recusam antes de chamar qualquer fonte com `invalid_input: scopus e web_of_science só funcionam no RSL.app instalado no seu computador, com a sua chave e o acesso da sua instituição (D-023)`; `_build_sources` não instancia os conectores de bases pagas no modo HTTP.
- **Bloqueio em `find_work` e `get_related_works`:** recusam `scopus` e `web_of_science` com `invalid_input: fonte não suportada nesta ferramenta: <nome>`, sem acionar fontes nem rede.
- **Deduplicação:** `SOURCE_PRECEDENCE` atualizada para `("openalex", "crossref", "semantic_scholar", "scopus", "web_of_science", "europe_pmc", "pubmed")`. Artigos com mesmo DOI unem `source_ids` e `citations` de todas as fontes mantendo os campos da fonte de maior prevalência.
- **Exportador CSV:** inclusão de 4 colunas novas no fim (`Scopus EID`, `Web of Science UID`, `Citations Scopus`, `Citations Web of Science`), preservando a ordem e integridade das 22 colunas anteriores para compatibilidade com o VOSviewer.
- **Crédito à fonte no `log.md`:** buscas que trouxeram dados de bases pagas terminam com a linha de crédito correspondente ("Dados do Scopus (Elsevier)" e/ou "Source: Clarivate Analytics (Web of Science)"); buscas sem dados de bases pagas não recebem a linha.
- **Limpeza da 10-01:** removido `try/except TypeError` em volta de `cache_query` e `search` em `core/search.py`, passando `include_peer_review` apenas às fontes que o aceitam (OpenAlex); se uma fonte levantar `TypeError`, ela é marcada como `failed` com uma única chamada (sem retentativa cega). Em `core/repeat.py`, `include_peer_review = orig_params.get("include_peer_review") is True` e grava no novo registro o valor efetivamente utilizado.
- **Prompt e orientações:** `render_plan_search` e a descrição de `search_works` orientam que `scopus` e `web_of_science` entram quando a pessoa pedir e tiver configurado as chaves (`list_sources` mostra), e que o Web of Science não traz resumo nem afiliações.

## Como testar

Onde olhar primeiro (pontos mais arriscados, o mais difícil primeiro):
1. **Isolamento de segredos e bloqueio no modo hospedado (D-023):** rodar `pytest tests/test_server_paid_sources.py -k "test_d023_modo_http_recusa_bases_pagas or test_d023_list_sources_stdio"` para certificar que chaves nunca vazam e que o modo HTTP não lista nem permite acionar bases pagas.
2. **Exportação CSV e integridade das colunas:** rodar `pytest tests/exporters/test_csv.py -k test_d023_csv_quatro_colunas_novas_no_fim_e_colunas_antigas_iguais` para conferir que as 22 colunas preexistentes continuam intactas e as 4 novas estão no final.
3. **Crédito no `log.md` e deduplicação:** rodar `pytest tests/test_server_paid_sources.py -k test_d023_search_works_grava_linha_de_credito_no_log_md` e `pytest tests/core/test_dedup.py -k test_d023_dedup_openalex_e_scopus_mesmo_doi_mescla_com_precedencia`.
4. **Limpeza da 10-01 com TypeError de dentro de fonte:** rodar `pytest tests/test_server_paid_sources.py -k test_d023_fonte_falsa_que_levanta_typeerror_da_failed_com_um_pedido_so`.

Para rodar a suíte completa de testes da integração das bases pagas no servidor:
```bash
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/test_server_paid_sources.py -v
```
Deve exibir os 8 testes passando com sucesso.
