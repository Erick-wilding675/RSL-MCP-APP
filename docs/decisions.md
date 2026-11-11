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

## D-011 · Uso por link: modo HTTP e imagem Docker no próprio pacote, hospedados por quem quiser

- **Decisão:** o próximo passo para usar o RSL.app como conector por link (sem instalar nada na máquina de quem usa) é um modo HTTP opcional no próprio `rslapp`, com uma imagem Docker. Quem hospeda é quem quiser: um laboratório, uma universidade ou a própria pessoa. O projeto não mantém servidor próprio por enquanto. O modo stdio continua sendo o padrão.
- **Motivo:** o Erick escolheu a opção C, que eu recomendei. O modo HTTP é necessário em qualquer caminho de servidor remoto, não gera custo para o projeto e mantém os dados dos autores com quem hospeda (D-004). Um servidor do projeto traria custo, cota compartilhada ou login com chaves de terceiros, e dados pessoais num servidor.
- **Alternativas:** (A) servidor do projeto com a chave do projeto: o mais simples para quem usa, mas com custo, cota e abuso por conta do Erick; (B) servidor do projeto com a chave de cada pessoa: justo, mas exige login e guardar chaves de terceiros. As duas ficam para depois da C, com pesquisa de preços de hospedagem.
- **Decidido por:** Erick · **Data:** 2026-11-05
- **Fontes:** conversa de 2026-11-05 (Claude Code)
- **Situação:** decidida; entra no plano como próximo passo, sem spec ainda
- **A pensar na spec:** como entregar as exportações a quem está do outro lado da rede (link temporário ou conteúdo na resposta, já que o arquivo fica no servidor); de onde vêm as chaves num servidor compartilhado; autenticação do link; separação de listas e log por pessoa; o que a LGPD pede quando os dados de autores ficam num servidor de terceiros (T-007)

## D-012 · v2: acesso por token de cada pessoa, que também separa os dados

- **Decisão:** no modo HTTP, quem hospeda gera um token para cada pessoa e pode revogá-lo. O token identifica a pessoa, e as listas, o log e as exportações de cada uma ficam separados.
- **Motivo:** o Erick escolheu a opção que eu recomendei. É pouco código, deixa tirar uma pessoa sem afetar as outras e resolve a separação dos dados sem login de verdade.
- **Alternativas:** um token para todos (sem separação nem revogação individual); OAuth completo (funciona em qualquer cliente, mas é bem mais código e configuração); sem login (só numa rede fechada).
- **A conferir na spec:** pela documentação do Claude (claude.com/docs/connectors/custom/remote-mcp, lida em 2026-11-10), os cabeçalhos fixos ("Request headers") dos conectores estão em beta, só para algumas organizações; no plano Team ou Enterprise o Owner adiciona o conector e o cabeçalho vale para todos; para credencial por pessoa, a página recomenda OAuth. O Claude Code aceita `--header`. Por isso a spec precisa de um meio de levar o token que funcione sem cabeçalho.
- **Decidido por:** Erick · **Data:** 2026-11-10
- **Fontes:** conversa de 2026-11-10 (Claude Code)
- **Situação:** decidida

## D-013 · v2: as chaves de API são de quem hospeda

- **Decisão:** no modo HTTP, as chaves do OpenAlex e da Semantic Scholar ficam no servidor, configuradas por quem hospeda, e valem para todos os usuários do link.
- **Motivo:** o Erick escolheu a opção que eu recomendei. Quem usa o link não precisa criar chave nenhuma, que é o objetivo do uso por link. A cota do OpenAlex (10.000 créditos por dia; um dia de testes gastou 36) folga para um laboratório.
- **Alternativas:** cada pessoa manda a própria chave (mais justo com a cota, mas cada um precisa criar chave); as duas (mais código e teste).
- **Decidido por:** Erick · **Data:** 2026-11-10
- **Fontes:** conversa de 2026-11-10 (Claude Code)
- **Situação:** decidida

## D-014 · v2: exportação por link temporário

- **Decisão:** no modo HTTP, `export_list` grava o arquivo no servidor e devolve um link de download que vale 1 hora, ajustável por quem hospeda. A pessoa clica e baixa o arquivo para abrir no VOSviewer.
- **Motivo:** o Erick escolheu a opção que eu recomendei. A resposta à IA fica pequena, mesmo numa lista de 1.000 artigos, e o arquivo chega igual ao do modo stdio.
- **Alternativas:** o conteúdo do arquivo na resposta (sem rota extra, mas pesa no contexto da IA); os dois.
- **Decidido por:** Erick · **Data:** 2026-11-10
- **Fontes:** conversa de 2026-11-10 (Claude Code)
- **Situação:** decidida

## D-015 · v2: login por OAuth, com o código pessoal na tela de login

- **Decisão:** o modo HTTP é um servidor OAuth completo, com o SDK `mcp` 2.x: registro automático de clientes, autorização, token, renovação e revogação. Na tela de login, a pessoa digita o código pessoal que quem hospeda gerou para ela (D-016). O token por pessoa da D-012 vira esse código; a separação dos dados por pessoa continua.
- **Motivo:** o Erick escolheu OAuth contra a minha recomendação (token no cabeçalho ou na URL), porque a documentação do Claude diz que os cabeçalhos fixos dos conectores estão em beta e valem para a organização inteira no Team e no Enterprise, e recomenda OAuth para credencial por pessoa. Para a tela de login, escolheu o código pessoal, que eu recomendei: não depende de serviço de fora nem guarda e-mail.
- **Alternativas:** token no cabeçalho ou dentro da URL (pouco código, mas não funciona por pessoa em todos os planos do Claude, e o link pode vazar); só cabeçalho; login pelo Google ou pelo SSO da universidade (exige registrar app e guardar e-mails).
- **Decidido por:** Erick · **Data:** 2026-11-10
- **Fontes:** conversa de 2026-11-10 (Claude Code); claude.com/docs/connectors/custom/remote-mcp, lida em 2026-11-10
- **Situação:** decidida

