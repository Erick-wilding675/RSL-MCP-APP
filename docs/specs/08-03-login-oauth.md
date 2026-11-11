# Login OAuth

**Fase:** 8 · Uso por link (v2) · **Situação:** pronta (testada pelo Erick em 2026-11-11, no teste real da 08-07)

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

## Decisões tomadas na revisão

- **Segredo do cliente OAuth em texto no `clients.json`** (Claude, 2026-11-10, barata de desfazer): a primeira rodada guardava só o hash do `client_secret` e o segredo numa variável em memória, e a sessão caía a cada reinício, o que quebrava a D-016. Ficou como no exemplo oficial `simple-auth` do SDK: o segredo em `<RSL_DATA_DIR>/auth/clients.json`. Sozinho ele não dá acesso: os tokens de acesso e de renovação continuam só como hash, e o código de autorização exige PKCE.

## O que não faz

- Não usa `auth_server_provider=` no `MCPServer` (legado, pela documentação do SDK).
- Não faz login pelo Google nem pela universidade (D-015). Não guarda e-mail.
- Não aceita token na URL nem em cabeçalho fixo fora do OAuth.
- Não suporta "Client ID Metadata Document", a opção "Use Claude's published identity" do Claude, a menos que o SDK 2.3.0 já faça isso sozinho. O guia (08-06) manda escolher "Register automatically" no Claude. Se o SDK suportar, registrar no "Resultado da entrega".
- Não separa os dados por pessoa (08-04).
- Nunca escreve código, token ou hash em log, em mensagem de erro, na página de login ou no `repr`.

## Pronto quando

- [X] Teste, com o app ASGI e o `httpx.ASGITransport` (sem rede): o fluxo inteiro passa, com `GET /.well-known/oauth-protected-resource/mcp`, os metadados do servidor de autorização, `POST /register`, `GET /authorize` (redireciona para `/login`), `POST /login` com o código certo (redireciona com `code` e `state`), `POST /token` com PKCE, e uma chamada a `/mcp` com o token de acesso que lista as ferramentas
- [X] Teste: `/mcp` sem token recebe 401 com `WWW-Authenticate` apontando os metadados; com token inventado, 401
- [X] Teste: depois de `token revoke` da pessoa, o token de acesso e o de renovação dela deixam de valer na hora; depois de `token add --replace`, os tokens emitidos antes também
- [X] Teste: a renovação devolve um par novo, e o token de renovação antigo é recusado
- [X] Teste: o token de acesso vencido (relógio adiantado no teste) é recusado, e a renovação continua funcionando
- [X] Teste: o código de autorização vale uma vez só e vence em 5 minutos
- [X] Teste: 5 códigos errados no mesmo pedido levam a 429; a página com código errado não diz se a pessoa existe
- [X] Teste: nenhum arquivo de `auth/` contém um token ou código em texto; só hashes
- [X] Teste: `rslapp serve --host 0.0.0.0` com `RSL_PUBLIC_URL=https://exemplo.org` inicia; com `http://`, recusa
- [X] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-015 (OAuth com código pessoal), D-016 (sessão sem prazo, revogação na hora), D-012 (código por pessoa), D-007 (só arquivos). São os ids que o código leva como âncoras.

## Antes de começar

Ler por inteiro: a página "Authorization" do SDK v2 (py.sdk.modelcontextprotocol.io/run/authorization/), a página "OAuth" de clientes (/client/oauth-clients/, para os testes) e o exemplo `examples/servers/simple-auth` do repositório `modelcontextprotocol/python-sdk` na tag `v2.3.0` (`auth_server.py`, `simple_auth_provider.py`, `token_verifier.py`, `server.py`). No SDK instalado, ler `mcp/server/auth/provider.py` (o protocolo `OAuthAuthorizationServerProvider` e o `TokenVerifier`), `mcp/server/auth/routes.py` e `mcp/server/auth/settings.py`. Ler também a página do Claude sobre conectores por URL (claude.com/docs/connectors/custom/remote-mcp), para saber o que o cliente espera.

