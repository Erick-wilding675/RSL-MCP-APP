# Pesquisa

**Projeto:** RSL.app · **Versão:** 0.2 · **Data:** 2026-11-02

> **Em resumo:** Cinco perguntas pesquisadas em 2026-11-02.
> Não existe MCP do VOSviewer (a busca não foi exaustiva), e o VOSviewer já lê RIS, CSV, URL do OpenAlex e lista de DOIs, então a ponte é o exportador.
> Já existem vários MCPs de busca acadêmica; forkar ou começar do zero fica para a Arquitetura.
> A primeira versão usa OpenAlex, Crossref e Semantic Scholar. Scopus, Web of Science e CAPES dependem de licença ou de acesso institucional.
> Sci-Hub fica fora; o texto completo, quando entrar, vem de acesso aberto.
> Quatro perguntas de Arquitetura foram acrescentadas em 2026-11-02: biblioteca do MCP, onde guardar os dados, como instalar e quanto custam referências e citações. Nenhuma está decidida ainda.

## Existe um MCP do VOSviewer, oficial ou da comunidade, para conectar ao nosso?

- **Decisão:** recomendado não depender de um MCP do VOSviewer e exportar nos formatos que ele já lê. Aceito pelo Erick em 2026-11-02 junto com o plano.
- **Motivo:** a busca "VOSviewer MCP server" não achou nenhum. O VOSviewer já aceita arquivos e consultas por API, então a ponte é o exportador, e ele serve também para outras ferramentas (critério: abrir caminho para outras ferramentas além do VOSviewer).
- **Alternativas:** escrever um MCP próprio para o VOSviewer, que só repetiria o que os arquivos e as URLs já fazem. O único resultado próximo foi um MCP de NetworkX que se apresenta como alternativa ao VOSviewer, não como ponte.
- **Fontes:**
  - Busca "VOSviewer MCP server", 2026-11-02, sem resultado do VOSviewer.
  - NetworkX MCP Server, https://glama.ai/mcp/servers/ku5sdbcpxo (diretório de terceiros), lido em 2026-11-02.

## Em que formatos e por quais caminhos o VOSviewer recebe dados?

- **Decisão:** exportar RIS (o formato geral), CSV, a URL de consulta do OpenAlex e a lista de DOIs. Mais tarde, arquivos map e network ou um link do VOSviewer Online.
- **Motivo:** são os caminhos de entrada que a documentação descreve, e cobrem os dois usos do Erick: levar a lista como arquivo ou deixar o VOSviewer buscar sozinho.
- **Alternativas:**
  - Arquivos de bases pagas (Scopus, Web of Science, Dimensions): ficam para depois, por exigirem licença.
  - Parâmetros de linha de comando do VOSviewer: existem no manual antigo (1.5.2), não verificados na versão atual.
- **Fatos principais:**
  - VOSviewer 1.6.21, lançada em 2026-06-12, melhorou a consulta ao OpenAlex, com suporte a chave de API.
  - Pelo OpenAlex, o usuário cola a URL da consulta no VOSviewer. O limite é de 50 mil registros por análise.
  - Com uma lista de DOIs, o VOSviewer busca os metadados pelo Crossref.
  - O VOSviewer Online abre redes por link, com os parâmetros json, map e network.
- **Fontes (lidas em 2026-11-02):**
  - https://help.openalex.org/how-to/integrations/ (oficial do OpenAlex)
  - https://vosviewer.com/ (oficial)
  - https://app.vosviewer.com/docs/sharing/linking/ (oficial)
  - https://www.vosviewer.com/documentation/Manual_VOSviewer_1.5.2.pdf (oficial, manual antigo)
  - https://www.griffith.edu.au/__data/assets/pdf_file/0030/1905483/VOSviewer-guide-2023.pdf (guia de universidade, terceiro)

## Que MCPs de busca acadêmica já existem?

- **Decisão:** em aberto. Forkar, contribuir ou construir o núcleo do zero será decidido na Arquitetura.
- **Motivo:** os existentes cobrem a busca em várias fontes. O academic-research-mcp, por exemplo, já traz 25 ferramentas, gestão de revisão sistemática e contagens PRISMA. Falta olhar o código e a licença de cada um para saber se vale reaproveitar.
- **Alternativas:**
  - academic-research-mcp (9 APIs, licença MIT, informada pela página do PyPI)
  - paper-search-mcp (dezenas de fontes)
  - cyanheads/openalex-mcp-server (só OpenAlex, com prompt de revisão sistemática)
  - Um MCP de descoberta e triagem em OpenAlex, Semantic Scholar e arXiv
