# Contrato das chamadas

**Projeto:** RSL.app · **Versão:** 0.1 · **Data:** 2026-11-02

> **Em resumo:** O servidor MCP oferece nove ferramentas (oito até a 1.1; `merge_lists` desde a 1.2) e um prompt à IA do pesquisador, por stdio, na máquina do usuário.
> Toda busca roda direto, sem etapa de aprovação, e gera uma lista própria e uma entrada no log.
> A promessa que não pode quebrar: nenhuma lista incompleta sai como se fosse completa.

## Quem chama

| Quem | Como chama | O que espera |
|---|---|---|
| A IA do pesquisador (cliente MCP) | Chamadas de ferramenta e um prompt, por stdio (`uvx rslapp`, ou o app desktop com `--mcp` desde a 2.1, D-028) ou por HTTP no modo hospedado (D-011) | Listas já deduplicadas, com o estado de cada fonte, e arquivos prontos para exportar |
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
| `merge_lists` | Junta listas salvas numa lista nova, sem duplicatas (D-021, desde a 1.2) | `list_ids` | Uma lista nova, com `merged_from` e `duplicates_removed` |
| `export_list` | Grava a lista num arquivo (FR-06, FR-12) | `list_id` e `format` | O caminho do arquivo gravado |
| `list_sources` | Diz quais fontes estão configuradas e prontas (FR-07) | Nada | Uma linha por fonte |
| `verify_references` | Confere referências contra alucinação no Crossref e OpenAlex (FR-21, D-030) | `references`, `doi`, `bibtex` | Classificação de cada item (verified, divergent, not_found) |
| `import_works` | Importa arquivos externos RIS, BibTeX, Scopus e WoS (FR-23, D-033) | `content`, `format`, `list_name` | Lista nova com registros deduplicados e log |
| `screen_work` | Registra decisão de triagem com rastro de autoria humano vs IA (FR-25, D-036) | `list_id`, `work_id`, `decision` | Decisão gravada e resumo estatístico atualizado |
| `get_screening_status` | Resumo quantitativo e motivos da triagem de uma lista (FR-25, D-036) | `list_id` | Totais de incluídos, excluídos, pendentes e motivos |
| `get_prisma_flow` | Quantitativos PRISMA 2020 e checklist PRISMA-S (FR-26, D-037) | `list_id`, `include_svg` | Dados das 4 fases, checklist PRISMA-S e SVG opcional |
| `get_ai_disclosure` | Declaração metodológica de uso de IA COPE/ICMJE/SciELO (FR-27, D-038) | `list_id`, `language` | Texto formal pronto para a metodologia em PT ou EN |
| `export_reproducibility_package` | Pacote de reprodutibilidade em .zip com manifesto SHA-256 (FR-28, D-039) | `list_id` | Caminho do arquivo zip, tamanho e hash SHA-256 |
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
| `sources` | As fontes a consultar: `openalex`, `crossref`, `semantic_scholar`, `bdtd`, `pubmed`, `europe_pmc`, `scopus`, `web_of_science` | não | `openalex`, `crossref` e `semantic_scholar`; as outras só quando pedidas (D-020, desde a 1.2; BDTD desde a 2.3, D-035). `scopus` e `web_of_science` só funcionam no RSL.app instalado no computador, com as chaves e o acesso de quem usa; no modo hospedado dão `invalid_input` (D-023, desde a 1.3) |
| `max_results` | O máximo de artigos a trazer por fonte | não | definido no spec |
| `include_peer_review` | Incluir os pareceres de revisão por pares (tipo `peer-review`, como os do Publons). Só `true` ou `false`: um número dá `invalid_input` | não | `false`: os pareceres ficam de fora (D-022, desde a 1.3) |

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

Desde a 1.3, quando `include_peer_review` é falso, a entrada de uma fonte em `sources` pode trazer `excluded_peer_review` com quantos pareceres saíram. `found` e `fetched` contam antes da remoção, e o `total` da lista conta depois.

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
| `sources` | As fontes a consultar: `openalex`, `crossref`, `semantic_scholar` (`pubmed`, `europe_pmc`, `scopus` e `web_of_science` dão `invalid_input`, D-020 e D-023) | não | todas as configuradas |
| `max_results` | O máximo de trabalhos a trazer por fonte; a lista juntada pode passar disso (Erick, 2026-11-05) | não | 1.000 (D-010) |

**Volta:** o mesmo formato de `search_works`. O log guarda o artigo de origem e a direção.
**Quando falha:** uma fonte que não entrega referências ou citações aparece com `not_supported`.

## `export_list`

```
export_list(list_id="l-0001", format="ris")
```

| Entrada | O que é | Obrigatório | Padrão |
|---|---|---|---|
| `list_id` | A lista a exportar | sim | - |
| `format` | `ris`, `csv`, `json`, `dois`, `openalex_url` ou `bibtex` (desde a 1.2) | sim | - |

