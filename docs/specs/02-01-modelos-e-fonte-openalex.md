# Modelos e fonte OpenAlex

**Fase:** 2 · Fatia completa · **Situação:** não iniciada

## O que faz

Os modelos do miolo (`Work`, `Author`, `Affiliation`, `SourceStatus`) em `core/models.py`, a interface comum das fontes em `sources/base.py` e o conector `sources/openalex.py`. O conector monta a consulta de busca, usa `per_page=100`, `select` para trazer só os campos necessários, a chave de API, e traduz o resultado para `Work`. Em cada autor guarda nome, ORCID, id do autor no OpenAlex e as afiliações com seus ids (incluindo o ROR). Guarda também as referências (`referenced_works`, como ids) e o número de citações (`cited_by_count`). Espera e tenta de novo (até 3 vezes, 1 s, 2 s, 4 s) em 429 e 500; trata a paginação básica, que para em 10 mil resultados; devolve o estado da fonte (`ok`, `failed`, `rate_limited`, `missing_key`) e quantos resultados a fonte disse ter e quantos foram trazidos.

## O que não faz

Não faz deduplicação, lista nem log (tarefa 02-02). Não traz citações de um artigo (tarefa 04-02). Não troca ids de referências por DOI (tarefa 04-01).

## Pronto quando

- [ ] Antes de escrever, conferir o T-001 para o OpenAlex: ler por inteiro as páginas oficiais de chave, custo, `select`, paginação e do objeto Work, e anotar no spec os campos usados e o que a página não detalha; ler o código do academic-research-mcp e do paper-search-mcp para essa fonte (T-010)
- [ ] Teste com respostas simuladas: título, DOI, ano, periódico, resumo (reconstruído do índice invertido do OpenAlex), palavras-chave, autores na ordem com ORCID e afiliações, ids das referências e contagem de citações são mapeados
- [ ] Teste: 429 e 500 provocam novas tentativas com espera crescente; esgotadas, a fonte devolve `rate_limited` ou `failed` com o motivo, sem exceção para o miolo
- [ ] Teste: sem `OPENALEX_API_KEY`, devolve `missing_key` sem chamar a API
- [ ] Teste: a chave não aparece em nenhum texto de log nem de erro
- [ ] Chamada real, uma vez, com a chave do Erick: uma busca de 100 trabalhos funciona; o custo medido é anotado no T-002

## Vem de

FR-01, FR-03, FR-14, NFR-01, NFR-03, NFR-04, NFR-05, D-004, D-010. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

T-001 (OpenAlex), T-002 e T-010. Depende de o Erick ter uma chave gratuita ativada (ver o plano).

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
