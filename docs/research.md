# Pesquisa

**Projeto:** RSL.app · **Versão:** 0.4 · **Data:** 2026-11-14

> **Em resumo:** Cinco perguntas pesquisadas em 2026-11-02.
> Não existe MCP do VOSviewer (a busca não foi exaustiva), e o VOSviewer já lê RIS, CSV, URL do OpenAlex e lista de DOIs, então a ponte é o exportador.
> Já existem vários MCPs de busca acadêmica; forkar ou começar do zero fica para a Arquitetura.
> A primeira versão usa OpenAlex, Crossref e Semantic Scholar. Scopus, Web of Science e CAPES dependem de licença ou de acesso institucional.
> Sci-Hub fica fora; o texto completo, quando entrar, vem de acesso aberto.
> Quatro perguntas de Arquitetura foram acrescentadas em 2026-11-02: biblioteca do MCP, onde guardar os dados, como instalar e quanto custam referências e citações. Nenhuma está decidida ainda.
> Em 2026-11-11, para a 2.0: o Scopus (visão COMPLETE) entra primeiro, só no modo stdio, com a chave de cada pessoa em variável de ambiente. O Web of Science Starter vem depois, como fonte magra. Nenhuma das duas entra no modo hospedado, por causa dos termos. As duas decisões estão em aberto, com o Erick.
> Em 2026-11-14, para o app desktop da 2.0: recomendado o NiceGUI em janela nativa, porque roda o núcleo assíncrono sem adaptação e a mesma interface serve no navegador. Decisão em aberto, com o Erick.

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
- Os dados do Crossref, do Web of Science Starter e do Scopus vêm de páginas de terceiros. (Scopus e Web of Science relidos nas páginas oficiais em 2026-11-11.)
- Os termos de produto das APIs da Clarivate (terms.clarivate.com) ficam atrás de uma verificação anti-robô e não foram lidos.
- Se as instituições que recebem o Scopus pelo Periódicos CAPES liberam a API pelo IP delas, e se a VPN da universidade conta como IP da instituição para a Elsevier.
- Se a visão COMPLETE do Scopus Search exige a assinatura (a página das visões não diz) e se as referências de cada artigo vêm pela Abstract Retrieval API com a mesma chave.

- (2026-11-14, app desktop) Se a janela nativa do NiceGUI abre num Linux comum (Ubuntu) sem instalar pacotes; tamanho do executável do `nicegui-pack` no Windows; se o `httpx` funciona com o `QtAsyncio` (só importa se a escolha for o PySide6).
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

## Scopus e Web of Science na 2.0: com qual API e dentro de quais termos?

- **Decisão:** em aberto, com o Erick. Recomendo começar pelo Scopus Search API, na visão COMPLETE, e deixar o Web of Science Starter para depois, como fonte mais magra. Os dois só no modo stdio, na máquina de quem tem acesso pela instituição.
- **Motivo:** o critério é ser gratuito para o pesquisador e cumprir os termos de cada base.
  - O Scopus devolve o que a revisão sistemática usa: todos os autores com ORCID, afiliações, resumo e palavras-chave.
  - O Starter não traz resumo, afiliações nem referências.
  - Nenhum dos dois permite servir os dados a quem é de fora da organização, o que exclui o modo hospedado.