É a maior tarefa da fase: deve passar de 400 linhas. Dividir em três commits revisáveis: (1) armazenamento de clientes e tokens e o verificador; (2) provedor, rotas de autorização e tela de login; (3) ligação no `rslapp serve` e regra do host. Cada um com D-015 ou D-016 no comentário e no nome dos testes. Dizer no relatório como dividiu.

## Resultado da entrega

O modo HTTP (`rslapp serve`) passou a operar simultaneamente como Authorization Server OAuth 2.1 e Resource Server MCP protegido no mesmo processo ASGI, seguindo a separação recomendada pela documentação de "Authorization" do SDK `mcp` 2.3.0 (sem usar `auth_server_provider=` no `MCPServer`):

1. **Armazenamento de clientes e tokens e verificador (`src/rslapp/auth/store.py`, `src/rslapp/auth/verifier.py`, `src/rslapp/config.py`, `tests/auth/test_store_and_verifier.py`):**
   - `AuthStore` grava clientes registrados e tokens em `<RSL_DATA_DIR>/auth/clients.json` e `<RSL_DATA_DIR>/auth/tokens.json` usando `atomic_write_replace` e `file_lock`.
   - `clients.json` persiste os metadados do cliente OAuth (incluindo `client_secret`, como no exemplo `simple-auth` do SDK) para que clientes registrados com `client_secret_post` renovem tokens mesmo após reinício do servidor. Em `tokens.json` ficam exclusivamente hashes SHA-256 (`token_hash`) dos tokens de acesso e de renovação, nunca tokens ou códigos pessoais em texto puro. Ao gravar `tokens.json`, tokens de acesso vencidos e tokens de pessoas inexistentes, revogadas ou com código trocado são removidos automaticamente.
   - `RSLTokenVerifier` verifica a cada requisição `/mcp` se o hash existe, se não venceu (`RSL_ACCESS_TOKEN_MINUTES`, padrão 60), se o campo `resource` bate com `<RSL_PUBLIC_URL>/mcp`, se a pessoa continua ativa em `people.json` e se `issued_at > person.code_created_at`, garantindo corte imediato em `rslapp token revoke` e `rslapp token add --replace`.
   - `current_person_id()` lê `get_access_token()` do contexto de autenticação do SDK e devolve o `person_id` autenticado no modo HTTP ou `None` no modo `stdio`.

2. **Provedor OAuth 2.1, rotas de autorização e tela de login (`src/rslapp/auth/provider.py`, `tests/auth/test_provider_and_login.py`):**
   - `RSLOAuthProvider` implementa `OAuthAuthorizationServerProvider` com pedidos pendentes em memória (validade de 10 minutos, teto de 1.000 pedidos pendentes), validação de `resource` em `/authorize` contra `<RSL_PUBLIC_URL>/mcp` (recusando divergências com `invalid_target`) e códigos de autorização de uso único (validade de 5 minutos).
   - `build_auth_routes` monta as rotas de `create_auth_routes(...)` do SDK (`/.well-known/oauth-authorization-server`, `/authorize`, `/token`, `/register` com escopo `rsl` válido e padrão, `/revoke`) junto com `GET /login` e `POST /login`.
   - A página `/login` é HTML autocontido em português do Brasil (sem CDN, fontes externas ou scripts), envia cabeçalhos `X-Frame-Options: DENY` e `Content-Security-Policy: frame-ancestors 'none'`, mostra o nome do conector e valida o código pessoal via `people.find_by_code` sem `await` entre a checagem de limite por IP e a contagem da falha (5 erros por pedido e 20 erros por IP a cada 15 minutos -> HTTP `429`), exibindo mensagem genérica (`"Código inválido..."`) sem revelar se a pessoa existe.
   - **Nota sobre Client ID Metadata Document:** o SDK `mcp` 2.3.0 suporta `client_metadata_url` apenas no lado cliente (`OAuthClientProvider`), deixando `client_id_metadata_document_supported=None` no servidor; o registro de conectores usa Dynamic Client Registration (`POST /register`), conforme previsto para a opção "Register automatically" no Claude.