- **Fontes (todas de terceiros, lidas em 2026-11-02):**
  - https://pypi.org/project/academic-research-mcp/
  - https://mcpservers.org/pt-BR/servers/openags/paper-search-mcp
  - https://mcpservers.org/ru/servers/cyanheads/openalex-mcp-server
  - https://glama.ai/mcp/servers/yjizu0u0pm

## Quais bases entram na primeira versão, dado o acesso de cada API?

- **Decisão:** OpenAlex, Crossref e Semantic Scholar. Recomendado e aceito pelo Erick em 2026-11-02.
- **Motivo:** o critério é ser gratuito e sem fins comerciais. Essas são as que não pedem licença nem acesso institucional.
- **Alternativas, por base:**
  - OpenAlex: chave gratuita obrigatória desde 2026-02-13. Acima da cota diária cobra por uso. A documentação cita US$ 0,10 por dia sem chave e US$ 1 por dia com chave gratuita, e recomenda per_page=100.
  - Semantic Scholar: a chave dá 1 requisição por segundo. Sem chave, o pool é compartilhado e devolve muitos erros 429.
  - Crossref: sem chave, cerca de 50 requisições por segundo na fila educada (dado de uma página de terceiro).
  - Scopus: chave gratuita para uso acadêmico não comercial, mas os dados dependem da assinatura da instituição e pode ser exigido um token institucional. O acesso não pode ser repassado a quem é de fora da organização. Fica para depois.
  - Web of Science: o plano Starter de teste dá 50 requisições por dia e não traz contagem de citações (dado de um guia de biblioteca). A Expanded exige licença paga. Fica para depois.
  - Periódicos CAPES: não achei API pública. O acesso é por rede institucional ou CAFe. Útil para texto completo, não para metadados.
- **Fontes (lidas em 2026-11-02):**
  - https://developers.openalex.org/api-reference/authentication.md (oficial)
  - https://groups.google.com/g/openalex-users/c/rI1GIAySpVQ (anúncio oficial na lista de usuários)
  - https://semanticscholar.org/product/api (oficial)
  - https://developer.clarivate.com/apis/wos (oficial)
  - https://www.gov.br/capes/pt-br/acesso-a-informacao/perguntas-frequentes/programas-e-bolsas-no-pais (oficial)
  - https://www.casrai.org/guides/using-the-scopus-api (terceiro)
  - https://libguides.csiro.au/TDM/API (guia de biblioteca, terceiro, cita as condições da Elsevier)
  - https://libanswers.suss.edu.sg/faq/278467 (guia de biblioteca, terceiro)
  - https://pypi.org/project/academic-research-mcp/ (terceiro, para o Crossref)

## Como obter texto completo sem o Sci-Hub?

- **Decisão:** Sci-Hub fica fora do projeto. O texto completo não entra na primeira versão. Quando entrar, vem de acesso aberto e, para quem tem acesso, do Periódicos CAPES via CAFe. Plano aceito pelo Erick em 2026-11-02.
- **Motivo:** o Sci-Hub distribui artigos pagos sem autorização das editoras, e o uso não comercial não muda isso. As bases abertas já informam links de cópias abertas, o que cobre boa parte do caso.
- **Alternativas:** links de PDF aberto do OpenAlex (via Unpaywall) e do Semantic Scholar; CORE, Europe PMC, PMC e arXiv; Periódicos CAPES via CAFe, que o doutorando provavelmente já tem.
- **Fontes (lidas em 2026-11-02):**
  - https://help.openalex.org/how-to/integrations/ (oficial)
  - https://www.gov.br/capes/pt-br/acesso-a-informacao/perguntas-frequentes/programas-e-bolsas-no-pais (oficial)
  - https://mcpservers.org/pt-BR/servers/openags/paper-search-mcp (terceiro, lista das fontes abertas)

## Não verificado

- As fontes foram lidas pelos trechos que a busca devolveu, não pelas páginas completas. As páginas oficiais devem ser lidas por inteiro antes de implementar cada conector.
- Cotas, preços e créditos do OpenAlex e limites do Semantic Scholar mudam. Conferir na hora de codar.
- Parâmetros de linha de comando do VOSviewer na versão atual: não testados.
- A busca por MCP do VOSviewer não foi exaustiva. Conferir GitHub e Glama.
- Os dados do Crossref, do Web of Science Starter e do Scopus vêm de páginas de terceiros.

