# Troca de ids de referências por DOI

**Fase:** 4 · Referências e citações · **Situação:** pronta

## O que faz

Um serviço no miolo, `core/references.py`, que troca os ids das referências (ids do OpenAlex, `W123`) por DOI, para a exportação ou a pedido. Usa o cache e agrupa os ids em chamadas de até 100. Os ids sem DOI continuam como ids. O resultado diz quantas chamadas foram feitas, se a troca ficou completa e, se não, por quê. A chamada à API fica num método novo do conector do OpenAlex.

## O que não faz

Não busca quem cita o artigo (04-02). Não troca ids na hora da busca (D-010). Não grava log nem lista: quem chama o serviço (a exportação, na 05-03, e a 04-02) decide o que registrar com o estado e o motivo devolvidos. Não mexe em `server.py`.

## Conferência do T-005 (OpenAlex)

Feita pelo Claude Code em 2026-11-03 na página oficial de filtros (`help.openalex.org/api/filtering/`) e com uma chamada real sem chave:

- O OR com `|` aceita **até 100 valores** num filtro.
- O filtro de ids do OpenAlex é `openalex` (a API o reescreve como `ids.openalex`). Aceita a forma curta: `GET /works?filter=openalex:W2741809807|W2755950973&select=id,doi&per_page=100`. A página de filtros não nomeia esse filtro; o nome foi confirmado na chamada real.
- Um id que não existe é simplesmente omitido do resultado, sem erro.
- O custo medido foi `cost_usd: 0.0001` por chamada (uma chamada de lista), com até 100 ids. Trocar as referências de 100 artigos com 40 referências cada (4.000 ids, menos os repetidos) custa no máximo 40 chamadas, ou US$ 0,004.
- O `doi` volta como URL (`https://doi.org/10.7717/peerj.4375`), e `null` quando o trabalho não tem DOI.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Na API:** `OpenAlexSource.lookup_dois(ids: list[str]) -> DoiLookup` em `sources/openalex.py`, reaproveitando a montagem de cabeçalhos, a chave no cabeçalho, as novas tentativas e os estados que já existem (`_request_page` e `_retry_failure`). `select=id,doi`, `per_page=100`, no máximo 100 ids por chamada. Nunca levanta exceção.
2. **No miolo:** `async def resolve_reference_dois(ids, *, store, source) -> ReferenceResolution` em `core/references.py`:
   - tira repetidos e ignora o que não é id do OpenAlex (por exemplo, um DOI que já veio da Crossref fica como está);
   - olha o cache por id (`store.get_cache("openalex_doi", {"id": "W123"})`), e só chama a API para os que faltam, em grupos de 100;
   - grava no cache cada id respondido, inclusive os sem DOI (`{"doi": null}`), para não perguntar de novo. Um id omitido pela API também vai para o cache como sem DOI;
   - devolve `mapping: dict[str, str | None]` (id → DOI minúsculo sem prefixo, ou `None`), `calls: int`, `from_cache: int`, `complete: bool` e `reason: str | None`.
3. **Falha no meio:** se um grupo falha (sem chave, limite, rede), os grupos já trocados ficam, os ids do grupo que falhou ficam como `None` **sem** ir para o cache, `complete` é falso e `reason` diz o estado e o motivo da fonte. Sem `OPENALEX_API_KEY`, nenhuma chamada é feita e `reason` diz `missing_key`.
4. **Dataclasses** `DoiLookup` (em `sources/openalex.py`) e `ReferenceResolution` (em `core/references.py`), com nomes de campo em inglês.

## Pronto quando

- [x] Antes de escrever, conferir o T-005 (feito acima pelo Claude Code)
- [x] Teste com respostas simuladas: uma lista de 120 ids vira DOI em 2 chamadas (100 e 20), cada chamada com o filtro `openalex:` e no máximo 100 ids; os ids sem DOI e os omitidos ficam `None`
- [x] Teste: ids repetidos e entradas que não são ids do OpenAlex não geram chamada
- [x] Teste: a segunda troca dos mesmos ids vem do cache e não gasta chamada (`calls == 0`)
- [x] Teste: se a segunda chamada falha, o resultado tem os DOIs da primeira, `complete` falso e o motivo; os ids do grupo que falhou não vão para o cache
- [x] Teste: sem chave, nenhuma chamada e `reason` com `missing_key`; com chave, ela vai só no cabeçalho
- [ ] Medida real, uma vez, com a chave do Erick: número de chamadas e créditos para trocar as referências de uma lista de 100 artigos, anotado no T-005. **É do Erick**

## Vem de

FR-14, NFR-01, NFR-03, D-005, D-010. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-01 integrada.

## Resultado da entrega

