# Plano de testes

**Projeto:** RSL.app · **Versão:** 0.2 · **Data:** 2026-11-02

> **Em resumo:** Dez itens a conferir que a pesquisa e as decisões deixaram em aberto. Um foi descartado e nenhum foi verificado ainda.
> Eles pesam antes de codar os conectores e antes de decidir como exportar para o VOSviewer.

## A verificar

| # | O que verificar | Vem de | Como | Situação |
|---|---|---|---|---|
| T-001 | Limites, preços e campos de resposta das APIs do OpenAlex, Semantic Scholar e Crossref, e os formatos do VOSviewer, lidos nas páginas oficiais por inteiro | research.md | Abrir cada página oficial e conferir antes de implementar o conector | a fazer |
| T-002 | Custo em créditos por chamada do OpenAlex e cota diária com a chave gratuita | research.md | Consultar o endpoint de limite com uma chave real e medir uma busca típica; o Erick estima cerca de uma centena por semana | a fazer |
| T-003 | Parâmetros de linha de comando do VOSviewer na versão 1.6.21 | research.md | Rodar o VOSviewer com os parâmetros do manual e ver se abre e salva um mapa | descartado: o servidor não abre o VOSviewer (decisão do Erick em 2026-11-02) |
| T-004 | Existência de MCP comunitário do VOSviewer | research.md | Buscar no GitHub e no Glama por VOSviewer e MCP | a fazer |
| T-005 | Custo em chamadas e em créditos de trazer referências e citações: OpenAlex (`referenced_works`, filtro `cites`, resolução dos ids em DOI) e Semantic Scholar (limite de 1 por segundo e de 10 mil por consulta de citações) | D-005, research.md | Medir com uma chave real o número de chamadas para um artigo de 50 e um de 5 mil citações | a fazer |
| T-006 | Tamanho das respostas das ferramentas e paginação, para não encher o contexto da IA | D-002 | Rodar `search_works` com 100 e 500 artigos e medir o tamanho da resposta resumida e da completa | a fazer |
| T-007 | O que a LGPD exige de uma ferramenta local que guarda nome e ORCID públicos de autores | D-004, data-classification.md | O Erick consulta fonte jurídica ou um profissional; o agente não dá parecer jurídico | a fazer |
| T-008 | O que o VOSviewer lê de referências e citações em RIS, CSV e JSON, e se mapas de citação funcionam sem edição | D-005 | Exportar uma lista de teste e abrir no VOSviewer 1.6.21 | a fazer |
| T-009 | Nome da classe e exemplo de servidor stdio na documentação da versão 2 do SDK oficial do MCP | research.md | Abrir a documentação v2 em py.sdk.modelcontextprotocol.io e conferir antes de escrever o spec | a fazer |
| T-010 | Como o academic-research-mcp e o paper-search-mcp montam as consultas ao OpenAlex e à Semantic Scholar, e o que dá para reaproveitar na licença MIT | research.md | Ler o código dos dois no GitHub antes de escrever os conectores | a fazer |
