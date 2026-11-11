# Fonte PubMed

**Fase:** 9 · Versão 1.2 · **Situação:** pronta

## O que faz

O conector `sources/pubmed.py`, com a mesma interface das outras fontes (`Source`, em `sources/base.py`): busca por termos no PubMed pelas E-utilities do NCBI e traduz cada registro para `Work`, com autores, ORCID, afiliações, resumo, palavras-chave e os DOIs das referências quando o PubMed os traz.

## O que não faz

- Não entra nas fontes do servidor nem em `server.py`: isso é a 09-03.
- Não busca por título ou DOI exato (`find_work`) nem referências ou citações de um artigo (`get_related_works`).
- Não deduplica entre fontes: a deduplicação que já existe faz isso na 09-03.

## Conferência do T-001 (PubMed)

Lida pelo Claude Code em 2026-11-11: "A General Introduction to the E-utilities" (NBK25497) e "The E-utilities In-Depth" (NBK25499), no NCBI Bookshelf, e chamadas reais a `esearch.fcgi`, `efetch.fcgi` e `elink.fcgi`.

- **Endereço:** `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`.
- **Limite:** sem chave, no máximo **3 pedidos por segundo** por IP; com chave (`api_key`), até **10 por segundo**. Acima disso, a resposta é um erro com `"API rate limit exceeded"`. A resposta real trouxe `X-Ratelimit-Limit: 3` e `X-Ratelimit-Remaining`. Trabalhos grandes devem ir para fins de semana ou entre 21h e 5h (horário da costa leste dos EUA); o RSL.app faz buscas pequenas.
- **Identificação:** todo pedido leva `tool` (texto sem espaço que identifica o programa) e `email` (de quem desenvolve ou opera o programa, não de um terceiro). O NCBI usa o e-mail só para avisar antes de bloquear um IP.
- **ESearch** (`esearch.fcgi?db=pubmed&term=<termos>&retmode=json&retmax=<n>&usehistory=y`): devolve `esearchresult.count` (texto), `idlist` (PMIDs, texto), `webenv` e `querykey` quando `usehistory=y`. `retmax` vai até 10.000, e o PubMed só devolve os primeiros 10.000 registros de uma busca.
- **EFetch** (`efetch.fcgi?db=pubmed&retmode=xml`): aceita `id` com a lista de PMIDs separados por vírgula (acima de uns 200, usar POST) ou `WebEnv` e `query_key` com `retstart` e `retmax`. Só tem saída em XML para registros completos.
- **XML de um `PubmedArticle`** (conferido em três registros reais):
  - `MedlineCitation/PMID`;
  - `Article/ArticleTitle`, que pode ter marcas internas como `<i>`;
  - `Article/Abstract/AbstractText`, uma ou várias partes, com atributo `Label` quando o resumo é estruturado;
  - `Article/Journal/Title`;
  - `Article/Journal/JournalIssue/PubDate/Year`, ou `MedlineDate` (texto como `2020 Jan-Feb`);
  - `Article/ArticleDate/Year`;
  - `Article/AuthorList/Author`, com `LastName`, `ForeName`, `Initials` ou `CollectiveName`, `Identifier Source="ORCID"` (pode vir só o número ou a URL) e `AffiliationInfo/Affiliation`;
  - `Article/PublicationTypeList/PublicationType`;
  - `MedlineCitation/KeywordList/Keyword`;
  - `MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName`;
  - `PubmedData/ArticleIdList/ArticleId IdType="doi"|"pubmed"|"pmc"`;
  - `PubmedData/ReferenceList/Reference`, com `Citation` e, muitas vezes, `ArticleIdList/ArticleId IdType="doi"`: num registro real, 89 de 90 referências tinham DOI.
- **O PubMed não traz número de citações** num registro (só pela ELink, fora desta tarefa).

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-11, baratas de desfazer:

