# Contrato das chamadas

**Projeto:** RSL.app · **Versão:** 0.1 · **Data:** 2026-11-02

> **Em resumo:** O servidor MCP oferece oito ferramentas e um prompt à IA do pesquisador, por stdio, na máquina do usuário.
> Toda busca roda direto, sem etapa de aprovação, e gera uma lista própria e uma entrada no log.
> A promessa que não pode quebrar: nenhuma lista incompleta sai como se fosse completa.

## Quem chama

| Quem | Como chama | O que espera |
|---|---|---|
| A IA do pesquisador (cliente MCP) | Chamadas de ferramenta e um prompt, por stdio | Listas já deduplicadas, com o estado de cada fonte, e arquivos prontos para exportar |
| O pesquisador | Só por meio da IA | Nada além do que a IA mostra |

## O que é oferecido

| O quê | O que faz | O que precisa | O que volta |
|---|---|---|---|
| `search_works` | Busca por tema, palavra-chave, subtema ou título nas fontes (FR-01) | `query` | Uma lista nova: `search_id`, `list_id`, `status`, estado de cada fonte e a primeira página |
| `find_work` | Acha um artigo específico por título ou DOI (FR-02) | `title` ou `doi` | Uma lista nova, com os candidatos |
| `get_related_works` | Traz as referências ou as citações de um artigo (FR-15) | `doi` ou `work_id`, e `direction` | Uma lista nova, ligada ao artigo de origem |
| `repeat_search` | Repete uma busca do log com as mesmas strings e bases (FR-11) | `search_id` | Uma lista nova, com `repeated_from` |
| `get_list` | Mostra uma lista salva, por páginas (FR-12) | `list_id` | A página pedida |
| `get_search_log` | Mostra entradas do log (FR-05, FR-13) | Nada | As entradas e o caminho do arquivo legível |
| `export_list` | Grava a lista num arquivo (FR-06, FR-12) | `list_id` e `format` | O caminho do arquivo gravado |
| `list_sources` | Diz quais fontes estão configuradas e prontas (FR-07) | Nada | Uma linha por fonte |
| `plan_search` (prompt) | Orienta a IA a planejar antes de buscar (FR-10) | `request` | O texto de orientação |

O servidor também entrega, na conexão, instruções curtas com a mesma orientação do `plan_search` (FR-10).

## `search_works`

```
search_works(
  query="machine learning interpretability",
  request_summary="Artigos sobre interpretabilidade de modelos de aprendizado de máquina",
  sources=["openalex", "semantic_scholar", "crossref"],
  max_results=100
)
```

| Entrada | O que é | Obrigatório | Padrão |
|---|---|---|---|
| `query` | Os termos técnicos da busca | sim | - |
| `request_summary` | O pedido do pesquisador, em linguagem natural, resumido (vai para o log) | não | vazio |
| `sources` | As fontes a consultar | não | todas as configuradas |
| `max_results` | O máximo de artigos a trazer por fonte | não | definido no spec |

**Volta:**

```
{
  "search_id": "s-0001",
  "list_id": "l-0001",
  "status": "incomplete",
  "total": 187,
  "page": 1,
  "next_page": 2,
  "sources": [
    {"name": "openalex", "status": "ok", "found": 412, "fetched": 100, "from_cache": false},
    {"name": "semantic_scholar", "status": "rate_limited", "reason": "HTTP 429"},
    {"name": "crossref", "status": "ok", "found": 230, "fetched": 100, "from_cache": true}
  ],
  "works": [
    {"doi": "10.1234/exemplo", "title": "…", "authors": ["…"], "year": 2024, "venue": "…",
     "references_count": 41, "citations": {"openalex": 17}}
  ]
}
```

A resposta à IA é um resumo (deduzido, para não encher o contexto da IA). O registro completo, com afiliações, identificadores e referências, fica salvo na lista e vai nas exportações. `get_list` aceita `detail="full"` para vê-lo.

**Quando falha:** uma fonte que falha não é erro. A busca segue, `status` vira `incomplete` e a fonte aparece em `sources` com o motivo (FR-08). Só é erro quando nada pode ser feito.