- **Fatos, Scopus (Elsevier):**
  - **Chave:** o pesquisador registra uma chave gratuita no portal da Elsevier. "An API key alone does not provide data or content access": os dados dependem da assinatura da instituição.
  - **Fora do campus:** a Elsevier confere a assinatura pelo IP de quem chama. Fora da rede da instituição, a Elsevier dá um token institucional (`insttoken`) a pedido, e "API access through proxies is not supported".
  - **Scopus Search API:** 20.000 pedidos por semana e 9 por segundo. A visão STANDARD traz até 200 resultados por pedido; a COMPLETE, até 25. Sem paginação por cursor, o limite é de 5.000 itens.
  - **Visão STANDARD:** só o primeiro autor, sem resumo e sem palavras-chave.
  - **Visão COMPLETE:** todos os autores com `authid`, ORCID e afiliação, o resumo (`dc:description`), as palavras-chave dos autores e o número de citações.
  - **Uso "Academic Research" da política:**
    - os dados guardados servem para arquivo e para reproduzir o resultado da pesquisa;
    - só os campos da lista da política podem ser usados, entre eles ids, DOI, resumo, autores, afiliações, título, ano, fonte e citações;
    - "no 3rd party or consultant access is permitted";
    - o Scopus precisa aparecer como fonte dos dados.
  - **Para sites:** a chamada tem que sair do navegador de quem usa, sem passar por um servidor no meio.
- **Fatos, Web of Science (Clarivate):**
  - **Starter API, três planos:**
    - Free Trial: aberto a qualquer um, 1 pedido por segundo e 50 por dia, sem número de citações;
    - Free Institutional Member: para quem é de instituição assinante, 5 por segundo e 5.000 por dia, com citações;
    - Integration: 20.000 por dia, só para a equipe administrativa da instituição.
  - **Campos do Starter** (descrição OpenAPI): UID, título, fonte, ano, autores, palavras-chave dos autores, DOI, PubMed ID, tipo de documento e número de citações (conforme o plano), além de links para o Web of Science. Não traz resumo, afiliações nem a lista de referências. Até 50 registros por página, paginados por `page`. Aceita só parte das etiquetas da busca avançada (por exemplo TI, SO, PY).
  - **API Expanded:** exige licença paga da instituição. Traz o registro completo, com afiliações, citações e referências.
  - **Termos gerais de usuário da Clarivate (2018):**
    - o usuário não pode "provide Content to anyone else" fora dos documentos do próprio trabalho, nem prestar serviço a quem é de fora da organização;
    - sem licença de arquivo da instituição, não pode guardar o conteúdo baixado por mais de 3 meses;
    - pede o crédito "Source: Clarivate Analytics".
    - O contrato da instituição prevalece sobre esses termos.
- **Alternativas:**
  - Os dois agora: dobra o trabalho, e o Starter acrescenta pouco às fontes abertas.
  - Só o Web of Science: mais fraco nos campos e preso a 50 por dia sem vínculo institucional.
  - API Expanded do Web of Science: depende de licença paga, fora do critério de ser gratuito.
  - Oferecer no modo hospedado: contraria os termos das duas bases.
- **Fontes (lidas em 2026-11-11):**
  - https://dev.elsevier.com/policy.html (oficial)
  - https://dev.elsevier.com/api_key_settings.html (oficial)
  - https://dev.elsevier.com/sc_search_views.html (oficial)
  - https://dev.elsevier.com/sc_search_tips.html (oficial)
  - https://dev.elsevier.com/support.html (oficial)
  - https://developer.clarivate.com/apis/wos-starter (oficial)
  - https://developer.clarivate.com/apis/wos-starter/swagger (oficial, descrição OpenAPI)
  - https://developer.clarivate.com/apis/wos (oficial)
  - https://clarivate.com/wp-content/uploads/dlm_uploads/2019/08/End-User-Terms.pdf (oficial, termos gerais de 2018)

## Onde fica a chave de cada pessoa para o Scopus e o Web of Science?

