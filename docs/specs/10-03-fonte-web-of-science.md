# Fonte Web of Science (Starter API)

**Fase:** 10 · Bases pagas e filtros (1.3) · **Situação:** a fazer

## O que faz

O conector `sources/web_of_science.py`, com a mesma interface das outras fontes (`Source`). Ele busca por termos na Web of Science Starter API com a chave da própria pessoa (D-023) e traduz cada resultado para `Work`: título, autores, palavras-chave dos autores, periódico, ano, DOI, PubMed ID e número de citações.

## O que não faz

- Não entra em `server.py` nem em `list_sources`: isso é a 10-04.
- Não traz resumo, afiliações nem referências, porque o Starter não devolve esses campos. A API Expanded, que devolve, é paga e fica para depois (D-023).
- Não roda no modo hospedado (10-04).

## Conferência do T-001 (Web of Science Starter)

Lida pelo Claude Code em 2026-11-11: a página `developer.clarivate.com/apis/wos-starter` e a descrição OpenAPI em `developer.clarivate.com/apis/wos-starter/swagger`.

- **Pedido:** `GET https://api.clarivate.com/apis/wos-starter/v1/documents`.
  - Cabeçalho: `X-ApiKey`.
  - Parâmetros:
    - `db` (padrão `WOS`);
    - `q` (busca avançada com as etiquetas aceitas pelo Starter, entre elas `TS` para tópico, `TI`, `AU`, `SO`, `PY`, `DO`, `DT`, `PMID` e `OG`);
    - `limit` (1 a 50, padrão 10);
    - `page` (padrão 1);
    - `sortField` (por exemplo `RS+D` para relevância).
  - `TS` procura no título, no resumo, nas palavras-chave dos autores e nas Keywords Plus.
- **Planos:**
  - Free Trial: 1 pedido por segundo e 50 por dia, sem número de citações;
  - Free Institutional Member: 5 por segundo e 5.000 por dia, com citações;
  - Integration: 20.000 por dia.
- **Resposta:** `metadata` (`total`, `page`, `limit`) e `hits[]`. Cada documento traz:
  - `uid` (`WOS:…`), `title`, `types[]`;
  - `source` (`sourceTitle`, `publishYear`, `volume`, `issue`, `pages`);
  - `names.authors[]` (`displayName`, `wosStandard`, `researcherId`);
  - `citations[]` (`db`, `count`), conforme o plano;
  - `identifiers` (`doi`, `issn`, `eissn`, `pmid`);
  - `keywords.authorKeywords[]`;
  - `links.record`.
- **Respostas de erro:** a descrição só documenta o 200. Os outros códigos seguem a regra geral das fontes (decisão 4).

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-11, baratas de desfazer:

1. **Consulta:** se o texto já usa etiquetas do Web of Science (`\b[A-Z]{2,4}=`, como `TS=` ou `AU=`), vai como está. Senão, vai como `TS=(<texto>)`.
2. **Fluxo:**
   - `db=WOS`, `limit=min(50, max_results)`, `page=1, 2…` até `max_results` ou até `metadata.total`;
   - um pedido por vez, com pelo menos 1,1 s entre um e outro, para caber no plano de teste (1 por segundo).
   - `found` = `metadata.total`.
3. **Chave:** vem de `WOS_STARTER_API_KEY`, só no cabeçalho `X-ApiKey`, nunca na URL nem em `query`, `reason`, `cache_query`, `repr` ou erros. Sem a chave, a busca responde `missing_key` sem chamar a rede. `needs_key` é verdadeiro.
4. **Estados e novas tentativas:**
   - 429, 5xx, tempo esgotado e erro de rede: até 3 novas tentativas (1, 2 e 4 s); esgotadas, `rate_limited` (429) ou `failed`.
   - Quando o 429 se repetir até o fim, `reason` diz "limite diário do Web of Science atingido (50 pedidos por dia no plano de teste)".
   - 401 e 403: `failed` na hora, com `reason` "chave do Web of Science recusada ou sem acesso".
   - Outras 4xx: `failed` na hora.
   - As páginas já trazidas ficam.
