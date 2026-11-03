# Decisões

Todas as decisões do projeto, num só lugar, a mais nova por último. Uma decisão nunca é reescrita: quando muda, uma nova entrada a substitui e diz qual.

## D-001 · Linguagem do projeto: Python

- **Decisão:** tudo em Python: o núcleo, o servidor MCP e, depois, o app desktop.
- **Motivo:** critério declarado pelo Erick. Perguntei entre Python e TypeScript e ele respondeu "vamos fazer tudo em Python".
- **Alternativas:** TypeScript, que é a linguagem de vários MCPs que já existem. Ficou de fora pela escolha do Erick.
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** -
- **Situação:** decidida
- **A testar:** -

## D-002 · Chamadas do servidor MCP

- **Decisão:** o servidor oferece oito ferramentas (`search_works`, `find_work`, `get_related_works`, `repeat_search`, `get_list`, `get_search_log`, `export_list`, `list_sources`) e um prompt (`plan_search`). O servidor grava as exportações numa pasta configurável da máquina e devolve o caminho. O contrato está em `interface-contract.md`.
- **Motivo:** o Erick aprovou a lista de chamadas ("ótimas") e seguiu a recomendação para a pasta de exportação. A ferramenta `get_related_works` foi acrescentada depois, por causa de D-005.
- **Alternativas:** nenhuma foi pedida.
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** -
- **Situação:** decidida
- **A testar:** T-006 (tamanho das respostas e paginação)

## D-003 · A busca roda direto, sem etapa de aprovação

- **Decisão:** a IA roda a busca direto, sempre, sem mostrar as strings ao pesquisador antes. O log guarda tudo o que foi enviado.
- **Motivo:** o Erick escolheu rodar direto ("roda direto, sempre"). Eu havia perguntado se a IA devia mostrar as strings e esperar aprovação.
- **Alternativas:** aprovar as strings antes de rodar, que deixaria o pesquisador revisar a busca antes de gastar cota.
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** -
- **Situação:** decidida
- **A testar:** -

## D-004 · Todos os dados dos autores entram

- **Decisão:** de cada autor entram todos os dados que a fonte oferecer: nome, ORCID, identificadores nas fontes e afiliações.
- **Motivo:** o Erick disse que esses dados são essenciais para ligar os registros entre si e formar os nós das redes. O projeto passa a guardar dados pessoais públicos; o tratamento está em `data-classification.md`.
- **Alternativas:** guardar só nome e ORCID, ou só o nome. Ficaram de fora pela escolha do Erick.
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** -
- **Situação:** decidida
- **A testar:** T-007 (o que a LGPD exige neste caso)

## D-005 · Referências e citações entram na primeira versão

- **Decisão:** cada artigo traz as referências e as citações, e o servidor busca as referências ou as citações de um artigo como lista própria (FR-14, FR-15).
- **Motivo:** o Erick disse que é crucial ter esses dados. O custo em cota é o risco: a Semantic Scholar limita a consulta de citações a 10 mil por artigo e o OpenAlex tem orçamento diário em dinheiro.
- **Alternativas:** deixar para uma versão posterior, ou trazer só a contagem de citações. Ficaram de fora pela escolha do Erick.
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** research.md, seção "Quanto custa buscar referências e citações?"
- **Situação:** decidida
- **A testar:** T-005 (custo em chamadas), T-008 (o que o VOSviewer lê de referências)

## D-006 · Biblioteca do servidor MCP: SDK oficial `mcp`, linha 2.x

- **Decisão:** o servidor usa o SDK oficial `mcp` na linha 2.x (`mcp>=2,<3`).
- **Motivo:** o Erick seguiu a recomendação. Critério: um desenvolvedor só, com agentes, e projeto gratuito de longo prazo; é o SDK mantido pela organização do MCP e o que `pip install mcp` instala hoje.
- **Alternativas:** SDK oficial 1.x com `mcp<2` (só correções críticas); pacote independente `fastmcp` 4.x (traz recursos que o projeto não usa).
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** research.md, seção "Qual biblioteca usar para o servidor MCP em Python?"
- **Situação:** decidida
- **A testar:** T-009 (nome da classe e exemplo stdio na documentação da v2)