## Qual biblioteca usar para o servidor MCP em Python?

- **Decisão:** SDK oficial `mcp`, linha 2.x (`mcp>=2,<3`), recomendado e escolhido pelo Erick em 2026-11-02 (D-006).
- **Motivo:** o critério é um desenvolvedor só, com agentes, e projeto gratuito de longo prazo. O SDK oficial é mantido pela organização do MCP, é o que `pip install mcp` instala hoje, e cobre ferramentas, prompts e stdio, que é o que o contrato das chamadas precisa.
- **Alternativas:**
  - SDK oficial na linha 1.x, com `mcp<2`: estável, mas só recebe correções críticas. É a linha em que a classe se chama `FastMCP`, e a maioria dos exemplos antigos usa essa forma.
  - Pacote independente `fastmcp` (PrefectHQ), hoje na versão 4: acrescenta composição de servidores, proxy e geração a partir de OpenAPI, que o projeto não precisa. É um pacote a mais para acompanhar.
- **Fatos principais:**
  - A documentação oficial da linha 1.x diz que a v2 é a versão estável atual e que, para ficar na 1.x, se usa `mcp<2`.
  - A página oficial do PyPI da 1.29.1 (24 de agosto de 2026) exige Python 3.10 ou mais e tem licença MIT. Diz que `pip install mcp` instala a 2.x.
  - Um artigo de terceiros (testes de 5 de outubro de 2026) diz que a v2 renomeou a classe `FastMCP` para `MCPServer` e removeu o caminho `mcp.server.fastmcp`, e que o `fastmcp` 4.x e o SDK usam a mesma biblioteca de base.
- **Não verificado:** o nome da classe na v2 vem só desse artigo; a documentação oficial da v2 não foi aberta (T-009). Como o Gemini escreve o código, o spec precisa trazer o import exato, porque o que ele aprendeu é quase todo da 1.x.
- **Fontes (lidas em 2026-11-02):**
  - https://py.sdk.modelcontextprotocol.io/v1/ (oficial)
  - https://pypi.org/project/mcp/1.29.1/ (oficial)
  - https://www.agenticwire.news/article/fastmcp-vs-mcp-python-sdk (terceiro)
  - https://mcp.directory/blog/fastmcp-vs-fastapi-mcp-vs-python-sdk-2026 (terceiro, de maio de 2026; fala da v2 do `fastmcp`, não da v2 do SDK)

## Onde guardar as listas, o log e o cache?

- **Decisão:** só arquivos soltos (D-007). Eu havia recomendado um banco SQLite num único arquivo mais um log legível em Markdown; o Erick escolheu a outra opção em 2026-11-02.
- **Motivo:** o critério é rodar na máquina do usuário sem instalar nada. O SQLite vem com o Python, dá consulta, paginação e prazo de cache sem esforço, e um arquivo só é fácil de copiar. O log legível é um pedido do Erick (FR-13) e fica à parte, para anexar na metodologia.
- **Alternativas:**
  - Só arquivos: um JSON por lista, um arquivo de log e um de cache. Simples de abrir e copiar, mas paginar, achar duplicatas e expirar o cache vira código à mão.
  - SQLite para tudo e o log gerado sob demanda: um só lugar para os dados, mas o log deixa de ser um arquivo que existe sozinho e cresce junto com as buscas.
- **Risco:** o log e o banco podem divergir se a gravação falhar no meio. O spec precisa gravar os dois na mesma etapa e dizer qual vale em caso de diferença.
- **Não pesquisado em fonte:** que o `sqlite3` faz parte da biblioteca padrão do Python é conhecimento geral; vale conferir na documentação do Python ao escrever o spec.

## Como instalar e distribuir o servidor?

- **Decisão:** publicar no PyPI e instalar com `uvx`, recomendado e escolhido pelo Erick em 2026-11-02 (D-008).
- **Motivo:** o critério é instalar sem mexer no código (FR-07) e rodar na máquina do usuário. Com `uvx`, a configuração do cliente MCP leva uma linha de comando e as dependências ficam isoladas. Publicar no PyPI é gratuito.
- **Alternativas:**
  - `pip` ou `pipx` em um ambiente próprio: funciona, mas o usuário cuida do ambiente e aponta a configuração para o Python certo.
  - Docker: isola tudo, mas é pesado para um servidor stdio local e complica a gravação das exportações na pasta do usuário.
