# Modo HTTP

**Fase:** 8 · Uso por link (v2) · **Situação:** a fazer

## O que faz

Cria o comando `rslapp serve`, que serve as mesmas oito ferramentas e o mesmo prompt por HTTP (transporte "streamable HTTP" do SDK), além do stdio de hoje. É a base de todo o uso por link (D-011).

- **Comandos:** `rslapp` sem argumento continua iniciando o servidor por stdio, igual à 1.0.1: nenhum cliente configurado hoje pode quebrar. `rslapp serve` inicia o modo HTTP. Os subcomandos ficam num módulo novo `src/rslapp/cli.py` (com `argparse`), e o `[project.scripts]` passa a apontar para `rslapp.cli:main`. `rslapp.server:main` continua existindo e iniciando o stdio.
- **Uma definição só das ferramentas:** o stdio e o HTTP usam as mesmas funções de ferramenta e o mesmo prompt. Nada de copiar as ferramentas para um segundo servidor.
- **Configuração** (lida em `rslapp.config`, sem expor valores secretos no `repr`):

| Variável | Padrão | Para quê |
|---|---|---|
| `RSL_HTTP_HOST` | `127.0.0.1` | Endereço em que o servidor escuta |
| `RSL_HTTP_PORT` | `8000` | Porta |
| `RSL_PUBLIC_URL` | `http://127.0.0.1:<porta>` | Endereço pelo qual os clientes chegam (no Docker, o domínio com HTTPS). Daqui sai a lista de hosts aceitos |
| `RSL_FORWARDED_ALLOW_IPS` | `127.0.0.1` | De quem o servidor aceita os cabeçalhos `X-Forwarded-*` (o proxy com HTTPS) |

  `rslapp serve --host` e `--port` sobrepõem as variáveis.
- **Proteção de host (DNS rebinding):** o servidor aceita só o host de `RSL_PUBLIC_URL` (na forma pura e com `:*`) e os de loopback, pelo `transport_security=TransportSecuritySettings(...)` do SDK. Um host diferente recebe 421, como o SDK já faz.
- **Atrás do proxy:** o uvicorn roda com os cabeçalhos do proxy ligados (`proxy_headers` e `forwarded_allow_ips`), para que redirecionamentos não virem `http://` atrás do Caddy (página "Deploy & scale" do SDK).
- **Rota `/health`:** `GET /health` devolve `{"status": "ok", "version": "<versão>"}`, sem nenhum outro dado. Serve ao healthcheck do Docker (08-06).
- **Sem login ainda:** nesta tarefa, `rslapp serve` recusa iniciar se o host de escuta não for de loopback (`127.0.0.1`, `localhost` ou `::1`), com uma mensagem clara no stderr e código de saída diferente de zero. A 08-03 libera outros hosts, exigindo o login.

## O que não faz

- Não tem login, nem separação por pessoa, nem link de download (08-03, 08-04 e 08-05). Nesta tarefa, o modo HTTP usa a mesma pasta de dados do stdio.
- Não muda nenhuma ferramenta, nenhuma entrada nem nenhum campo de resposta.
- Não usa vários processos (workers): um processo só, como no `mcp.run(transport="streamable-http")`.
- Não faz HTTPS: isso é do Caddy (D-017).

## Pronto quando

- [ ] Teste: `rslapp` sem argumento continua servindo por stdio (o teste de handshake por stdio que já existe passa sem mudança)
- [ ] Teste: com o servidor HTTP de pé numa porta livre (uvicorn numa thread ou num subprocesso), um cliente do SDK conectado por HTTP em `/mcp` lista as oito ferramentas e o prompt, e `list_sources` responde igual ao stdio
- [ ] Teste: uma chamada com o cabeçalho `Host` de um domínio que não é o de `RSL_PUBLIC_URL` recebe 421; com `Host` igual ao domínio de `RSL_PUBLIC_URL`, passa
- [ ] Teste: `GET /health` devolve 200 com `status` e `version`, e nada mais
- [ ] Teste: `rslapp serve --host 0.0.0.0` sai com erro e mensagem clara, sem abrir a porta
- [ ] Teste: `rslapp --help` e `rslapp serve --help` mostram os comandos em português, sem iniciar servidor nenhum
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-011 (modo HTTP no próprio pacote), D-006 (SDK oficial 2.x), D-017 (HTTPS pelo proxy). São os ids que o código leva como âncoras.

## Antes de começar

Ler por inteiro as páginas oficiais do SDK v2 "Running your server" (py.sdk.modelcontextprotocol.io/run/), "Deploy & scale" (/run/deploy/), "Add to an existing app" (/run/asgi/) e "Transports" (/client/transports/, para o cliente HTTP dos testes). No SDK instalado, conferir em `mcp/server/mcpserver/server.py` os métodos `run`, `streamable_http_app` e `custom_route`. O `uvicorn` já vem como dependência do `mcp`. O import continua `from mcp.server import MCPServer`, não o `FastMCP` da versão 1.

Ler `src/rslapp/server.py`, `src/rslapp/config.py` e o `pyproject.toml`.

Cerca de 300 linhas. Um commit por item do "O que faz" que for grande (comandos; modo HTTP com proteção de host; `/health`), cada um com D-011 no comentário e no nome do teste.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega: os comandos dos três gates, como subir o servidor HTTP à mão e conectar um cliente, o que deve aparecer e os pontos mais arriscados, o mais difícil primeiro)