**Volta:** `{"path": "…/l-0001.ris", "format": "ris", "count": 187}`. Em `openalex_url`, volta também `url`.
Se o formato precisa de DOI nas referências, o servidor troca os ids por DOI nesse momento, o que pode gastar cota (T-005).
O arquivo é gravado numa pasta configurável da máquina do usuário. O `json` é o formato completo, e foi deduzido para guardar o que RIS e CSV levam só em parte.
**Quando falha:** `format_not_available` (por exemplo, `openalex_url` numa lista que não veio do OpenAlex), `empty_list` (lista sem artigos; nenhum arquivo é gravado) ou `export_folder_not_writable`.

## Modo HTTP (v2, fase 8)

O `rslapp serve` oferece as mesmas ferramentas e o mesmo prompt, com os mesmos nomes, entradas e campos, por HTTP em `/mcp`, com login OAuth (D-015). As diferenças:

- **Login:** toda chamada a `/mcp` precisa de um token de acesso OAuth. Sem token, ou com um token inválido ou de pessoa revogada, a resposta é 401, antes de qualquer ferramenta.
- **Dados por pessoa:** cada pessoa logada vê só as próprias buscas, listas e log. Um `list_id` de outra pessoa dá `list_not_found` (D-012).
- **`export_list`:** devolve `download_url` (link que vale 1 hora) e `expires_at`, e não devolve `path` (D-014). No stdio, nada muda.
- **`get_search_log`** (desde a 1.2): devolve `log_download_url` e `expires_at`, um link que vale o mesmo tempo e baixa o `log.md` da pessoa, e não devolve `log_file`. No stdio, nada muda.
- **Exportações antigas** (desde a 1.2): os arquivos exportados ficam no servidor por `RSL_EXPORT_RETENTION_HOURS` (padrão 24 horas) e depois são apagados na exportação seguinte da mesma pessoa.

## As outras chamadas

