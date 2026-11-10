# Modo HTTP

**Fase:** 8 · Uso por link (v2) · **Situação:** para testar

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

- [X] Teste: `rslapp` sem argumento continua servindo por stdio (o teste de handshake por stdio que já existe passa sem mudança)
- [X] Teste: com o servidor HTTP de pé numa porta livre (uvicorn numa thread ou num subprocesso), um cliente do SDK conectado por HTTP em `/mcp` lista as oito ferramentas e o prompt, e `list_sources` responde igual ao stdio
- [X] Teste: uma chamada com o cabeçalho `Host` de um domínio que não é o de `RSL_PUBLIC_URL` recebe 421; com `Host` igual ao domínio de `RSL_PUBLIC_URL`, passa
- [X] Teste: `GET /health` devolve 200 com `status` e `version`, e nada mais
- [X] Teste: `rslapp serve --host 0.0.0.0` sai com erro e mensagem clara, sem abrir a porta
- [X] Teste: `rslapp --help` e `rslapp serve --help` mostram os comandos em português, sem iniciar servidor nenhum
- [X] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-011 (modo HTTP no próprio pacote), D-006 (SDK oficial 2.x), D-017 (HTTPS pelo proxy). São os ids que o código leva como âncoras.

## Antes de começar

Ler por inteiro as páginas oficiais do SDK v2 "Running your server" (py.sdk.modelcontextprotocol.io/run/), "Deploy & scale" (/run/deploy/), "Add to an existing app" (/run/asgi/) e "Transports" (/client/transports/, para o cliente HTTP dos testes). No SDK instalado, conferir em `mcp/server/mcpserver/server.py` os métodos `run`, `streamable_http_app` e `custom_route`. O `uvicorn` já vem como dependência do `mcp`. O import continua `from mcp.server import MCPServer`, não o `FastMCP` da versão 1.

Ler `src/rslapp/server.py`, `src/rslapp/config.py` e o `pyproject.toml`.

Cerca de 300 linhas. Um commit por item do "O que faz" que for grande (comandos; modo HTTP com proteção de host; `/health`), cada um com D-011 no comentário e no nome do teste.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/config.py`: adicionada a dataclass imutável `HttpConfig` e as funções `load_http(host, port)`, `is_loopback_host(host)` e `parse_public_url_host(public_url)` para ler `RSL_HTTP_HOST` (padrão `127.0.0.1`), `RSL_HTTP_PORT` (padrão `8000`), `RSL_PUBLIC_URL` (padrão `http://127.0.0.1:<porta>`) e `RSL_FORWARDED_ALLOW_IPS` (padrão `127.0.0.1`), aplicando a sobreposição de `--host` e `--port` e mantendo segredos fora do `repr` e de mensagens de erro (**D-011**, **D-017**, **NFR-03**).
  - `src/rslapp/cli.py`: criado o módulo de linha de comando com `argparse` em português; `rslapp` sem argumentos inicia direto `rslapp.server:main` por stdio sem escrever nada em `stdout`, e `rslapp serve [--host HOST] [--port PORTA]` valida o host de loopback (recusando hosts externos com mensagem clara no `stderr` e saída `!= 0`) e inicia o servidor HTTP (**D-008**, **D-011**).
  - `src/rslapp/server.py`: adicionada a rota `@mcp.custom_route("/health", methods=["GET"])` devolvendo `{"status": "ok", "version": __version__}`, e as funções `build_transport_security`, `create_http_app`, `build_uvicorn_config` (com `proxy_headers=True` e `forwarded_allow_ips`) e `run_http` servindo as mesmas oito ferramentas e o prompt `plan_search` em `/mcp` num processo único (**D-011**, **D-006**, **D-017**).
  - `pyproject.toml` e `tests/test_config.py`: atualizado `[project.scripts]` de `rslapp = "rslapp.server:main"` para `rslapp = "rslapp.cli:main"` (mantendo `rslapp.server:main` funcional) e ajustado o valor esperado do entry point no teste `test_d001_d008_pacote_e_entrypoint_instalados`.
  - `tests/test_cli.py` e `tests/test_server_http.py`: 16 novos testes cobrindo a CLI (`--help`, `serve --help`, `serve --host 0.0.0.0`, sobreposição de variáveis), `HttpConfig`, handshake HTTP real em porta livre com listagem das oito ferramentas, do prompt `plan_search` e chamada de `list_sources`, proteção contra DNS rebinding (`421` para host estranho e `200` para o host de `RSL_PUBLIC_URL`), cabeçalhos de proxy no `uvicorn.Config` e rota `GET /health`.
