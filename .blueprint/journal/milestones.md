# Marcos

Uma linha por marco, o mais novo por último.

| Data | Marco | O que significa |
|---|---|---|
| 2026-11-02 | Descrição do sistema pronta | O escopo da primeira versão está definido: servidor MCP com OpenAlex, Crossref e Semantic Scholar, exportando para o VOSviewer |
| 2026-11-02 | Pesquisa inicial e primeira decisão registradas | Há base para os Requisitos: o que o VOSviewer aceita, o estado das APIs, os MCPs existentes, e o Python decidido |
| 2026-11-02 | Requisitos prontos | O que a primeira versão precisa fazer e o critério de aceite estão escritos; dá para modelar jornadas, dados e chamadas do MCP |
| 2026-11-02 | Casos de uso prontos | As três jornadas que não podem dar errado estão escritas, com o que acontece quando algo falha |
| 2026-11-02 | Modelo de dados pronto | Está definido o que o sistema guarda (log, listas, artigos e cache) e as regras que não podem quebrar |
| 2026-11-02 | Contrato das chamadas pronto | As oito ferramentas e o prompt do servidor estão definidos, e a busca roda direto, sem etapa de aprovação |
| 2026-11-02 | Modelagem fechada | Referências, citações e todos os dados dos autores entram na primeira versão; o projeto passa a guardar dados pessoais públicos, com classificação escrita |
| 2026-11-02 | Stack escolhida | SDK oficial `mcp` 2.x, arquivos soltos para listas, log e cache, e instalação por PyPI com uvx |
| 2026-11-02 | Arquitetura pronta | Servidor stdio em Python, núcleo do zero, arquivos soltos, instalação por uvx, e o custo de referências e citações limitado; falta o plano |
| 2026-11-02 | Plano e repositório prontos | Seis fases, 16 tarefas com spec, arquivo de entrada para os agentes e memória do Lore nomeada; falta começar a codar |
| 2026-11-03 | Fase 1 · Esqueleto entregue para teste | O pacote instala, o servidor MCP responde por stdio com `list_sources` e o armazenamento grava buscas, listas, log e cache; falta o Erick testar e marcar como pronta |
| 2026-11-03 | Fase 2 · Fatia completa entregue para teste | Uma busca no OpenAlex vira lista sem duplicatas, entra no log e no cache, e a lista exporta em RIS; falta o Erick fazer a busca real e abrir o RIS no VOSviewer |
| 2026-11-03 | Fase 3 · Mais fontes entregue para teste | Uma busca consulta OpenAlex, Crossref e Semantic Scholar em paralelo e devolve uma lista sem duplicatas, com o estado de cada fonte e as divergências no log; falta o Erick testar com as chaves reais |
| 2026-11-03 | Fase 4 · Referências e citações entregue para teste | As referências de uma lista viram DOI em lotes de 100 com cache, e `get_related_works` traz referências ou citações de um artigo numa lista própria, com teto e motivo no log; falta o Erick testar com as chaves reais |