| Chamada | Entrada | Volta |
|---|---|---|
| `find_work` | `title` ou `doi` (um é obrigatório); `request_summary`, `sources` opcionais (sem `bdtd`, `pubmed`, `europe_pmc`, `scopus` e `web_of_science`) | Como `search_works` |
| `repeat_search` | `search_id` (obrigatório) | Como `search_works`, mais `repeated_from`. Repete com as mesmas fontes e o mesmo `include_peer_review` (uma busca anterior à 1.3 repete com `false`). Uma junção (`merge_lists`) não pode ser repetida |
| `merge_lists` | `list_ids` (2 a 20, obrigatório); `request_summary` opcional | Como `search_works`, sem `sources`, mais `merged_from`, `duplicates_removed` e, quando incompleta, `incomplete_from` |
| `get_list` | `list_id` (obrigatório); `page`, `page_size` e `detail` (`summary` ou `full`, padrão `summary`) | `works`, `page`, `next_page`, `total`, `status` |
| `get_search_log` | `search_id` e `limit`, ambos opcionais | `entries` e `log_file` (o caminho do arquivo legível) |
| `list_sources` | Nada | Por fonte: `name`, `configured`, `needs_key`, `status`. Desde a 1.2, também `pubmed` e `europe_pmc`. Desde a 1.3, `scopus` e `web_of_science`. Desde a 2.3, `bdtd` (D-035) |
| `screen_work` | `list_id`, `work_id`, `decision` (obrigatórios); `reason`, `decided_by`, `stage`, `notes`, `doi` (opcionais, desde a 2.4, D-036) | Decisão gravada em `screening/{list_id}.json` e resumo da triagem atualizado |
| `get_screening_status` | `list_id` (obrigatório, desde a 2.4, D-036) | Resumo com total, triados, pendentes, decisões, motivos e autoria |
| `get_prisma_flow` | `list_id` (obrigatório); `include_svg` (opcional, desde a 2.4, D-037) | Quantitativos das 4 fases PRISMA 2020, checklist PRISMA-S e SVG vetorial |
| `get_ai_disclosure` | `list_id` (obrigatório); `language` (opcional, desde a 2.4, D-038) | Declaração metodológica de uso de IA (padrão COPE/ICMJE/SciELO) em PT ou EN |
| `export_reproducibility_package` | `list_id` (obrigatório); `export_dir` (opcional, desde a 2.5, D-039) | Gera `.zip` autocontido com os 11 arquivos da revisão e manifesto `checksums.sha256` |
| `save_work_note` | `list_id`, `work_id` (obrigatórios); campos analíticos, `source` (`ai_suggested`, `human_reviewed`), `ai_model` (desde a 2.6, D-040) | Ficha científica gravada em `notes/{list_id}/{work_id}.json` |
| `get_work_note` | `list_id`, `work_id` (obrigatórios, desde a 2.6, D-040) | Ficha científica detalhada com rastro de autoria |
| `list_work_notes` | `list_id` (obrigatório, desde a 2.6, D-040) | Lista de todas as fichas científicas registradas para a lista |
| `export_notes_markdown` | `list_id` (obrigatório); `export_dir` (opcional, desde a 2.6, D-040) | Arquivo Markdown compilado pronto para Obsidian/Logseq |
| `save_protocol` | `title`, `question` (obrigatórios); `framework` (PICO, PCC, PICo, SPIDER, Narrativo), componentes, critérios, fontes, estratégia (desde a 2.7, D-041) | Protocolo salvo com ID único, versão incrementada e versão anterior arquivada |
| `get_protocol` | `protocol_id` (obrigatório); `version` (opcional, desde a 2.7, D-041) | Protocolo metodológico detalhado (versão atual ou histórica) |
| `list_protocols` | Nada (desde a 2.7, D-041) | Lista de protocolos ativos com contagem, status e datas de atualização |
| `export_protocol_markdown` | `protocol_id` (obrigatório); `version`, `output_path` (opcionais, desde a 2.7, D-041) | Documento Markdown formatado para submissão no PROSPERO/OSF ou anexo de tese |
| `export_network` | `list_id` (obrigatório); `network_type` (`coauthorship`, `source_coupling`, `keyword_cooccurrence`), `format` (`vosviewer`, `gephi`, `json`), `min_node_weight`, `min_edge_weight`, `max_nodes`, `output_path` (desde a 2.8, D-042) | Exporta rede bibliométrica em arquivos nativos VOSviewer (.map e .network), Gephi (.gexf) ou JSON |
| `compare_search_versions` | `base_list_id`, `new_list_id` (obrigatórios, desde a 2.9, D-043) | Compara duas versões de busca da Revisão Viva, retornando novos artigos, mantidos e relatório textual em Markdown |
| `update_search_differential` | `list_id` (obrigatório, desde a 2.9, D-043) | Reexecuta a busca de uma lista existente preservando triagens e notas, e detecta novos artigos publicados |
| `lookup_descriptors` | `query` (obrigatório); `lang` (`pt`, `en`, `es`, padrão `pt`), `max_results` (desde a 2.10, D-044) | Consulta descritores controlados DeCS/MeSH em 3 línguas com sinônimos autorizados |
| `build_multilingual_search_query` | `descriptors` (obrigatório); `operator` (`OR` ou `AND`, padrão `OR`) (desde a 2.10, D-044) | Gera blocos booleanos de busca prontos para cada idioma (PT, EN, ES) a partir dos descritores e seus sinônimos |
| `plan_search` | `request` (obrigatório) | Orientação em texto: separar o que é melhor buscado à parte, montar a string de cada fonte, chamar `search_works` uma vez por assunto e entregar cada lista separada |
| `plan_scoping_review` | `topic`, `population`, `concept`, `context` (desde a 2.3, D-035) | Roteiro metodológico JBI / PRISMA-ScR pelo framework PCC e literatura cinzenta |
| `plan_integrative_review` | `topic`, `guiding_question`, `theoretical_framework` (desde a 2.3, D-035) | Roteiro metodológico em 6 fases (Whittemore & Knafl / Mendes, Silveira e Galvão) |
| `plan_systematic_review` | `topic`, `population`, `intervention`, `comparison`, `outcome` (desde a 2.3, D-035) | Roteiro metodológico Cochrane / PRISMA 2020 com estratégia PICO |
| `plan_bibliometric_study` | `topic`, `analysis_type` (desde a 2.3, D-035) | Roteiro metodológico para VOSviewer com Leis de Bradford, Lotka e Zipf |

## Erros e estados

| Código | Quando | Onde aparece |
|---|---|---|
| `no_source_available` | Nenhuma fonte pode responder, por exemplo sem chave configurada | Erro da chamada |
| `invalid_input` | Falta uma entrada obrigatória ou o valor não vale, inclusive `true` ou `false` numa entrada numérica (`max_results`, `page`, `page_size`, `limit`); um número escrito como texto (`"2"`) é aceito | Erro da chamada |
| `list_not_found`, `search_not_found`, `work_not_found` | O id não existe | Erro da chamada |
| `format_not_available` | O formato não serve para aquela lista | Erro da chamada |
| `export_folder_not_writable` | A pasta de exportação não aceita gravação | Erro da chamada |
| `empty_list` | A lista não tem nenhum artigo, então não há o que exportar (Erick, 2026-11-05) | Erro da chamada |
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
- ~~Juntar listas de buscas diferentes.~~ Entrou na 1.2, com `merge_lists` (D-021).
- Abrir o VOSviewer. O servidor só grava o arquivo e devolve o caminho.
- Texto completo dos artigos.