- **O que mudou:**
  - Em `src/rslapp/sources/openalex.py`: adicionadas a dataclass `DoiLookup` e o método `OpenAlexSource.lookup_dois(ids)` para consulta em lote de DOIs (filtro `openalex:W1|W2...`, `select=id,doi`, `per_page=100`, até 100 ids por chamada). Reutiliza `_request_page` com retentativas (429, 5xx) e autenticação via cabeçalho `Authorization: Bearer <chave>`. Nunca propaga exceção.
  - Em `src/rslapp/core/references.py`: implementados o serviço `resolve_reference_dois(ids, *, store, source)` e a dataclass `ReferenceResolution`. Filtra e deduplica ids do OpenAlex, consulta o cache em `store.get_cache("openalex_doi", {"id": "W123"})`, agrupa os faltantes em lotes de até 100 e grava no cache cada id respondido (inclusive nulos e omitidos). Em caso de falha de lote (rede, limite ou ausência de chave), preserva os DOIs já obtidos, isola o lote falho sem poluir o cache e marca `complete=False`. Sem chave configurada, não faz chamadas à rede e indica `missing_key`.
  - Em `tests/sources/test_openalex_dois.py`: 14 testes cobrindo consulta com parâmetros esperados, ids sem DOI e omitidos, envio exclusivo da chave no header (sem vazamento na URL), chave ausente ou com caracteres inválidos, tratamento de 429 com esgotamento de tentativas e créditos esgotados, captura de exceções e serialização da dataclass.
  - Em `tests/core/test_references.py`: 10 testes cobrindo resolução de 120 ids em 2 chamadas (100 e 20), deduplicação e descarte de entradas não-OpenAlex sem gerar chamadas, reaproveitamento integral do cache na segunda resolução (`calls == 0`), retenção dos DOIs do primeiro lote com isolamento do lote com erro sem gravar no cache, e comportamento sem chave configurada.
- **Requisitos atendidos:** FR-14, NFR-01, NFR-03, D-005, D-010.
- **O que foi assumido:** Ids de trabalho do OpenAlex seguem o padrão `W` seguido de dígitos (aceitando também URLs completas `https://openalex.org/W...` convertidas para id curto canônico). Entradas que não correspondem a esse padrão (como DOIs já existentes oriundos de outras fontes) são ignoradas sem disparar consultas à API do OpenAlex.
- **O que não deu para verificar:** A medida real com a chave do Erick para troca de 100 artigos (anotada no T-005), por ser uma atividade que depende da chave pessoal e execução manual dele.

## Como testar

- **Comandos:**
  ```bash
  uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/sources/test_openalex_dois.py tests/core/test_references.py -v
  uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
  uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
  uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
  ```
- **O que deve aparecer:**
  - 14 testes passando em `test_openalex_dois.py` e 10 testes passando em `test_references.py`.
  - 71 testes passando no pytest geral em Python 3.10 e em Python 3.14.
  - No ruff: `All checks passed!`.
- **Onde olhar primeiro (dois ou três pontos mais arriscados, o mais difícil primeiro):**
  1. *Segurança e confidencialidade da chave de API (NFR-03):* Em `tests/sources/test_openalex_dois.py` (`test_nfr03_lookup_dois_chave_apenas_no_header`) e `tests/core/test_references.py` (`test_nfr03_com_chave_vai_so_no_cabecalho`), certificar-se de que a chave viaja estritamente no cabeçalho `Authorization: Bearer <key>` e nunca aparece em query strings, URLs nem logs.
  2. *Isolamento do cache em falhas no meio da resolução (FR-14, D-007):* Em `tests/core/test_references.py` (`test_fr14_nfr04_falha_na_segunda_chamada`), verificar que, quando o segundo lote falha, os 100 ids do primeiro lote permanecem válidos e salvos no cache, enquanto nenhum dos 20 ids do lote que falhou é persistido no cache.
  3. *Agrupamento em lotes e economia de chamadas (NFR-01, D-010):* Em `tests/core/test_references.py` (`test_fr14_nfr01_resolve_120_ids_em_2_chamadas` e `test_nfr06_d007_segunda_troca_vem_do_cache`), conferir que 120 referências geram exatamente 2 chamadas de até 100 itens (`openalex:W...|W...`) e que a repetição imediata resulta em `calls == 0` com 100% de acerto no cache.

**Acompanhamentos da revisão (não bloqueiam):** `calls` conta consultas, não requisições HTTP (uma chave inválida conta 1; quatro tentativas num 429 contam 1). `lookup_dois` não valida o formato dos ids nem aceita mais de 100: quem chamar direto (04-02) precisa passar ids já limpos e em grupos de 100. Faltam testes da deduplicação no miolo com mais de 100 entradas e de `results` que não é lista.