## D-007 · Armazenamento: só arquivos

- **Decisão:** listas, log e cache ficam em arquivos soltos numa pasta de dados configurável: um JSON por lista, um arquivo de log legível e arquivos de cache. Não há banco de dados.
- **Motivo:** o Erick escolheu contra a recomendação (SQLite mais log em Markdown) e não deu motivo. A leitura que fiz: arquivos são fáceis de abrir, copiar e anexar. O que ele assume: paginação, duplicatas e prazo do cache passam a ser código nosso, e o spec precisa tratar gravação interrompida.
- **Alternativas:** SQLite num arquivo só com log legível à parte (recomendada); SQLite para tudo, com o log gerado sob demanda.
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** research.md, seção "Onde guardar as listas, o log e o cache?"
- **Situação:** decidida
- **A testar:** T-006 (tamanho das respostas e paginação) e o desempenho do cache com muitos arquivos, quando o cache passar de alguns milhares de respostas

## D-008 · Instalação: PyPI com `uvx`

- **Decisão:** o pacote é publicado no PyPI e instalado com `uvx`, com uma linha de comando na configuração do cliente MCP.
- **Motivo:** o Erick seguiu a recomendação. Critério: instalar sem mexer no código (FR-07), rodar na máquina do usuário e isolar as dependências.
- **Alternativas:** `pip` ou `pipx` em ambiente próprio; Docker.
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** research.md, seção "Como instalar e distribuir o servidor?"
- **Situação:** decidida
- **A testar:** como publicar o pacote e definir o comando de entrada (documentação do uv e do PyPI); o caminho completo do `uvx` em clientes com interface

## D-009 · Núcleo escrito do zero, com os MCPs existentes como referência

- **Decisão:** o núcleo do servidor é escrito do zero. Os MCPs acadêmicos existentes (academic-research-mcp e paper-search-mcp, ambos MIT) servem de referência de código, com o aviso de licença quando algum trecho for aproveitado.
- **Motivo:** o Erick seguiu a recomendação. Critério: o rigor da revisão e o controle de um desenvolvedor só. Lista imutável por busca, log legível de acréscimo, estado por fonte e listas de referências e citações mudam o miolo, e nenhum dos dois traz isso pronto.
- **Alternativas:** forkar o academic-research-mcp (guarda em SQLite, exporta DOIs e Zotero, sem RIS nem CSV); usar o paper-search-mcp como base (citações ainda por fazer, traz conector do Sci-Hub); contribuir com um deles.
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** research.md, seção "Forkar um MCP acadêmico existente ou começar do zero?"
- **Situação:** decidida
- **A testar:** T-010 (ler o código dos dois antes de escrever os conectores). Se o código mudar a conta, a decisão volta ao Erick

## D-010 · Referências no registro, citações sob demanda, com teto

- **Decisão:** as referências que o OpenAlex entrega no registro do trabalho (ids) e o número de citações entram em toda lista. Quem cita o artigo e as referências vindas da Semantic Scholar só vêm pela ferramenta `get_related_works`, com teto de 1.000 trabalhos por lista (ajustável). Se o teto ou o limite da fonte cortar a lista, ela sai incompleta e o log diz o motivo. Os ids viram DOI só na exportação ou a pedido.
- **Motivo:** o Erick seguiu a recomendação. Critério: orçamento zero e nada suposto. O OpenAlex entrega as referências sem chamada extra, e a Semantic Scholar, a 1 por segundo, tornaria a busca lenta demais se completasse tudo na hora.
- **Alternativas:** completar tudo na hora da busca (busca de minutos e gasto proporcional à lista); só contagens, com o resto sob demanda (deixa referências fora do registro).
- **Decidido por:** Erick · **Data:** 2026-11-02
- **Fontes:** research.md, seção "Quanto custa buscar referências e citações?"
- **Situação:** decidida
- **A testar:** T-005 (se o OpenAlex troca muitos ids por DOI numa chamada, e a que custo). Se o custo for maior que o previsto, volta ao Erick com novas opções