5. **Mapeamento:**
   - `title`: `title`; sem título, o registro é descartado.
   - `doi`: `identifiers.doi` em minúsculas.
   - `year`: `source.publishYear`.
   - `venue`: `source.sourceTitle`.
   - `type`: o primeiro de `types`, em minúsculas.
   - `keywords`: `keywords.authorKeywords`, sem espaços nas pontas e sem repetir.
   - `abstract`: nulo.
   - `authors`, na ordem: `name` = `displayName`, `ids` = `{"web_of_science": researcherId}` quando houver, sem ORCID e sem afiliações.
   - `references`: vazio. `references_count`: nulo.
   - `citations`: `{"web_of_science": count}` da entrada com `db` igual a `WOS`, quando houver. Sem ela, o campo fica sem a chave, para não confundir "sem dado" com zero.
   - `source_ids`: `{"web_of_science": uid}` e, quando houver, `"pubmed": identifiers.pmid`.
6. **Cache:** `cache_query` devolve `{"source": "web_of_science", "query": ..., "max_results": ...}`, sem a chave.

## Pronto quando

- [ ] Teste com respostas simuladas (`httpx.MockTransport`), a partir do exemplo oficial: os campos acima são mapeados, inclusive documento sem DOI, sem `citations` (plano de teste), com `pmid`, sem `researcherId` e sem título (descartado)
- [ ] Teste: texto simples vira `TS=(...)`, e `AU=Silva AND PY=2020` vai como está
- [ ] Teste: a paginação pede `page` 1, 2 e 3 e para em `max_results` ou em `total`, esperando pelo menos 1,1 s entre os pedidos (com `sleep` injetado)
- [ ] Teste: 429 repetido dá `rate_limited` com a mensagem do limite diário; 401 e 403 dão `failed` na hora
- [ ] Teste: a chave vai no cabeçalho `X-ApiKey` e não aparece na URL, em `query`, `reason`, `cache_query`, `repr` nem nos registros do `caplog`
- [ ] Teste: sem `WOS_STARTER_API_KEY`, `missing_key` sem pedido nenhum
- [ ] Os três gates passam

## Vem de

