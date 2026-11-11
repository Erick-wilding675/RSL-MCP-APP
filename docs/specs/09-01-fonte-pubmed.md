# Fonte PubMed

**Fase:** 9 · Versão 1.2 · **Situação:** a fazer

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
- [ ] Teste com respostas simuladas (`httpx.MockTransport`): os campos acima são mapeados, inclusive autor coletivo, ORCID em URL e só número, várias afiliações, resumo estruturado com `Label`, `MedlineDate`, DOI só em `ELocationID`, referências com e sem DOI e registro sem título descartado
- [ ] Teste: o ESearch pede `usehistory=y`, e o EFetch pede lotes de 200 pelo `WebEnv` até `max_results`
- [ ] Teste: 429, 5xx e a mensagem de limite seguem as novas tentativas e os estados acima
- [ ] Teste: com `NCBI_API_KEY` e `RSL_CONTACT_EMAIL`, a URL leva `api_key` e `email`; nenhum dos dois aparece em `query`, `reason` nem `cache_query`
- [ ] Teste: os pedidos saem um por vez, com o intervalo mínimo (relógio simulado no teste)
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

FR-01, FR-03, FR-14, NFR-03, NFR-04, D-004 e D-020. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/sources/crossref.py` e `tests/sources/test_crossref.py` inteiros: o PubMed segue o mesmo molde (estados, novas tentativas, e-mail fora do log, testes com `MockTransport`). Ler `src/rslapp/core/models.py` (`Work`, `Author`, `Affiliation`, `SourceResult`) e `src/rslapp/config.py` (como as chaves são lidas).

Cerca de 350 linhas, testes incluídos. Um commit para o conector e outro para os testes, com D-020 no comentário e no nome dos testes.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
