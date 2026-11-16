# Guia das instituições, com o ChatGPT pelo servidor da instituição

**Fase:** 12 · Conectar a IA ao app (2.1) · **Situação:** a fazer

## O que faz

Reorganiza o `docs/hospedagem.md` para o público principal do projeto, as instituições de ensino (D-029, FR-20), e acrescenta o uso pelo ChatGPT.

**Quem faz:** é documento e teste. O Claude escreve e testa no servidor de teste (`rsl.sinteselabs.com`). O Gemini só entra se o teste do ChatGPT mostrar uma mudança de código necessária, que vira item desta spec.

### 1. Abertura para instituições

No topo do guia, antes da seção 1, uma parte "Para instituições de ensino" com:

- **O que a instituição oferece:** cada pesquisador liga a própria IA (Claude, ChatGPT e outras que aceitam MCP remoto) ao servidor da instituição, com um código pessoal. Cada pessoa tem as suas listas e o seu log, separados.
- **Por que interessa:**
  - a busca fica registrada (a string, a data e o número de resultados por base) e pode ser anexada à metodologia;
  - as listas saem prontas para o VOSviewer e outras ferramentas;
  - tudo sem custo de licença.
- **O que a instituição precisa:**
  - um servidor com Docker e um domínio com HTTPS (seção 1);
  - uma pessoa de TI para cadastrar os pesquisadores (seção 3);
  - as chaves gratuitas das bases.
- **O que fica com a instituição:** os dados de autores e o cadastro das pessoas ficam no servidor dela, e ela responde por eles. Aviso da LGPD (T-007) em destaque.
- **As duas formas de oferecer:** o servidor hospedado (este guia) e o app desktop distribuído aos pesquisadores (seção que a 12-02 acrescenta).

### 2. ChatGPT

Na seção 4, "Como cada pessoa conecta a IA" (hoje "o Claude"), uma parte "No ChatGPT":

- os passos para adicionar um servidor MCP personalizado no ChatGPT da web, com a URL `https://<domínio>/mcp` e o login OAuth com o código pessoal;
- em quais planos funciona, segundo a página oficial da OpenAI lida no dia;
- o que fazer se o ChatGPT recusar o login.

### 3. Teste real no servidor de teste

O Claude confere antes de escrever:

- Ler por inteiro as páginas oficiais da OpenAI:
  - https://developers.openai.com/api/docs/guides/custom-mcp-server.md
  - https://developers.openai.com/apps-sdk/build/auth
  - e a página de ajuda sobre servidores MCP personalizados (se a ajuda bloquear a leitura automática, registrar).
- Conferir os dados de login do servidor de teste contra o que a OpenAI pede:
  - `S256` em `code_challenge_methods_supported`;
  - `registration_endpoint` ou CIMD;
  - os metadados do recurso protegido;
  - o `resource`;
  - os métodos de autenticação do cliente no `token_endpoint`, porque hoje só há `client_secret_post` e `client_secret_basic`, sem `none`.
- **O Erick conecta o ChatGPT** ao `https://rsl.sinteselabs.com/mcp` com um código pessoal de teste e faz uma busca.
  - Se falhar, o Claude lê o log do servidor, acha a causa e escreve a correção como item desta spec, para o `agy`.

## O que não faz

- Não cria servidor do projeto (D-027).
- Não muda o modo hospedado, a menos que o teste do ChatGPT mostre que é preciso.

## Para instituições

Esta tarefa é o guia das instituições.

## Pronto quando

- [x] O guia abre com "Para instituições de ensino"
- [x] A seção 4 cobre o Claude e o ChatGPT
- [ ] O ChatGPT do Erick fez uma busca no servidor de teste, ou a falha virou item com a causa
- [x] O README aponta para o guia, com uma linha para instituições

## Vem de

FR-20, D-011, D-012, D-016, D-018, D-027, D-029.

## Antes de começar