## D-016 · v2: códigos pessoais criados e revogados por comando, sem prazo de sessão

- **Decisão:** quem hospeda gerencia as pessoas pelo comando `rslapp` (por exemplo, `token add`, `token list` e `token revoke`). O código aparece uma vez só, e o servidor guarda só o hash dele, em arquivo na pasta de dados (D-007). Depois do login, a sessão não tem prazo: vale até a pessoa ser revogada. Revogar só corta o acesso; apagar os dados da pessoa é um comando à parte, com confirmação.
- **Motivo:** o Erick escolheu o comando e a revogação sem apagar, que eu recomendei. Escolheu a sessão sem prazo contra a minha recomendação (30 dias renovando), por comodidade. Na spec, o token de acesso continua curto e renovado sozinho, sem prazo para a renovação, o que mantém a escolha dele e limita o estrago de um token de acesso vazado.
- **Alternativas:** códigos numa variável de ambiente (texto puro e reinício para revogar); sessão de 30 dias ou de 1 dia; revogar apagando tudo (um corte por engano perde a metodologia da pessoa).
- **Decidido por:** Erick · **Data:** 2026-11-10
- **Fontes:** conversa de 2026-11-10 (Claude Code)
- **Situação:** decidida

## D-017 · v2: imagem no ghcr.io e HTTPS pelo Caddy num docker-compose

- **Decisão:** o `rslapp` fala HTTP simples no modo hospedado. O projeto entrega um Dockerfile, um docker-compose com o Caddy na frente, que obtém e renova o certificado HTTPS para o domínio de quem hospeda, e publica a imagem no GitHub Container Registry (ghcr.io) por um GitHub Action a cada tag de versão.
- **Motivo:** o Erick escolheu as opções que eu recomendei. O Claude só aceita conector com link HTTPS, e o Caddy resolve o certificado sem código de segurança no projeto. O ghcr.io fica ao lado do código e dos releases e é gratuito para projeto público.
- **Alternativas:** só a imagem, com o HTTPS por conta de quem hospeda; HTTPS no próprio `rslapp`; imagem no Docker Hub (outra conta, limite de downloads); só o Dockerfile.
- **Decidido por:** Erick · **Data:** 2026-11-10
- **Fontes:** conversa de 2026-11-10 (Claude Code)
- **Situação:** decidida

## D-018 · v2: a LGPD (T-007) é conferida antes de divulgar o modo hospedado, não antes de codar

- **Decisão:** a v2 é escrita e testada sem esperar a T-007. Conferir a LGPD vira condição para anunciar o modo hospedado. O guia de hospedagem avisa que quem hospeda passa a tratar nomes, ORCID e afiliações de autores das buscas de outras pessoas, e mostra o comando que apaga os dados de uma pessoa (D-016).
- **Motivo:** o Erick escolheu a opção que eu recomendei: o código não depende da resposta jurídica, e travar a v2 até a consulta pararia o projeto.
- **Alternativas:** conferir a LGPD antes de escrever a spec da v2.
- **Decidido por:** Erick · **Data:** 2026-11-10
- **Fontes:** conversa de 2026-11-10 (Claude Code)
- **Situação:** decidida

## D-019 · Teste real da v2 numa máquina da Azure for Students, com nome do DuckDNS

- **Decisão:** o teste real da 08-07 roda numa máquina Linux pequena da Azure, paga com os créditos de estudante do Erick (US$ 100), com um nome gratuito do DuckDNS (por exemplo, `rsl-erick.duckdns.org`) apontado para o IP dela. A 1.1.0 é publicada antes do teste; se ele achar defeito, sai uma 1.1.1.
- **Motivo:** o Erick escolheu servidor alugado com os créditos e as opções que eu recomendei. A Azure for Students não pede cartão e desativa a conta quando o crédito acaba, sem cobrança surpresa. Os nomes gratuitos das nuvens não servem para o HTTPS: o Let's Encrypt recusa `*.compute.amazonaws.com`, e `cloudapp.azure.com` não está na Public Suffix List, então divide com todos os clientes da Azure o limite de certificados por domínio. O `duckdns.org` está na lista, e cada nome tem o próprio limite. Publicar já é seguro porque o modo stdio não mudou.
- **Alternativas:** AWS (o crédito de estudante pode ser do Learner Lab, que desliga a máquina no fim da sessão); comprar um domínio (cerca de US$ 10 por ano, fora dos créditos); máquina da universidade; a máquina do Erick com portas abertas; publicar uma 1.1.0rc1 antes.
- **Decidido por:** Erick · **Data:** 2026-11-11
- **Fontes:** conversa de 2026-11-11 (Claude Code); azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p e publicsuffix.org/list, lidos em 2026-11-11; fórum community.letsencrypt.org ("Policy forbids issuing for name on Amazon EC2 domain")
- **Situação:** decidida