3. **Ligação no `rslapp serve` e regra do host (`src/rslapp/server.py`, `src/rslapp/cli.py`, `src/rslapp/config.py`, `tests/auth/test_oauth_flow_http.py`, `tests/test_server_http.py`, `tests/test_cli.py`):**
   - `_build_http_mcp_server` instancia `MCPServer` pelo construtor com `token_verifier=` e `auth=AuthSettings(issuer_url=..., resource_server_url=.../mcp, required_scopes=["rsl"], validate_token_resource=True)` (sem alterar a instância global `mcp` do modo `stdio`), e `create_http_app` monta as rotas do Authorization Server e `/login` no mesmo app Starlette, mantendo proteção contra DNS rebinding (`421`) antes da exigência de token (`401`).
   - `config.validate_http_host` permite hosts fora do loopback (como `0.0.0.0`) quando `RSL_PUBLIC_URL` começa com `https://` e continua recusando quando `RSL_PUBLIC_URL` usa `http://`.

## Como testar

### 1. Executar os três gates (um após o outro, nunca em paralelo)

```powershell
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
```

### 2. Testar o login à mão no navegador com o servidor local e um cliente OAuth + PKCE

1. Cadastre uma pessoa e anote o código pessoal exibido:
   ```powershell
   uv run rslapp token add erick
   ```
2. Em um terminal, inicie o servidor HTTP local:
   ```powershell
   uv run rslapp serve
   ```
3. Em outro terminal, confira que `/mcp` sem token devolve `401` com `WWW-Authenticate` apontando para `/.well-known/oauth-protected-resource/mcp`:
   ```powershell
   curl -i http://127.0.0.1:8000/mcp
   ```
4. Para fazer o fluxo completo de login no navegador (que exige registro de cliente OAuth e PKCE `S256`), abra um cliente MCP compatível com OAuth 2.1 + PKCE, como o **MCP Inspector** (`npx @modelcontextprotocol/inspector`) apontando para `http://127.0.0.1:8000/mcp` (tipo **Streamable HTTP**):
   - O cliente lerá `/.well-known/oauth-protected-resource/mcp` e `/.well-known/oauth-authorization-server`, registrará o conector em `POST /register` e abrirá o navegador em `/authorize` com `code_challenge` PKCE.
   - O navegador será redirecionado para `http://127.0.0.1:8000/login?req=...`, exibindo o nome do conector e o campo **"Código pessoal"** em português.
   - Digite primeiro um código errado para ver a mensagem genérica `"Código inválido. Verifique seu código pessoal e tente novamente."` (e, se repetir 5 vezes no mesmo pedido, o bloqueio `429`). Em seguida, digite o código pessoal de `erick` gerado no passo 1: o servidor redirecionará de volta ao cliente com `code` e `state`, concluirá a troca em `POST /token` e listará as 8 ferramentas em `/mcp`.

### 3. Onde olhar primeiro na revisão (do ponto mais arriscado para o mais simples)

1. **Verificação por requisição, rotação, limpeza de tokens e persistência de clientes (`src/rslapp/auth/store.py` e `src/rslapp/auth/verifier.py`):**
   - `AuthStore.issue_token_pair` e `AuthStore.rotate_refresh_token` gravam em `<RSL_DATA_DIR>/auth/tokens.json` exclusivamente hashes SHA-256 (`hash_token`) dos tokens de acesso e renovação (nunca tokens ou códigos pessoais em texto puro), limpam tokens de acesso vencidos e tokens de pessoas revogadas/inexistentes a cada gravação (`_prune_invalid_tokens`), e mantêm `clients.json` com os metadados do cliente para que `client_secret_post` sobreviva a reinícios do servidor.
   - `AuthStore._is_token_record_valid_for_person` confere a cada chamada se `person.is_active` é verdadeiro e se `issued_at > person.code_created_at`, fazendo `token revoke` e `token add --replace` invalidarem imediatamente tanto o `access_token` quanto o `refresh_token`.