- Leia o `docs/hospedagem.md` inteiro e a D-011, a D-012 e a D-016.
- O servidor de teste fica ligado.
- O código pessoal de teste é criado pelo Claude no servidor (`rslapp token add`) e entregue ao Erick na conversa, nunca em arquivo.

## Resultado da entrega

Entregue pelo Claude em 2026-11-15, menos o teste do ChatGPT, que espera o Erick.

- **Guia (`docs/hospedagem.md`):** a parte "Para instituições de ensino" abre o guia (o que a instituição oferece, por que interessa, do que precisa, o que fica com ela, as duas formas de oferecer), seguida do aviso da LGPD. A seção 4 virou "Como cada pessoa conecta a IA", com a parte "No ChatGPT": passos, planos, confirmações e o que fazer se o login falhar.
- **README:** uma linha para instituições, apontando para o guia.
- **Páginas lidas em 2026-11-15:**
  - `developers.openai.com/api/docs/guides/custom-mcp-server.md`: o cadastro é em chatgpt.com/plugins → **+** → "Add custom MCP server"; transporte SSE ou HTTP com streaming; OAuth por CIMD ou DCR; a página não lista os planos.
  - `developers.openai.com/apps-sdk/build/auth`: PKCE `S256`; DCR pelo `registration_endpoint` ou CIMD; metadados do recurso protegido com `resource` e `authorization_servers`; o ChatGPT manda `resource`; sem o `iss` da RFC 9207, o retorno vai para `https://chatgpt.com/connector/oauth/{callback_id}`.
  - A ajuda da OpenAI (help.openai.com) devolveu 403 à leitura automática. Os planos no guia vêm de fontes de terceiros, e o guia diz isso.
- **Conferência do servidor de teste contra a OpenAI:**
  - `S256` em `code_challenge_methods_supported`: sim.
  - `registration_endpoint` (DCR): sim. CIMD: não, e não é preciso.
  - Metadados do recurso protegido e `resource` (`https://rsl.sinteselabs.com/mcp`): sim.
  - Métodos no `token_endpoint`: os metadados anunciam só `client_secret_post` e `client_secret_basic`. Mesmo assim, um cadastro igual ao do ChatGPT (`token_endpoint_auth_method: none`, retorno em `chatgpt.com/connector/oauth/...`) foi aceito com 201. **Risco:** a OpenAI diz que, no CIMD, o ChatGPT escolhe o método no cruzamento das duas listas; se fizer o mesmo no DCR, o cruzamento com `none` e `private_key_jwt` fica vazio. O teste do Erick responde. Se falhar aí, o item para o `agy` é anunciar `none` em `token_endpoint_auth_methods_supported`.
- **Achado para depois:** nenhuma ferramenta declara `readOnlyHint`, então o ChatGPT pede confirmação a cada chamada. Marcar como só de leitura as ferramentas que não gravam nada (`list_sources`, `get_list`, `get_search_log`, `get_related_works`, `find_work`) é uma tarefa pequena, que fica proposta para depois do teste.
- **Cliente de teste:** a simulação deixou um cliente OAuth `teste-claude` registrado no servidor de teste, sem acesso a nada (não tem código pessoal).

## Como testar

**Onde olhar primeiro:** a parte "No ChatGPT", porque é a única escrita sem teste real; depois o aviso da LGPD, que agora vem depois da parte das instituições e precisa continuar visível.

1. O Erick, no ChatGPT da web: chatgpt.com/plugins → **+** → "Add custom MCP server", URL `https://rsl.sinteselabs.com/mcp`, OAuth sem credenciais, login com o código de teste `chatgpt-teste`.
2. Pedir uma busca. Ela deve voltar com resultados e aparecer no log de buscas.
3. Se falhar, mandar ao Claude a mensagem do ChatGPT e a hora. O Claude lê `docker compose logs rslapp` e escreve o item com a causa.
4. Depois do teste, o Claude revoga o código: `docker compose exec rslapp rslapp token revoke chatgpt-teste`.