- **Ids servidos:** D-011, D-006, D-017 (além de D-002, D-008 e NFR-03 preservados).
- **O que foi assumido:**
  - A configuração do modo HTTP foi estruturada em `HttpConfig` e `load_http()` dentro de `rslapp.config`, preservando intactos os campos de `Config` retornados por `config.load()` nas ferramentas e permitindo que `--port` atualize também a porta padrão de `RSL_PUBLIC_URL` (`http://127.0.0.1:<porta>`) quando `RSL_PUBLIC_URL` não está definida no ambiente.
  - Em `TransportSecuritySettings`, além de `allowed_hosts` com os endereços de loopback (`127.0.0.1`, `localhost`, `[::1]`, puros e com `:*`) e o host de `RSL_PUBLIC_URL` (puro e com `:*`), `allowed_origins` também inclui loopback e a origem de `RSL_PUBLIC_URL` (pura e com `:*`) para não bloquear clientes que enviem cabeçalho `Origin` legítimo.
- **O que não deu para verificar:** nada; todos os itens de "Pronto quando" foram verificados com testes automatizados locais em `127.0.0.1`.

## Como testar

1. **Rode os três gates na raiz do repositório:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
   - **O que deve aparecer:** `All checks passed!` no `ruff check .` e `487 passed` nas duas execuções do `pytest` (Python 3.10 e Python 3.14).

2. **Como subir o servidor HTTP à mão e conectar um cliente:**
   - Num terminal, suba o servidor HTTP local numa porta livre (por exemplo, `8765`):
     ```powershell
     uv run rslapp serve --host 127.0.0.1 --port 8765
     ```
   - Noutro terminal, consulte `/health` e conecte um cliente MCP do SDK em `/mcp`:
     ```powershell
     uv run python -c "import httpx; print(httpx.get('http://127.0.0.1:8765/health').json())"
     uv run python -c "import asyncio; from mcp import Client; exec('async def main():\n async with Client(\"http://127.0.0.1:8765/mcp\") as c:\n  print([t.name for t in (await c.list_tools()).tools])\n  print([p.name for p in (await c.list_prompts()).prompts])\n  print((await c.call_tool(\"list_sources\", {})).structured_content)\nasyncio.run(main())')"
     ```
   - **O que deve aparecer:**
     - Em `GET /health`: `{'status': 'ok', 'version': '1.0.1'}`.
     - Na conexão ao `/mcp`: as oito ferramentas (`search_works`, `find_work`, `get_related_works`, `repeat_search`, `get_list`, `get_search_log`, `export_list`, `list_sources`), o prompt `plan_search` e o retorno de `list_sources` idêntico ao modo stdio.
     - Ao rodar `uv run rslapp serve --host 0.0.0.0`: mensagem de erro no `stderr` informando que o modo HTTP sem login só escuta em loopback e código de saída `1`.

3. **Onde olhar primeiro (pontos mais arriscados, do mais difícil para o mais simples):**
   1. **Proteção contra DNS rebinding e extração do host de `RSL_PUBLIC_URL` (`src/rslapp/server.py` — `build_transport_security` e `src/rslapp/config.py` — `parse_public_url_host`):** conferir que `TransportSecuritySettings` inclui exclusivamente os hosts de loopback (`127.0.0.1`, `localhost`, `[::1]`) e o host extraído de `RSL_PUBLIC_URL` (nas formas pura e `:*`), recusando qualquer outro cabeçalho `Host` com HTTP `421`.
   2. **Bloqueio de escuta fora de loopback sem login e preservação de segredos (`src/rslapp/cli.py`, `src/rslapp/server.py` — `run_http` e `src/rslapp/config.py` — `load_http`):** garantir que tanto a CLI quanto `server.run_http` recusam hosts diferentes de `127.0.0.1`, `localhost` e `::1` antes de abrir socket no `uvicorn`, e que `HttpConfig` e erros de validação nunca expõem chaves de API no `repr` ou em exceções.
   3. **Pureza do canal `stdout` no modo stdio padrão (`src/rslapp/cli.py` — `main`):** confirmar que `rslapp` chamado sem argumentos desvia imediatamente para `server.main()` sem acionar impressão do `argparse` nem tocar no `stdout`.

**Revisão do Claude (2026-11-10):** aprovada. A rodada do Gemini foi interrompida pelo Claude Code por falta de memória na máquina, depois dos três commits e durante a conferência final; os gates foram refeitos na revisão: ruff limpo, 487 testes em 3.10 e em 3.14. A entrega passou de 400 linhas (851, das quais cerca de 550 de testes), dividida em três commits. Acompanhamentos, não bloqueiam: a recusa de host fora do loopback está repetida em `cli.py` e em `server.run_http` (a 08-03 troca essa regra nos dois lugares); `allowed_origins` aceita só `http://` no loopback, o que basta porque os clientes MCP não mandam `Origin`.