D-023, FR-01, FR-03, NFR-04, D-004. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/sources/europe_pmc.py` e `tests/sources/test_europe_pmc.py` inteiros (o molde mais novo), `src/rslapp/sources/base.py`, `src/rslapp/core/models.py` e `src/rslapp/config.py`. Acrescentar a `config.py` `wos_key_configured`, lido como as outras chaves.

Cerca de 300 linhas, testes incluídos. Um commit para o conector, outro para os testes, com D-023 no comentário e no nome dos testes.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/config.py`: adicionado o campo `wos_key_configured` ao dataclass `Config`, carregado a partir da variável de ambiente `WOS_STARTER_API_KEY` via `_is_key_configured` (**FR-07**, **NFR-03**, **D-023**).
  - `src/rslapp/sources/web_of_science.py`: conector `WebOfScienceSource` implementando o protocolo `Source` para a Web of Science Starter API (`https://api.clarivate.com/apis/wos-starter/v1/documents`). Configurado com `needs_key = True`. Realiza paginação simples com `limit=min(50, effective_max)` e `page=1, 2…`, aguardando pelo menos 1,1 s (`REQUEST_INTERVAL = 1.1`) entre pedidos para respeitar o teto do plano de teste (1 pedido por segundo). Preserva a consulta quando detectada etiqueta de campo do Web of Science (`\b[A-Z]{2,4}=`, como `TS=` ou `AU=`) ou envolve o termo em `TS=(...)`. Passa `WOS_STARTER_API_KEY` estritamente no cabeçalho HTTP `X-ApiKey`, sem expor credenciais na URL, query, reason, cache_query, repr ou caplog; responde `missing_key` sem chamadas de rede quando a variável de ambiente não está configurada. Traduz cada registro para `Work`: título, DOI em minúsculas (normalizado), ano de 4 dígitos de `source.publishYear`, periódico de `source.sourceTitle`, tipo do primeiro elemento de `types` em minúsculas, palavras-chave dos autores (`keywords.authorKeywords`) sem repetição e sem espaços nas pontas, autores na ordem com `displayName` (e fallback para `wosStandard`), `ids={"web_of_science": researcherId}` quando houver, sem ORCID e sem afiliações, contagem de citações de `db == "WOS"` (sem a chave quando ausente, evitando confundir ausência com zero), e identificadores de fonte em `source_ids` (`web_of_science` do `uid` e `pubmed` de `identifiers.pmid`). Registros sem título são descartados. Erros 401 e 403 falham na hora com `failed` ("chave do Web of Science recusada ou sem acesso"); erro 429 persistente após 3 tentativas de recuo (1, 2 e 4 s) devolve `rate_limited` informando o limite diário de 50 pedidos do plano de teste; erros 5xx, timeout e rede realizam até 3 novas tentativas antes de reportar `failed`; páginas parciais já obtidas são mantidas em falhas subsequentes (**FR-01**, **FR-03**, **FR-14**, **NFR-04**, **D-004**, **D-023**).
  - `tests/test_config.py`: atualizados os testes de configuração para incluir `WOS_STARTER_API_KEY` e `wos_key_configured` em isolamento, valores vazios, chave independente, não exposição em representações (`repr`, `str`, `vars`, `asdict`) e mensagens de erro (**FR-07**, **NFR-03**).
  - `tests/sources/test_web_of_science.py`: nova suíte de testes com 10 testes unitários sem rede (`httpx.MockTransport`), cobrindo mapeamento do exemplo oficial e casos especiais (sem DOI, sem citações, com pmid, sem researcherId e descarte de itens sem título), preservação de sintaxe e encapsulamento em `TS=(...)`, paginação em páginas 1, 2 e 3 com intervalo de 1,1 s e paradas corretas por `max_results` ou `total`, estados de erro (429 repetido, 401, 403, 400, 500, timeout e rede), preservação de páginas em falha posterior, recuperação de 429 seguido de 200, isolamento rigoroso da chave em `X-ApiKey` sem vazamento, e `missing_key` sem requisição (**FR-01**, **FR-03**, **FR-14**, **NFR-04**, **D-004**, **D-023**).
- **O que foi assumido:**
  - Registros com `title` ausente, vazio ou contendo apenas espaços são descartados.
  - O resumo (`abstract`), as afiliações e as referências são nulos/vazios no plano Starter da API Clarivate, conforme a spec e a decisão D-023.
- **O que não deu para verificar:**
  - Chamadas com rede aberta à API real da Clarivate Web of Science (todos os testes foram realizados com `httpx.MockTransport`, conforme a regra do projeto).

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
2. **O que deve aparecer:**
   - `All checks passed!` na verificação do `ruff check .`
   - `655 passed` no `pytest` em Python 3.10 e em Python 3.14.
3. **Onde olhar primeiro (pontos de risco, do mais difícil ao mais simples):**
   1. **Isolamento de credencial (`WOS_STARTER_API_KEY`) (`src/rslapp/sources/web_of_science.py` — `headers`, `cache_query`, `_format_query_text`, `__repr__`, NFR-03, D-023):** conferir que a chave vai exclusivamente no cabeçalho `X-ApiKey`, nunca na URL (evitando logging do `httpx`), em `query`, `reason`, `cache_query`, `repr` nem no `caplog`.
   2. **Tratamento de 429 com limite diário e intervalo de pelo menos 1,1 s entre pedidos (`src/rslapp/sources/web_of_science.py` — `search`, `_request_page`, NFR-04, D-023):** verificar o aguardo de `REQUEST_INTERVAL` (1,1 s) antes de cada página subsequente, as 3 retentativas (1, 2 e 4 s) para 429 transitório e a mensagem exata de limite diário do plano de teste ao esgotar as tentativas.
   3. **Mapeamento de citações do WOS e descarte de registros sem título (`src/rslapp/sources/web_of_science.py` — `_parse_work`, `_extract_citations`, `_parse_authors`, FR-03, FR-14, D-004, D-023):** verificar que apenas entradas com `db == "WOS"` geram citação (evitando que a ausência seja mapeada como 0), que autores levam `ids={"web_of_science": researcherId}` sem afiliações, e que registros sem título são descartados.
