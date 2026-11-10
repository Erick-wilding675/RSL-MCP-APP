# Login OAuth

**Fase:** 8 · Uso por link (v2) · **Situação:** a fazer

## O que faz

Coloca login no modo HTTP: o `rslapp serve` passa a ser, no mesmo processo, um servidor de autorização OAuth 2.1 e o servidor MCP protegido por ele (D-015). A pessoa adiciona o link como conector no Claude, o Claude a manda para a tela de login do RSL.app, ela digita o código pessoal (08-02) e volta conectada. A sessão não tem prazo: vale até a pessoa ser revogada (D-016).

- **Separação recomendada pelo SDK:** a página "Authorization" do SDK v2 chama de legado o `auth_server_provider=` do `MCPServer` e diz que servidores novos não devem usá-lo. Por isso:
  - o **servidor MCP** recebe `token_verifier=` e `auth=AuthSettings(issuer_url=<RSL_PUBLIC_URL>, resource_server_url=<RSL_PUBLIC_URL>/mcp, required_scopes=["rsl"], validate_token_resource=True)`;
  - o **servidor de autorização** são as rotas de `create_auth_routes(...)` do SDK (`mcp.server.auth.routes`), com um provedor do RSL.app, mais as rotas da tela de login, montadas no mesmo app ASGI do servidor MCP, como no exemplo oficial `examples/servers/simple-auth` (tag `v2.3.0`), só que num processo só.
- **Registro de clientes:** registro automático (Dynamic Client Registration) ligado, com o escopo `rsl` válido e padrão. Revogação (`/revoke`) ligada.
- **Autorização:** o `authorize` do provedor guarda o pedido em memória por até 10 minutos e redireciona para `<RSL_PUBLIC_URL>/login?req=<id aleatório>`.
- **Tela de login** (`GET /login` e `POST /login`): página HTML simples em português, sem nenhum arquivo de fora (sem CDN, sem fonte externa), com o nome do conector que está pedindo acesso e um campo para o código. Com um código certo de pessoa ativa, gera o código de autorização (válido por 5 minutos, uso único) e redireciona para o `redirect_uri` do cliente com `code` e `state`. Com um código errado, mostra de novo a página com uma mensagem genérica ("código inválido"), sem dizer se a pessoa existe.
- **Limite de tentativas:** no máximo 5 códigos errados por pedido e 20 por IP a cada 15 minutos (em memória). Depois disso, 429 com mensagem em português. O IP fica só na memória.
- **Tokens:** o token de acesso vale 60 minutos (`RSL_ACCESS_TOKEN_MINUTES`, padrão 60). O token de renovação não tem prazo e é trocado a cada uso: o antigo deixa de valer. Os dois são aleatórios (`secrets`), e em disco fica só o SHA-256 deles, com a pessoa, o cliente, os escopos, o `resource`, a data de emissão e a validade. Arquivos em `<RSL_DATA_DIR>/auth/` (clientes registrados e tokens), com a gravação segura que já existe. Pedidos e códigos de autorização ficam só na memória.
- **Verificação a cada chamada:** um token só vale se o hash existe, não venceu, o `resource` é o `/mcp` deste servidor, a pessoa está ativa e o token foi emitido depois do `code_created_at` dela. Assim `token revoke` e `token add --replace` (08-02) cortam o acesso na hora, sem reiniciar o servidor.
- **Quem é a pessoa:** a ferramenta descobre a pessoa do token da chamada (por `get_access_token()` do SDK ou pelo que o verificador devolve). Esta tarefa deixa uma função `current_person_id() -> str | None` pronta para a 08-04. No stdio, ela devolve `None`.
- **Host de escuta:** com o login, `rslapp serve` passa a aceitar host fora do loopback (por exemplo, `0.0.0.0` no Docker), desde que `RSL_PUBLIC_URL` comece com `https://`. Com `RSL_PUBLIC_URL` em `http://`, só loopback, como na 08-01. No loopback, o login também vale: não existe modo HTTP sem login.

## O que não faz

- Não usa `auth_server_provider=` no `MCPServer` (legado, pela documentação do SDK).
- Não faz login pelo Google nem pela universidade (D-015). Não guarda e-mail.
- Não aceita token na URL nem em cabeçalho fixo fora do OAuth.
- Não suporta "Client ID Metadata Document", a opção "Use Claude's published identity" do Claude, a menos que o SDK 2.3.0 já faça isso sozinho. O guia (08-06) manda escolher "Register automatically" no Claude. Se o SDK suportar, registrar no "Resultado da entrega".
- Não separa os dados por pessoa (08-04).
- Nunca escreve código, token ou hash em log, em mensagem de erro, na página de login ou no `repr`.

## Pronto quando

- [ ] Teste, com o app ASGI e o `httpx.ASGITransport` (sem rede): o fluxo inteiro passa, com `GET /.well-known/oauth-protected-resource/mcp`, os metadados do servidor de autorização, `POST /register`, `GET /authorize` (redireciona para `/login`), `POST /login` com o código certo (redireciona com `code` e `state`), `POST /token` com PKCE, e uma chamada a `/mcp` com o token de acesso que lista as ferramentas
- [ ] Teste: `/mcp` sem token recebe 401 com `WWW-Authenticate` apontando os metadados; com token inventado, 401
- [ ] Teste: depois de `token revoke` da pessoa, o token de acesso e o de renovação dela deixam de valer na hora; depois de `token add --replace`, os tokens emitidos antes também
- [ ] Teste: a renovação devolve um par novo, e o token de renovação antigo é recusado
- [ ] Teste: o token de acesso vencido (relógio adiantado no teste) é recusado, e a renovação continua funcionando
- [ ] Teste: o código de autorização vale uma vez só e vence em 5 minutos
- [ ] Teste: 5 códigos errados no mesmo pedido levam a 429; a página com código errado não diz se a pessoa existe
- [ ] Teste: nenhum arquivo de `auth/` contém um token ou código em texto; só hashes
- [ ] Teste: `rslapp serve --host 0.0.0.0` com `RSL_PUBLIC_URL=https://exemplo.org` inicia; com `http://`, recusa
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-015 (OAuth com código pessoal), D-016 (sessão sem prazo, revogação na hora), D-012 (código por pessoa), D-007 (só arquivos). São os ids que o código leva como âncoras.

## Antes de começar

Ler por inteiro: a página "Authorization" do SDK v2 (py.sdk.modelcontextprotocol.io/run/authorization/), a página "OAuth" de clientes (/client/oauth-clients/, para os testes) e o exemplo `examples/servers/simple-auth` do repositório `modelcontextprotocol/python-sdk` na tag `v2.3.0` (`auth_server.py`, `simple_auth_provider.py`, `token_verifier.py`, `server.py`). No SDK instalado, ler `mcp/server/auth/provider.py` (o protocolo `OAuthAuthorizationServerProvider` e o `TokenVerifier`), `mcp/server/auth/routes.py` e `mcp/server/auth/settings.py`. Ler também a página do Claude sobre conectores por URL (claude.com/docs/connectors/custom/remote-mcp), para saber o que o cliente espera.

É a maior tarefa da fase: deve passar de 400 linhas. Dividir em três commits revisáveis: (1) armazenamento de clientes e tokens e o verificador; (2) provedor, rotas de autorização e tela de login; (3) ligação no `rslapp serve` e regra do host. Cada um com D-015 ou D-016 no comentário e no nome dos testes. Dizer no relatório como dividiu.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega: os comandos dos três gates, como fazer o login à mão no navegador com o servidor local, o que deve aparecer e os pontos mais arriscados, o mais difícil primeiro)
