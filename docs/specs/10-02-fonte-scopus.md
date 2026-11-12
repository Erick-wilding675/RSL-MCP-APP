# Fonte Scopus

**Fase:** 10 · Bases pagas e filtros (1.3) · **Situação:** a fazer

## O que faz

O conector `sources/scopus.py`, com a mesma interface das outras fontes (`Source`). Ele busca por termos na Scopus Search API com a chave da própria pessoa (D-023) e traduz cada resultado para `Work`: todos os autores com ORCID e afiliações, resumo, palavras-chave e número de citações.

## O que não faz

- Não entra em `server.py` nem em `list_sources`: isso é a 10-04.
- Não traz as referências de cada artigo, que pediriam a Abstract Retrieval API, um pedido por artigo: `references` fica vazio.
- Não usa paginação por cursor. A paginação simples chega a 5.000 itens, bem acima do que o RSL.app pede por fonte.
- Não roda no modo hospedado (10-04).

## Conferência do T-001 (Scopus)

Lida pelo Claude Code em 2026-11-11 nas páginas oficiais: `dev.elsevier.com/documentation/ScopusSearchAPI.wadl`, `api_key_settings.html`, `sc_search_views.html`, `sc_search_tips.html`, `policy.html` e o exemplo `payloads/search/scopusSearchResp.json`.

- **Pedido:** `GET https://api.elsevier.com/content/search/scopus`.
  - Cabeçalhos: `X-ELS-APIKey` (obrigatório), `X-ELS-Insttoken` (opcional, o token institucional) e `Accept: application/json`.
  - Parâmetros: `query` (obrigatório, sintaxe booleana do Scopus), `view` (`STANDARD` ou `COMPLETE`), `start` (posição), `count` (quantidade) e `sort`.
- **Limites:**
  - 20.000 pedidos por semana e 9 por segundo;
  - visão COMPLETE com no máximo 25 resultados por pedido, STANDARD com 200;
  - 5.000 itens sem cursor.
- **Respostas de erro:** 400 (pedido inválido), 401 (chave ausente ou inválida), 403 (sem direito de acesso), 429 (cota estourada), 500 (erro genérico).
- **Acesso:** a chave sozinha não dá dados. A Elsevier confere a assinatura da instituição pelo IP de quem chama, ou pelo token institucional, que a instituição pede à Elsevier.
- **Resposta (`search-results`):** `opensearch:totalResults` (texto) e a lista `entry`. Cada entrada da visão COMPLETE traz:
  - `dc:identifier` (`SCOPUS_ID:…`), `eid`, `dc:title`, `prism:doi`, `prism:publicationName`, `prism:coverDate` (`AAAA-MM-DD`);
  - `dc:description` (o resumo), `authkeywords` (texto separado por ` | `), `citedby-count` (texto);
  - `subtype` e `subtypeDescription` (por exemplo `Article`, `Review`, `Conference Paper`);
  - `pubmed-id`, quando houver;
  - `affiliation[]`, com `afid`, `affilname`, `affiliation-city` e `affiliation-country`;
  - `author[]`, com `authid`, `authname`, `given-name`, `surname`, `orcid` e `afid[]` (cada um `{"$": "<afid>"}`).
  - Uma busca sem resultado pode trazer uma entrada com `error`; isso conta como zero resultados.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-11, baratas de desfazer:

1. **Consulta:**
   - Se o texto já usa a sintaxe do Scopus (tem um código de campo seguido de parêntese, como `TITLE-ABS-KEY(`, `AUTH(` ou `DOI(`, conferido por expressão regular `\b[A-Z][A-Z-]+\(`), vai como está.
   - Senão, vai como `TITLE-ABS-KEY(<texto>)`, que procura no título, no resumo e nas palavras-chave, como as outras fontes.
2. **Fluxo:**
   - `view=COMPLETE`, `count=min(25, falta)`, `start=0, 25, 50…` até `max_results` ou até `totalResults`;
   - limite de 5.000;
   - um pedido por vez, com pelo menos 0,2 s entre um e outro.
   - `found` = `opensearch:totalResults`.