1. **Fluxo:** um ESearch com `usehistory=y` e `retmax` = `min(max_results, 10000)`, depois EFetch em lotes de 200 pelo `WebEnv` e `query_key` (`retstart` 0, 200, 400…) até `max_results` ou o fim. `found` = `count` do ESearch; `fetched` = registros traduzidos.
2. **Ritmo:** um pedido por vez, nunca em paralelo, com pelo menos 0,34 s entre pedidos sem chave e 0,1 s com chave. Isso fica dentro do limite e não depende do relógio do servidor.
3. **Chave opcional:** `NCBI_API_KEY`, lida do ambiente como as outras chaves. Esta tarefa acrescenta a `config.py` o campo que diz se ela está configurada (como `semantic_scholar_key_configured`). Ela vai no parâmetro `api_key`. `needs_key` é falso. A chave nunca vai para `query`, `reason`, a chave do cache ou o log, e nunca aparece em `repr`.
4. **Identificação:** `tool=rslapp` sempre; `email=<RSL_CONTACT_EMAIL>` quando houver, com os mesmos cuidados da Crossref: o e-mail fica fora de `query`, do cache e dos erros.
5. **Mapeamento:**
   - `title`: texto de `ArticleTitle` com as marcas internas tiradas e espaços simples; sem título, o registro é descartado.
   - `doi`: de `ArticleId IdType="doi"`, em minúsculas; se não houver, de `ELocationID EIdType="doi"`.
   - `year`: `PubDate/Year`, senão os quatro primeiros dígitos de `MedlineDate`, senão `ArticleDate/Year`, senão nulo.
   - `venue`: `Journal/Title`.
   - `abstract`: as partes de `AbstractText` unidas por espaço; quando uma parte tem `Label`, entra como `LABEL: texto`.
   - `keywords`: as de `KeywordList` primeiro, depois os `DescriptorName` do MeSH, sem repetir (comparação sem maiúsculas). Assim o VOSviewer pode fazer o mapa de coocorrência com o vocabulário do MeSH.
   - `type`: o primeiro `PublicationType`, em minúsculas (por exemplo, `journal article`).
   - `authors`: na ordem. `name` = `ForeName LastName`, ou só `LastName`, ou `CollectiveName`. `orcid` na forma curta `0000-0000-0000-0000`, venha como número ou URL; inválido vira nulo. `raw_affiliations` = os textos de `Affiliation`, e `affiliations` = `Affiliation(name=texto)` para cada um. `position` fica nulo, porque o PubMed não diz.
   - `references`: os DOIs (minúsculos) das referências que têm DOI. `references_count` = número de `Reference` quando há `ReferenceList`, senão nulo.
   - `citations`: vazio. `source_ids`: `{"pubmed": "<PMID>"}`.
6. **XML:** lido com `xml.etree.ElementTree` da biblioteca padrão. O expat do Python 3.10 em diante já se protege da expansão de entidades em massa, e a resposta vem do NCBI por HTTPS. Não entra dependência nova.
7. **Estados e novas tentativas**, como nas outras fontes: 429, 5xx, tempo esgotado, erro de rede e a mensagem `API rate limit exceeded` com até 3 novas tentativas (1, 2 e 4 s); esgotadas, `rate_limited` ou `failed`. Outras 4xx dão `failed` na hora. As páginas já trazidas ficam. Uma busca sem nenhum resultado é `ok` com zero artigos.
8. **Cache:** `cache_query` devolve `{"source": "pubmed", "query": ..., "max_results": ...}`, sem chave e sem e-mail.

## Pronto quando

