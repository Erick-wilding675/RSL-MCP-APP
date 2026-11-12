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

(preenche quem entrega)

## Como testar

(preenche quem entrega)