3. **Chave:** a chave vem de `SCOPUS_API_KEY` e o token de `SCOPUS_INSTTOKEN`, os dois só nos cabeçalhos, nunca na URL. Assim nenhum dos dois aparece na linha que o `httpx` registra, nem em `query`, `reason`, `cache_query`, `repr` ou erros. Sem `SCOPUS_API_KEY`, a busca responde `missing_key` sem chamar a rede. `needs_key` é verdadeiro.
4. **Visão reduzida:** se o pedido COMPLETE responder 403, o conector tenta uma vez a visão STANDARD.
   - Se a STANDARD responder 200, segue nela e avisa em `reason`: "visão reduzida do Scopus: só o primeiro autor, sem resumo nem palavras-chave".
   - Se a STANDARD também der 403, o estado é `failed`, com `reason` "o Scopus recusou o acesso: confira se está na rede da instituição ou configure SCOPUS_INSTTOKEN".
   - A página das visões não diz se a COMPLETE exige assinatura, então este caminho cobre as duas possibilidades.
5. **Mapeamento:**
   - `title`: `dc:title`; sem título, o registro é descartado.
   - `doi`: `prism:doi` em minúsculas.
   - `year`: os 4 primeiros dígitos de `prism:coverDate`.
   - `venue`: `prism:publicationName`.
   - `abstract`: `dc:description`, sem a frase final de direitos autorais (o trecho a partir de `©` no fim) e com espaços simples.
   - `keywords`: `authkeywords` dividido por `|`, sem espaços nas pontas e sem repetir.
   - `type`: `subtypeDescription` em minúsculas.
   - `authors`, na ordem:
     - `name` = `given-name surname` quando houver os dois, senão `authname`;
     - `orcid` na forma curta, quando houver;
     - `ids` = `{"scopus": authid}`;
     - `affiliations` = as afiliações cujo `afid` está em `author.afid`, com `Affiliation(name=affilname, ids={"scopus": afid})`;
     - `raw_affiliations` = `"affilname, cidade, país"` sem as partes vazias.
     - Na visão STANDARD, entra só o autor de `dc:creator`.
   - `references`: vazio. `references_count`: nulo.
   - `citations`: `{"scopus": int(citedby-count)}` quando for número.
   - `source_ids`: `{"scopus": eid}` e, quando houver, `"pubmed": pubmed-id`.
6. **Estados e novas tentativas**, como nas outras fontes:
   - 429, 5xx, tempo esgotado e erro de rede: até 3 novas tentativas (1, 2 e 4 s); esgotadas, `rate_limited` (429) ou `failed`;
   - 401: `failed` na hora, com `reason` "chave do Scopus recusada";
   - 403: segue a decisão 4;
   - outras 4xx: `failed` na hora;
   - as páginas já trazidas ficam.
7. **Cache:** `cache_query` devolve `{"source": "scopus", "query": ..., "max_results": ...}`, sem chave nem token.

## Pronto quando

- [ ] Teste com respostas simuladas (`httpx.MockTransport`), a partir do exemplo oficial da visão COMPLETE: os campos acima são mapeados, inclusive autor sem ORCID, autor com duas afiliações, resumo com "©", `authkeywords` vazio, `prism:coverDate` ausente e registro sem título descartado
- [ ] Teste: texto simples vira `TITLE-ABS-KEY(...)`, e `AUTH(silva) AND TITLE(x)` vai como está
- [ ] Teste: a paginação pede `start` 0, 25 e 50 e para em `max_results` ou em `totalResults`
- [ ] Teste: 403 na COMPLETE e 200 na STANDARD seguem com o aviso; 403 nas duas dá `failed` com a mensagem da decisão 4
- [ ] Teste: 401, 429 e 5xx seguem os estados acima
- [ ] Teste: com `SCOPUS_API_KEY` e `SCOPUS_INSTTOKEN`, os dois vão nos cabeçalhos e não aparecem na URL, em `query`, `reason`, `cache_query`, `repr` nem nos registros do `caplog`
- [ ] Teste: sem `SCOPUS_API_KEY`, `missing_key` sem pedido nenhum
- [ ] Os três gates passam