- [x] Antes de escrever, conferir o T-001 para o PubMed (feito acima pelo Claude Code)
- [x] Teste com respostas simuladas (`httpx.MockTransport`): os campos acima são mapeados, inclusive autor coletivo, ORCID em URL e só número, várias afiliações, resumo estruturado com `Label`, `MedlineDate`, DOI só em `ELocationID`, referências com e sem DOI e registro sem título descartado
- [x] Teste: o ESearch pede `usehistory=y`, e o EFetch pede lotes de 200 pelo `WebEnv` até `max_results`
- [x] Teste: 429, 5xx e a mensagem de limite seguem as novas tentativas e os estados acima
- [x] Teste: com `NCBI_API_KEY` e `RSL_CONTACT_EMAIL`, a URL leva `api_key` e `email`; nenhum dos dois aparece em `query`, `reason` nem `cache_query`
- [x] Teste: os pedidos saem um por vez, com o intervalo mínimo (relógio simulado no teste)
- [x] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

FR-01, FR-03, FR-14, NFR-03, NFR-04, D-004 e D-020. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/sources/crossref.py` e `tests/sources/test_crossref.py` inteiros: o PubMed segue o mesmo molde (estados, novas tentativas, e-mail fora do log, testes com `MockTransport`). Ler `src/rslapp/core/models.py` (`Work`, `Author`, `Affiliation`, `SourceResult`) e `src/rslapp/config.py` (como as chaves são lidas).

Cerca de 350 linhas, testes incluídos. Um commit para o conector e outro para os testes, com D-020 no comentário e no nome dos testes.

## Resultado da entrega

Entregue o conector `PubmedSource` em `src/rslapp/sources/pubmed.py` e os testes completos com `httpx.MockTransport` em `tests/sources/test_pubmed.py`, acompanhados de `ncbi_key_configured` em `src/rslapp/config.py`:

1. **Conector E-utilities enxuto (`PubmedSource`, FR-01, D-020):**
   - ESearch com `usehistory=y`, `retmode=json`, `retmax=min(max_results, 10000)`, `tool=rslapp` e `db=pubmed`.
   - EFetch com `retmode=xml`, `WebEnv` e `query_key` do histórico em lotes de até 200 (`retmax=min(200, faltam)`, `retstart` 0, 200, 400…) até atingir `max_results` ou o fim dos registros.
   - Requisições unificadas no helper `_request(url, params, parse)` com até 3 tentativas (1, 2, 4 s) para 429, 5xx, timeout, rede e rate limit.
   - Busca sem resultados devolve `status="ok"` com `found=0`, `fetched=0` e lista vazia sem acionar EFetch.
2. **Mapeamento completo para `Work` (FR-03, FR-14, D-004, D-020):**
   - `title`: texto de `ArticleTitle` sem marcas internas XML/HTML e com espaços normalizados; registro sem título é descartado.
   - `doi`: prioritariamente de `PubmedData/ArticleIdList/ArticleId IdType="doi"` direto (sem pegar DOIs de `ReferenceList`); se ausente, de `Article/ELocationID EIdType="doi"`, normalizado em minúsculas; senão nulo.
   - `year`: `PubDate/Year`, senão os quatro primeiros dígitos de `MedlineDate`, senão `ArticleDate/Year`, senão nulo.
   - `venue`: `Journal/Title`.
   - `abstract`: partes de `AbstractText` unidas por espaço; quando tem `Label`, prefixa `LABEL: texto`.
   - `keywords`: as de `KeywordList` primeiro, depois `DescriptorName` do MeSH, sem repetições (comparação insensível a maiúsculas).
   - `type`: primeiro `PublicationType` em minúsculas.
   - `authors`: na ordem, com `name` (`ForeName LastName`, ou `LastName`, ou `CollectiveName`), `orcid` em formato canônico `0000-0000-0000-0000` (inválido vira nulo), afiliações em `raw_affiliations` e `affiliations` (`Affiliation(name=...)`), com `position=None`.
   - `references`: lista de DOIs minúsculos das referências; `references_count` total quando `ReferenceList` existe, senão nulo.
   - `citations`: dicionário vazio `{}`; `source_ids`: `{"pubmed": "<PMID>"}`.
3. **Ritmo e controle de taxa (NFR-04, D-020):**
   - Trava assíncrona (`RATE_LOCK`) no módulo garantindo chamadas estritamente sequenciais (nunca em paralelo).
   - Intervalo mínimo entre inícios de chamadas de 0,34 s sem chave (<= 3 req/s) e 0,10 s com chave (<= 10 req/s).
4. **Resiliência e retentativas (NFR-04, D-020):**
   - Até 3 novas tentativas com espera crescente (1 s, 2 s, 4 s) para HTTP 429, 5xx, tempo esgotado, erro de rede e resposta com `"API rate limit exceeded"` (apenas em respostas não 200 ou no erro do ESearch, nunca no XML 200 do EFetch).
   - Outros erros 4xx falham imediatamente sem retentativa.
   - Falha parcial preserva as páginas/registros já obtidos anteriormente.
5. **Segurança e proteção de credenciais (NFR-03, D-020):**
   - Suporte opcional a `NCBI_API_KEY` e `RSL_CONTACT_EMAIL`.
   - Nem a chave nem o e-mail aparecem em `query`, `reason`, `cache_query` ou `__repr__`.
   - Suporte em `config.py` com o campo booleano `ncbi_key_configured`.

## Como testar

**Onde olhar primeiro (pontos de maior risco):**
1. **Isolamento de DOI próprio vs Referências (FR-03, FR-14):** verificar se um artigo sem DOI próprio ou com DOI apenas em `ELocationID` não captura erroneamente os DOIs de suas referências (`test_fr03_d020_doi_proprio_nao_confunde_com_referencias`).
2. **Segurança e isolamento de chaves/e-mail (NFR-03):** verificar se `NCBI_API_KEY` e `RSL_CONTACT_EMAIL` vão nos parâmetros da URL de rede mas nunca vazam em `query`, `reason`, `cache_query` ou `repr` (`test_nfr03_d020_chaves_e_email_nao_vazam_em_nenhum_campo` e `tests/test_config.py`).
3. **Ritmo de requisições e limite do NCBI (NFR-04):** verificar se os pedidos saem um por vez e respeitam os intervalos mínimos de 0,34 s sem chave e 0,10 s com chave (`test_nfr04_d020_ritmo_pedidos_sequenciais_e_intervalo_minimo`).
4. **Mapeamento de dados acadêmicos e autores (FR-03, FR-14, D-004):** conferir a extração de autores coletivos, ORCID, resumo estruturado com Label, referências e descarte de trabalhos sem título (`test_fr01_fr03_fr14_d004_d020_mapeamento_completo_campos`).

**Comandos a executar:**
```bash
# 1. Testes do conector PubMed
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/sources/test_pubmed.py -v