## `get_related_works`

```
get_related_works(doi="10.1234/exemplo", direction="citations", max_results=200)
```

| Entrada | O que é | Obrigatório | Padrão |
|---|---|---|---|
| `doi` ou `work_id` | O artigo de origem. Um dos dois | sim | - |
| `direction` | `references` (o que ele cita) ou `citations` (quem o cita) | sim | - |
| `request_summary` | O pedido, resumido | não | vazio |
| `sources` | As fontes a consultar | não | todas as configuradas |
| `max_results` | O máximo de trabalhos a trazer | não | 1.000 (D-010) |

**Volta:** o mesmo formato de `search_works`. O log guarda o artigo de origem e a direção.
**Quando falha:** uma fonte que não entrega referências ou citações aparece com `not_supported`.

## `export_list`

```
export_list(list_id="l-0001", format="ris")
```

| Entrada | O que é | Obrigatório | Padrão |
|---|---|---|---|
| `list_id` | A lista a exportar | sim | - |
| `format` | `ris`, `csv`, `json`, `dois` ou `openalex_url` | sim | - |

**Volta:** `{"path": "…/l-0001.ris", "format": "ris", "count": 187}`. Em `openalex_url`, volta também `url`.
Se o formato precisa de DOI nas referências, o servidor troca os ids por DOI nesse momento, o que pode gastar cota (T-005).
O arquivo é gravado numa pasta configurável da máquina do usuário. O `json` é o formato completo, e foi deduzido para guardar o que RIS e CSV levam só em parte.
**Quando falha:** `format_not_available` (por exemplo, `openalex_url` numa lista que não veio do OpenAlex) ou `export_folder_not_writable`.

## As outras chamadas

| Chamada | Entrada | Volta |
|---|---|---|
| `find_work` | `title` ou `doi` (um é obrigatório); `request_summary`, `sources` opcionais | Como `search_works` |
| `repeat_search` | `search_id` (obrigatório) | Como `search_works`, mais `repeated_from` |
| `get_list` | `list_id` (obrigatório); `page`, `page_size` e `detail` (`summary` ou `full`, padrão `summary`) | `works`, `page`, `next_page`, `total`, `status` |
| `get_search_log` | `search_id` e `limit`, ambos opcionais | `entries` e `log_file` (o caminho do arquivo legível) |
| `list_sources` | Nada | Por fonte: `name`, `configured`, `needs_key`, `status` |
| `plan_search` | `request` (obrigatório) | Orientação em texto: separar o que é melhor buscado à parte, montar a string de cada fonte, chamar `search_works` uma vez por assunto e entregar cada lista separada |

## Erros e estados

| Código | Quando | Onde aparece |
|---|---|---|
| `no_source_available` | Nenhuma fonte pode responder, por exemplo sem chave configurada | Erro da chamada |
| `invalid_input` | Falta uma entrada obrigatória ou o valor não vale | Erro da chamada |
| `list_not_found`, `search_not_found`, `work_not_found` | O id não existe | Erro da chamada |
| `format_not_available` | O formato não serve para aquela lista | Erro da chamada |
| `export_folder_not_writable` | A pasta de exportação não aceita gravação | Erro da chamada |
| `ok`, `failed`, `rate_limited`, `missing_key`, `not_supported` | O estado de uma fonte | Em `sources`, na resposta |

## O que não muda sem aviso

- Os nomes das ferramentas e do prompt.
- Os nomes das entradas e dos campos da resposta (`search_id`, `list_id`, `status`, `sources`, `works`).
- Os códigos de erro e os estados das fontes.
- Os nomes dos formatos de exportação.
- Os campos do log.

Mudar qualquer um desses quebra o que as IAs e os usuários já configuraram. É uma decisão difícil de desfazer.

## O que fica de fora

- Etapa de aprovação das strings antes de rodar. O Erick escolheu rodar direto, sempre (D-003). A garantia de rigor está no log.
- Juntar listas de buscas diferentes.
- Abrir o VOSviewer. O servidor só grava o arquivo e devolve o caminho.
- Texto completo dos artigos.