- **Decisão:** em aberto, com o Erick. Recomendo variáveis de ambiente na configuração do cliente MCP de cada pessoa (`SCOPUS_API_KEY`, `SCOPUS_INSTTOKEN` opcional e `WOS_STARTER_API_KEY`), como já é com o OpenAlex. No modo hospedado, as duas fontes ficam indisponíveis.
- **Motivo:** o critério é não ter chave em arquivo do projeto e manter os dados na máquina de quem usa. As variáveis de ambiente já são o caminho do projeto (D-013) e ficam na máquina da pessoa. Os termos das duas bases proíbem servir os dados a terceiros, então o servidor hospedado não as oferece.
- **O que muda no código**, para a spec:
  - **Fora do modo hospedado:** `list_sources` mostra as duas como indisponíveis no modo hospedado.
  - **Cache:** o cache compartilhado não guarda respostas delas; no stdio, o cache é por pessoa e curto.
  - **Crédito à fonte:** o log e as exportações dizem "Fonte: Scopus" e "Source: Clarivate Analytics".
- **Alternativas:**
  - Guardar a chave no cofre do sistema (keyring): mais seguro, mas é dependência e passo de instalação novos, e diferente das outras chaves.
  - Cada pessoa cadastra a chave no servidor hospedado: contraria os termos.
- **Fontes:** as da pergunta anterior.

## Com qual biblioteca fazer a interface do app desktop (Windows e Linux)?

- **Decisão:** em aberto, com o Erick. Recomendo o **NiceGUI** em modo nativo (janela própria pelo pywebview), empacotado com `nicegui-pack` (PyInstaller).
- **Motivo:** o núcleo do RSL.app é assíncrono (`async def` com `httpx`), e o NiceGUI roda sobre o asyncio, então chama o núcleo direto, sem adaptação (critério: reaproveitar o núcleo em Python, um desenvolvedor com agentes). A mesma interface também roda no navegador, o que serve depois ao servidor do projeto. Licença MIT, igual à do projeto.
- **Alternativas:**
  - **PySide6 (Qt):** a mais madura, com ferramenta oficial de empacotamento (`pyside6-deploy`) e janelas sem dependência do sistema no Linux. Mas o `QtAsyncio` está em prévia técnica e não cobre conexões de rede, então o núcleo rodaria numa thread à parte ou com o `qasync`, de terceiros. Licença LGPL/GPL e executável grande.
  - **Flet 1.x:** interface em Flutter, assíncrona, Apache-2.0. O `flet build` baixa o SDK do Flutter e precisa ser rodado em cada sistema; a 1.0 saiu em 2026-09-14 e mudou a API, então os exemplos que os modelos conhecem são da 0.x.
  - **Toga (BeeWare):** BSD, ainda na versão 0.5.7; menos componentes de tabela e lista prontos. Não aprofundado.
- **Fatos principais (PyPI, 2026-11-14):** NiceGUI 4.0.0 (2026-11-04, MIT, Python 3.11+); PySide6 6.12.0 (LGPL-3.0/GPL, Python 3.10 a 3.15); Flet 1.1.2 (2026-11-06, Apache-2.0, Python 3.10+); Toga 0.5.7 (BSD-3, Python 3.11+); pywebview 6.2.1 (BSD-3).
- **Cuidados com o NiceGUI:**
  - Exige Python 3.11+; o servidor MCP continua aceitando 3.10, então o app desktop seria um extra ou um pacote à parte (decidir na spec).
  - A 4.0 é recente: como no `mcp` 2.x, ler a documentação da 4.0 antes de escrever (T-009).
  - No Linux, a janela nativa precisa do WebKitGTK ou de Qt no sistema; sem eles, o app abre no navegador.
- **Fontes (lidas em 2026-11-14):**
  - https://pypi.org/project/nicegui/ (oficial)
  - https://nicegui.io/documentation/section_configuration_deployment (oficial)
  - https://pypi.org/project/PySide6/ (oficial)
  - https://doc.qt.io/qtforpython-6/deployment/index.html (oficial)
  - https://doc.qt.io/qtforpython-6/PySide6/QtAsyncio/index.html (oficial)
  - https://pypi.org/project/flet/ (oficial)
  - https://flet.dev/docs/publish/ (oficial)
  - API JSON do PyPI para toga, flet, nicegui, pyside6 e pywebview (oficial)