# 2. Testes de configuração
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/test_config.py -v

# 3. Linter e formatação
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
```

**O que deve aparecer:**
- 16 testes de `test_pubmed.py` passando com sucesso.
- 18 testes de `test_config.py` passando com sucesso.
- Ruff limpo com `All checks passed!`.

**Revisão do Claude (2026-11-11, run `b20261111-144701` do Playmaker):** três rodadas. A primeira (Gemini 4 Argon) parou pela cota; a segunda (Gemini 3.8 Flash) voltou pelo parecer do agente revisor. O código usava `.//ArticleIdList/ArticleId` em `PubmedData`, que também acha os DOIs das referências: um artigo sem DOI próprio ficava com o DOI da primeira referência, e a deduplicação juntaria artigos diferentes. Também havia código morto e apelidos sem uso (674 linhas). Na terceira rodada, o DOI vem só do `ArticleIdList` filho direto e, na falta dele, do `ELocationID`. Conferido com o teste do revisor: `ELocationID` próprio mais referências dá o DOI próprio, e sem DOI próprio dá nulo. O limite de taxa só é procurado no JSON do ESearch e em respostas que não são 200, o EFetch pede só o que falta e o conector caiu para 615 linhas. Integrada com os gates refeitos pelo `board integrate`. Acompanhamento: o registrador `httpx` grava a URL completa (com `api_key` e e-mail) em nível INFO, se alguém ligar esse nível; vale para todas as fontes.