## Vem de

D-023, FR-01, FR-03, FR-14, NFR-04, D-004. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/sources/europe_pmc.py` e `tests/sources/test_europe_pmc.py` inteiros (o molde mais novo), `src/rslapp/sources/base.py`, `src/rslapp/core/models.py` e `src/rslapp/config.py`. Acrescentar a `config.py` `scopus_key_configured` e `scopus_insttoken_configured`, lidos como as outras chaves.

Cerca de 350 linhas, testes incluídos. Um commit para o conector, outro para os testes, com D-023 no comentário e no nome dos testes.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/config.py`: adicionados os campos `scopus_key_configured` e `scopus_insttoken_configured` ao dataclass `Config`, carregados a partir de `SCOPUS_API_KEY` e `SCOPUS_INSTTOKEN` via `_is_key_configured` (**FR-07**, **NFR-03**, **D-023**).
  - `src/rslapp/sources/scopus.py`: conector `ScopusSource` implementando o protocolo `Source` para a API Scopus Search (`https://api.elsevier.com/content/search/scopus`). Configurado com `needs_key = True`. Realiza paginação simples (`count=min(25, falta)`, `start=0, 25, 50...`) com intervalo de pelo menos 0,2 s entre pedidos e teto de 5.000 resultados. Mantém sintaxe nativa do Scopus quando detectado código de campo (`\b[A-Z][A-Z-]+\(`) ou encapsula a consulta em `TITLE-ABS-KEY(...)`. Passa `X-ELS-APIKey` e opcionalmente `X-ELS-Insttoken` estritamente em cabeçalhos HTTP, sem expor credenciais em URL, query, reason, cache_query, repr ou caplog; devolve `missing_key` sem requisições de rede quando `SCOPUS_API_KEY` não está configurada. Mapeia a visão `COMPLETE` com título, DOI em minúsculas, ano de 4 dígitos de `prism:coverDate`, periódico de `prism:publicationName`, resumo com limpeza de direitos autorais da última frase (`_clean_abstract` cortando a partir de `©` e prefixos `Copyright` ou `(C)` apenas quando não houver encerramento de frase posterior, preservando `©` no meio do texto) e espaços simples, palavras-chave divididas por `|` sem repetição e sem espaços nas pontas, tipo em minúsculas, autores na ordem com `given-name surname` (ou `authname`), ORCID curto, `ids={"scopus": authid}`, e afiliações correlacionadas por `afid` com nome e `raw_affiliations` no formato `affilname, cidade, país`. Descarte de registros sem título ou com erro. Em caso de 403 na visão `COMPLETE`, aguarda `REQUEST_INTERVAL` e tenta a visão reduzida `STANDARD` (notificando em `reason` quando bem-sucedida, ou reportando `failed` com mensagem única sem duplicação caso recuse). Trata retentativas com recuo exponencial (1, 2 e 4 s) para 429 transitório, 5xx, timeout e erros de rede, preservando páginas parciais já trazidas em caso de falha posterior (**FR-01**, **FR-03**, **FR-14**, **NFR-04**, **D-004**, **D-023**).
  - `tests/test_config.py`: testes de configuração verificando `scopus_key_configured` e `scopus_insttoken_configured` em isolamento, valores vazios, valores válidos, e não exposição em representações (`repr`, `str`, `asdict`, `vars`) e mensagens de erro (**FR-07**, **NFR-03**).
  - `tests/sources/test_scopus.py`: suíte completa com 12 testes unitários sem rede (`httpx.MockTransport`), cobrindo mapeamento da visão COMPLETE (inclusive autor sem ORCID, autor com duas afiliações, resumo com "©", `authkeywords` vazio, `prism:coverDate` ausente e registros sem título descartados), sintaxe Scopus e texto simples, paginação com `start` 0, 25, 50 até limites, fallback de 403 para visão STANDARD com respeito a `REQUEST_INTERVAL` e falha dupla, estados 401, 429, 5xx, timeout e rede com páginas parciais mantidas, retry de 429 seguido de 200, limpeza de direitos autorais no resumo e preservação de `©` no meio, isolamento rigoroso de credenciais em cabeçalhos, e `missing_key` sem rede (**FR-01**, **FR-03**, **FR-14**, **NFR-04**, **D-004**, **D-023**).