- **Fatos principais (de um artigo de terceiros):**
  - `uvx` roda um pacote do PyPI num ambiente isolado. A configuração do Claude Desktop usa `"command": "uvx"`, o nome do pacote em `args` e as chaves em `env`.
  - Pede Python 3.10 ou mais e uv 0.4 ou mais.
  - No Windows, o `uvx` costuma funcionar sem embrulho; em clientes com interface, o PATH pode não achar o `uvx`, e a saída é pôr o caminho completo na configuração.
- **Não verificado:** o artigo não explica como publicar o pacote nem como definir o comando de entrada. Isso entra no spec e se confere na documentação do uv e do PyPI.
- **Fontes (lida em 2026-11-02):** https://www.rapidevelopers.com/mcp-tutorial/how-to-use-uvx-to-run-python-mcp-servers (terceiro)

## Quanto custa buscar referências e citações?

- **Decisão:** referências no registro, citações sob demanda, com teto (D-010). Recomendado e escolhido pelo Erick em 2026-11-02. O que entra já estava decidido em D-005.
- **Fatos principais:**
  - OpenAlex: a chamada de lista custa US$ 0,0001, a busca com `search` US$ 0,001 e a leitura de um trabalho avulso é grátis. O orçamento é de US$ 1 por dia com chave gratuita. `per_page` vai até 100, e a paginação básica para em 10 mil resultados. Os campos `referenced_works`, `referenced_works_count` e `cited_by_count` e o filtro `cites` existem; a página lida não detalha o uso de `cites`.
  - OpenAlex: `authorships.author.orcid` e `authorships.institutions.ror` existem como campos de filtro. Os ids das referências vêm no registro do trabalho; trocá-los por DOI exige mais chamadas (a conferir no T-005).
  - Semantic Scholar: a consulta de citações exige `offset + limit` abaixo de 10 mil, e acima disso a API devolve erro 400. A consulta em lote aceita até 500 ids. Sem chave, as medições de terceiros mostraram muitos erros 429.
- **Contas aproximadas (cálculo meu, sobre os preços acima):** com US$ 1 por dia dá para 10 mil chamadas de lista ou mil buscas por dia. Uma centena por semana cabe com folga, mesmo trazendo referências e citações. O limite real é o de 1 por segundo da Semantic Scholar e os 10 mil por artigo.
- **Não verificado:** os números são de páginas lidas hoje e mudam. O custo real por artigo é o T-005.
- **Fontes (lidas em 2026-11-02):**
  - https://help.openalex.org/api/llm-quick-reference/ (oficial)
  - https://developers.openalex.org/api-reference/works.md (oficial, só filtros)
  - https://www.casrai.org/guides/semantic-scholar-api (terceiro, com medições de 26 de agosto de 2026)

## Forkar um MCP acadêmico existente ou começar do zero?

- **Decisão:** começar do zero, usando os dois mais próximos como referência de código (ambos são MIT). Recomendado e escolhido pelo Erick em 2026-11-02 (D-009).
- **Motivo:** o critério é o rigor da revisão e o controle de um desenvolvedor só. O que o Erick pediu muda o miolo: uma lista imutável por busca, um log só de acréscimo e legível, o estado de cada fonte com lista marcada como incompleta, listas próprias de referências e citações, e exportação para o VOSviewer. Nenhum dos dois traz isso pronto, e adaptar o miolo de outro projeto custa mais do que escrever o nosso.
- **Alternativas:**
  - Forkar o academic-research-mcp (MIT, versão 0.2.0 de 30 de agosto de 2026, 25 ferramentas, 9 APIs): é o mais próximo, com log de buscas, deduplicação por DOI e título e citações pela Semantic Scholar. Guarda tudo em SQLite, o que contraria D-007, a falha por fonte não está documentada, exporta lista de DOIs e dados para o Zotero (sem RIS nem CSV) e tem só duas versões publicadas.
  - Usar o paper-search-mcp (MIT, Python, cerca de 2,5 mil estrelas, mais de 20 fontes) como base: a página diz que citações e referências ainda são uma tarefa por fazer, não menciona RIS nem CSV, e traz um conector opcional do Sci-Hub, que o projeto exclui.
  - Contribuir com um deles em vez de manter o nosso: dependeria do ritmo e das escolhas do mantenedor.
- **Não verificado:** li as páginas dos projetos, não o código. Vale ler como cada um monta as consultas ao OpenAlex e à Semantic Scholar antes de escrever os conectores (T-010).
- **Fontes (lidas em 2026-11-02):**
  - https://pypi.org/project/academic-research-mcp/ (terceiro)
  - https://github.com/openags/paper-search-mcp (terceiro)