2. **Validação do código pessoal, `resource`, teto de pedidos e limites de tentativas em `/login` (`src/rslapp/auth/provider.py`):**
   - `RSLOAuthProvider.authorize` valida `params.resource` contra `<RSL_PUBLIC_URL>/mcp` (recusando com `invalid_target`) e aplica o teto `MAX_PENDING_AUTH_REQUESTS = 1000`.
   - `RSLOAuthProvider.handle_login_post` lê o formulário antes de checar o limite por IP (sem `await` entre checar e contar a falha), nunca distingue pessoa inexistente de pessoa revogada na resposta HTML, envia `X-Frame-Options: DENY` e `Content-Security-Policy: frame-ancestors 'none'` e consome o pedido pendente ao emitir um `RSLAuthorizationCode` de uso único válido por 5 minutos.
3. **Construção do `MCPServer` HTTP pelo construtor e regra de host (`src/rslapp/server.py`, `src/rslapp/config.py`, `src/rslapp/cli.py`):**
   - `_build_http_mcp_server` constrói o `MCPServer` passando `token_verifier=` e `auth=AuthSettings(validate_token_resource=True)` diretamente ao construtor (sem `auth_server_provider=` e sem tocar em atributos privados da instância global `mcp`), preserva a verificação de `Host`/`Origin` (`421`) antes de `RequireAuthMiddleware` (`401`) e `validate_http_host` exige `https://` em `RSL_PUBLIC_URL` para qualquer host fora de loopback.

**Revisão do Claude (2026-11-10, run `b20261110-163816` do Playmaker):** duas rodadas. A primeira foi devolvida pelo gerente com o parecer do agente revisor: segredo do cliente só em memória (sessão caía ao reiniciar), código de teste no caminho de produção (`_install_asgi_transport_fallback`, mexendo em partes internas do SDK), `tokens.json` sem limpeza, limite por IP com corrida entre pedidos simultâneos, `/authorize` aceitando outro `resource`, sem teto de pedidos pendentes e sem proteção contra a página ser embutida. A segunda corrigiu tudo, com um teste que reinicia o servidor e renova o token de um cliente com `client_secret_post`. Integrada com os gates refeitos pelo `board integrate`. Conferido e certo: escape do HTML, redirecionamento só para o `redirect_uri` validado com o `state` original, código de uso único em 5 minutos, PKCE e `resource` presos ao código, rotação do token de renovação, verificação a cada pedido (hash, validade, `resource`, pessoa ativa, emitido depois do `code_created_at`), nada de segredo em log ou `repr`, stdio sem mudança.

Acompanhamentos, não bloqueiam:
- O servidor HTTP registra as oito ferramentas numa lista em `_build_http_mcp_server`. Uma ferramenta nova precisa entrar nos dois lugares; o teste da 08-01 que compara as ferramentas do HTTP com as do stdio falha se alguém esquecer.
- Para o guia (08-06): se alguém publicar a porta 8000 do `rslapp` com `RSL_FORWARDED_ALLOW_IPS=*`, o IP do limite de tentativas pode ser falsificado; e atrás de um proxy sem essa variável, todos dividem o mesmo IP, e 20 códigos errados de qualquer pessoa bloqueiam o login de todos por 15 minutos.
- O registro de clientes é aberto (como o Claude espera): qualquer um pode registrar um cliente com o nome "Claude". A tela mostra o nome do conector, mas não o endereço para onde volta.