- **O que foi assumido:**
  - Registros com `dc:title` ausente, vazio ou contendo apenas espaços são descartados.
  - Na visão `STANDARD`, apenas `dc:creator` entra como autor único e `abstract` e `keywords` ficam vazios/nulos, conforme a especificação.
- **O que não deu para verificar:**
  - Chamadas com rede aberta à API real da Elsevier (testes executados com `httpx.MockTransport`, conforme regra do projeto de não fazer requisições externas nos testes automatizados).

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
2. **O que deve aparecer:**
   - `All checks passed!` na verificação do `ruff check .`
   - `634 passed` no `pytest` em Python 3.10 e em Python 3.14.
3. **Onde olhar primeiro (pontos de risco, do mais difícil ao mais simples):**
   1. **Isolamento de credenciais (`SCOPUS_API_KEY` e `SCOPUS_INSTTOKEN`) (`src/rslapp/sources/scopus.py` — `headers`, `cache_query`, `_format_query_text`, `__repr__`, NFR-03, D-023):** verificar que a chave e o token institucional vão exclusivamente nos cabeçalhos `X-ELS-APIKey` e `X-ELS-Insttoken`, nunca na URL (evitando logging do `httpx`), em `query`, `reason`, `cache_query`, `repr` nem no `caplog`.
   2. **Fallback para visão STANDARD em 403 e intervalo entre requisições (`src/rslapp/sources/scopus.py` — `search`, D-023):** verificar o aguardo de `REQUEST_INTERVAL` (0,2 s) antes da requisição STANDARD de fallback, aviso em `reason` na visão reduzida, fluxo unificado de falha quando ambas recusam, além da paginação por `start` (0, 25, 50).
   3. **Mapeamento de autores, afiliações e resumo na visão COMPLETE (`src/rslapp/sources/scopus.py` — `_parse_work`, `_parse_author`, `_extract_affiliations`, `_clean_abstract`, FR-03, FR-14, D-004, D-023):** conferir a associação de afiliações por `afid` em autores com mais de uma afiliação, formatação de `raw_affiliations`, normalização de ORCID curto, corte da última frase a partir de `©` (e `Copyright`/`(C)` logo antes) apenas sem encerramento de frase posterior, e descarte seguro de registros sem título.

**Revisão do Claude (2026-11-12, run `b20261111-211913` do Playmaker):** duas rodadas (Gemini 3.8 Flash).
- **Primeira rodada:** voltou pelo parecer do agente revisor. Faltava a espera de 0,2 s antes do pedido STANDARD, sobrava uma variável sem uso, três retornos de erro estavam duplicados, o corte do "©" apagava o resto do resumo quando o símbolo aparecia no meio, e os itens de "Pronto quando" estavam marcados.
- **Segunda rodada:** os cinco pontos foram corrigidos, conferidos pelo Claude Code, e a tarefa foi integrada com os gates refeitos pelo `board integrate`.

Conferido pelo revisor com testes próprios, inclusive pelo transporte real do `httpx` em DEBUG:
- a chave e o token só vão nos cabeçalhos e não aparecem em log, URL, `query`, `reason`, `repr` nem `cache_query`, nem quando o servidor ecoa a chave na resposta;
- as esperas das novas tentativas são 1, 2 e 4 s;
- a visão reduzida segue na STANDARD nas páginas seguintes;
- a paginação para em 5.000;
- o mapeamento bate com o exemplo oficial.

O comportamento com a API real (403 fora da rede da instituição, `insttoken`) espera a chave do Erick (10-05). O conector tem 593 linhas; a estimativa da spec era baixa, já que o molde tem 512.
