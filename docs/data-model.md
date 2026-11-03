# Modelo de dados

**Projeto:** RSL.app · **Versão:** 0.4 · **Data:** 2026-11-02

> **Em resumo:** O sistema guarda quatro coisas na máquina do usuário: o log de buscas, as listas de resultados, os artigos de cada lista e um cache das respostas das APIs.
> Tudo fica em arquivos soltos numa pasta de dados (D-007). Cada artigo leva todos os dados dos autores, as referências e as citações, porque são eles que ligam os registros entre si.
> Uma busca gera uma lista, e a lista nunca muda depois de criada. O log só cresce. As chaves de API nunca entram em nada disso.

## O que é guardado

| O quê | O que contém | Quantos, mais ou menos |
|---|---|---|
| Busca (entrada do log) | O pedido, as strings enviadas a cada base e o resultado de cada fonte | Uma por busca |
| Lista | Os artigos que uma busca devolveu, já sem duplicatas | Uma por busca |
| Artigo | Os metadados de um artigo dentro de uma lista, com autores, referências e citações | De dezenas a algumas centenas por lista |
| Resposta em cache | A resposta de uma API a uma consulta | Milhares |

## Como se relacionam

```
Busca 1 ──── 1 Lista 1 ──── N Artigo
  ├─ repetida_de ──> outra Busca (opcional)
  └─ artigo_base ──> um Artigo de outra Lista (nas buscas de referências e citações)

Resposta em cache: independente. As buscas a consultam antes de chamar a API.
```

## Busca (entrada do log)

| Campo | O que é | Obrigatório | Regra |
|---|---|---|---|
| id | Identificador da busca | sim | Único, nunca muda |
| criada_em | Data e hora da busca, em UTC | sim | - |
| tipo | termos, artigo, relacionados ou repeticao | sim | Deduzido; diz qual chamada gerou a busca |
| pedido | O que o pesquisador pediu, em linguagem natural, resumido pela IA | não | Deduzido, para o log ser interpretável |
| fontes | Para cada fonte consultada: a string ou a URL enviada, quantos resultados a fonte disse ter encontrado, quantos o servidor trouxe, o estado (ok, failed, rate_limited, missing_key ou not_supported), o motivo quando não foi ok e se a resposta veio do cache | sim | Uma linha por fonte. "Encontrados" e "trazidos" são deduzidos: sem eles não se sabe se a lista foi cortada |
| artigo_base | Nas buscas do tipo relacionados: o artigo de origem e a direção (referencias ou citacoes) | não | Deduzido |
| lista_id | A lista que a busca gerou | sim | - |
| repetida_de | O id da busca original, quando esta repete outra | não | FR-11 |

**Dados pessoais:** o campo pedido pode ter texto livre do pesquisador. Fica só na máquina dele.

## Lista

| Campo | O que é | Obrigatório | Regra |
|---|---|---|---|
| id | Identificador da lista | sim | Único, nunca muda |
| busca_id | A busca que gerou a lista | sim | Uma busca, uma lista |
| criada_em | Data e hora, em UTC | sim | - |
| situacao | completa ou incompleta | sim | Incompleta se alguma fonte falhou ou atingiu o limite (FR-08) |
| total | Número de artigos depois de tirar as duplicatas | sim | - |

**Situações:** completa e incompleta. A lista não muda de situação depois de criada. Repetir a busca cria outra lista.

## Artigo

| Campo | O que é | Obrigatório | Regra |
|---|---|---|---|
| doi | O DOI do artigo | não | Quando existe, é único dentro da lista (FR-04) |
| titulo | Título | sim | - |
| autores | Lista ordenada. Cada autor tem nome (obrigatório), ORCID, identificadores do autor em cada fonte e afiliações (nome e os identificadores que a fonte trouxer, como o ROR) | sim | Todos os dados de autor que a fonte trouxer entram (D-004). Os coautores são os autores depois do primeiro |
| ano | Ano de publicação | não | - |
| periodico | Periódico ou evento | não | - |
| resumo | Resumo | não | - |
| palavras_chave | Palavras-chave | não | - |
| referencias | Identificadores dos trabalhos que o artigo cita, como a fonte entrega (no OpenAlex, ids do OpenAlex) e o DOI quando já se conhece | não | D-005, D-010. Ids viram DOI na exportação ou a pedido. Fica vazio quando nenhuma fonte entrega, e o log diz por quê. Nunca é preenchido com valor suposto |
| citacoes | Número de citações recebidas, por fonte | não | D-005. Os números diferem de uma fonte para outra, por isso não são somados |
| fontes | As fontes em que o artigo apareceu, com o id dele em cada uma | sim | - |

Os campos opcionais vêm preenchidos quando a fonte tiver o dado (FR-03). A lista de quem cita um artigo não fica dentro do artigo: vira uma lista própria, pedida à parte (FR-15).

**Dados pessoais:** nomes, ORCID, identificadores de autor e afiliações. Ver `data-classification.md`.

## Resposta em cache

| Campo | O que é | Obrigatório | Regra |
|---|---|---|---|
| fonte | A API consultada | sim | - |
| consulta | A requisição, normalizada | sim | Fonte mais consulta formam a chave |
| resposta | O que a API devolveu | sim | - |
| obtida_em | Quando a resposta foi obtida | sim | - |
| expira_em | Quando deixa de valer | sim | O prazo é definido na Arquitetura |

## Regras que valem para todos

- Uma busca gera exatamente uma lista, e a lista nunca é alterada. Repetir uma busca cria busca e lista novas (FR-09, FR-11).
- O log só cresce. Nenhuma entrada é apagada nem reescrita (FR-05, FR-11).
- O log é legível por pessoas, para poder ser anexado na metodologia (FR-13).
- Um artigo aparece uma vez por lista. A chave é o DOI e, sem DOI, o título normalizado. O detalhe fica no spec (FR-04).
- Uma lista é incompleta se alguma fonte falhou, e o log diz qual (FR-08).
- Quando uma fonte não entrega referências ou citações, o log diz not_supported e o campo fica vazio (FR-14).
- O que veio do cache fica marcado no log, com a data em que a resposta foi obtida (NFR-06).
- As chaves de API nunca entram no log, nas listas nem no cache (NFR-03).

## O que não é guardado

- Chaves de API. Ficam na configuração local do usuário, fora destes dados.
- Texto completo dos artigos.
- Listas que juntam buscas diferentes (decisão do Erick em 2026-11-02).

## Pontos em aberto

| Nº | Ponto | Depende de |
|---|---|---|
| 1 | Lista exata de campos obrigatórios | Spec das tarefas |
| 2 | Prazo de expiração do cache, formato do log legível, nomes e estrutura dos arquivos na pasta de dados, e como a gravação evita arquivo pela metade | Arquitetura |
