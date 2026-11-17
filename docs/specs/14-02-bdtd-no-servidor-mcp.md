# BDTD no Servidor MCP, Deduplicação e Exportação

**Fase:** 14 · Versão 2.3 · **Situação:** pronta

## O que faz

Integra o conector BDTD ao servidor MCP (`search_works`, `list_sources`), à deduplicação de listas e à exportação CSV:
- Disponibiliza `"bdtd"` em `list_sources` como fonte aberta (`needs_key=False`, `status="ok"`), disponível tanto no modo stdio quanto no modo HTTP/hospedado.
- Permite solicitar `"bdtd"` no parâmetro `sources` de `search_works`.
- Atualiza as orientações para IA em `src/rslapp/prompts.py` e nos docstrings das ferramentas para indicar BDTD em buscas de literatura cinzenta, teses e dissertações nacionais.
- Garante prioridade na deduplicação em `src/rslapp/core/dedup.py`.
- Adiciona a coluna `BDTD ID` no exportador CSV (`src/rslapp/exporters/csv.py`).

## O que não faz

- Não dá suporte a `find_work` nem a `get_related_works` para BDTD (assim como PubMed e Europe PMC, que são apenas de busca).
- Não altera a interface do Desktop (isso fica na tarefa 14-04).

## Decisões desta spec

1. **Prioridade na deduplicação (`SOURCE_PRIORITY`):** BDTD entra após as bases de periódicos com DOI estabelecido (`openalex`, `crossref`, `semantic_scholar`, `pubmed`, `europe_pmc`, `scopus`, `web_of_science`, `bdtd`). Quando uma tese gera um artigo posterior já indexado nas bases globais, o artigo principal preserva o DOI e incorpora o ID da BDTD em `source_ids`.
2. **Disponibilidade no modo hospedado:** Sendo uma base aberta governamental mantida pelo IBICT (sem custo de API nem credenciais privadas), a BDTD fica liberada no modo hospedado/HTTP assim como OpenAlex, Crossref, Semantic Scholar, Europe PMC e PubMed.
3. **Restrição em `find_work` e `get_related_works`:** Como a BDTD não possui endpoints de rede de citação nem busca por DOI exato com resolução global, chamadas com `source="bdtd"` são recusadas com mensagem clara informando as fontes suportadas.

## Pronto quando

- [x] `SourceName` em `sources/__init__.py` inclui `"bdtd"`.
- [x] `build_sources` e `list_sources_info` instanciam e listam BDTD.
- [x] `SOURCE_PRIORITY` em `core/dedup.py` inclui `"bdtd"`.
- [x] `search_works` no servidor MCP aceita `"bdtd"` em `sources`.
- [x] `find_work` e `get_related_works` recusam `"bdtd"` com mensagem amigável.
- [x] `BDTD ID` incluído nas colunas do exportador CSV.
- [x] Prompts do sistema e instruções do MCP atualizados mencionando literatura cinzenta/teses.
- [x] Testes do servidor e de deduplicação atualizados e passando.
- [x] Todos os gates passam (Ruff limpo, testes em Python 3.10 e 3.14).
