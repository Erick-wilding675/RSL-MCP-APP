# Fonte Crossref

**Fase:** 3 · Mais fontes · **Situação:** não iniciada

## O que faz

O conector `sources/crossref.py` com a mesma interface do OpenAlex (`Source`, tarefa 02-01): busca por termos e traduz o resultado para `Work` (título, autores com ORCID quando houver, afiliações com ROR quando houver, ano, periódico, resumo, DOI, tipo, DOIs das referências, número de referências e de citações). Usa o `RSL_CONTACT_EMAIL`, quando houver, para entrar na fila educada, e respeita o limite com novas tentativas.

## O que não faz

Não consulta citações de um artigo (04-02). Não deduplica entre fontes (03-03). Não busca por título ou DOI exato (05-01). Não mexe em `server.py`: a Crossref entra nas fontes do servidor na 03-03.

## Conferência do T-001 (Crossref)

Lida pelo Claude Code em 2026-11-03: `crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/`, `…/tips-for-using-the-crossref-rest-api/`, o formato do Work em `github.com/CrossRef/rest-api-doc/api_format.md`, e uma chamada real sem chave a `api.crossref.org/works`.

- **Filas:** pública (sem identificação), educada (e-mail no parâmetro `mailto` ou no cabeçalho de agente) e Plus (paga, fora do projeto). A página dá 5 e 1 de concorrência para a pública e 10 e 3 para a educada, por intervalo informado no cabeçalho `x-rate-limit-interval`. A chamada real de 2026-11-03 veio da fila pública com `x-rate-limit-limit: 1`, `x-rate-limit-interval: 1s` e `x-concurrency-limit: 1`. Conclusão: **uma chamada por vez**, sempre.
- **Excesso:** 429; esperar e tentar de novo mais devagar. 403 é bloqueio manual (raro).
- **Recomendações oficiais:** `mailto` em toda chamada, `User-Agent` que identifique o programa, cache das respostas.
- **Busca:** `GET https://api.crossref.org/works?query=<termos>&rows=<n>&select=<campos>&cursor=*`. `rows` vai até 1.000 (usar 100). O cursor começa em `*` e segue com o `next-cursor` da resposta; para quando a página vem com menos itens que `rows`.
- **`select`** conferido na chamada real: `DOI,title,author,issued,container-title,abstract,reference,references-count,is-referenced-by-count,type`.
- **Envelope:** `{"status": "ok", "message-type": "work-list", "message": {"total-results", "items", "items-per-page", "next-cursor"}}`.
- **Work:** `DOI` (texto, sem URL), `title` (lista; usar o primeiro), `author` (lista de `given`, `family`, `ORCID` como URL, `sequence`, `affiliation` com `name` e, às vezes, `id` com `{"id": "https://ror.org/…", "id-type": "ROR"}`), `issued.date-parts` (`[[2020]]`, e pode vir `[[null]]`), `container-title` (lista), `abstract` (texto puro ou JATS XML, como `<jats:p>`), `reference` (lista; cada uma pode ter `DOI`), `references-count`, `is-referenced-by-count`, `type` (por exemplo `journal-article`, `dissertation`).
- **Não há palavras-chave por artigo.** `subject` é a área do periódico e quase sempre falta: **não** vira `keywords`.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Mapeamento:** `title` = primeiro de `title` (sem título, o item é descartado); `doi` minúsculo; `year` = primeiro número de `issued.date-parts` ou nulo; `venue` = primeiro de `container-title`; `abstract` sem as marcas JATS (só o texto, espaços simples); `keywords` vazio; `type` como veio; `authors` na ordem, com `name` = `given family` (ou só `family`, ou `name` quando for uma organização), `orcid` na forma curta, `position` = `sequence`, afiliações com `name` e `ids["ror"]` quando o `id-type` for ROR; `references` = DOIs (minúsculos) das referências que têm DOI; `references_count` = `references-count`; `citations` = `{"crossref": is-referenced-by-count}`; `source_ids` = `{"crossref": <doi>}`.
2. **O e-mail:** com `RSL_CONTACT_EMAIL`, vai no parâmetro `mailto`. Ele não entra no `query` do `SourceResult` (que vai para o log), nem na chave do cache, nem nos motivos de erro. O `User-Agent` é `rslapp/<versão>`, sem e-mail.
3. **Estados e novas tentativas** iguais aos do OpenAlex: 429, 5xx, tempo esgotado e erro de rede com até 3 novas tentativas (1, 2 e 4 s); esgotadas, `rate_limited` (429) ou `failed`; outras 4xx `failed` na hora; páginas já trazidas ficam. A Crossref não tem `missing_key`: `needs_key` é falso.
4. **Uma chamada por vez:** as páginas saem em sequência, nunca em paralelo.

## Pronto quando

- [x] Antes de escrever, conferir o T-001 para a Crossref (feito acima pelo Claude Code)
- [ ] Teste com respostas simuladas: os campos acima são mapeados, inclusive autor organização, ORCID em URL, afiliação com e sem ROR, `issued` com `[[null]]` e resumo em JATS; o que a Crossref não traz fica vazio, sem valor suposto
- [ ] Teste: paginação por cursor pede a página seguinte com o `next-cursor` e para em `max_results` ou quando a página vem menor que `rows`
- [ ] Teste: 429 e 5xx seguem a mesma regra de novas tentativas e estado do OpenAlex
- [ ] Teste: com `RSL_CONTACT_EMAIL`, a URL pedida leva `mailto`; o e-mail não aparece no `query`, no `reason` nem na chave do cache

## Vem de

FR-01, FR-03, FR-14, NFR-04, D-004. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-01 integrada. Roda em paralelo com a 02-02 e a 03-02.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
