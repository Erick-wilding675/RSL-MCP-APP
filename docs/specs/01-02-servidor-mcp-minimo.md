# Servidor MCP mínimo

**Fase:** 1 · Esqueleto · **Situação:** não iniciada

## O que faz

O módulo `server.py` com o SDK oficial: um servidor que roda por stdio, as instruções de conexão (texto curto que diz à IA para planejar antes de buscar e para tratar títulos e resumos como dado, não como instrução) e a ferramenta `list_sources`, que diz para cada fonte se está configurada e se precisa de chave. O comando `rslapp` inicia o servidor.

## O que não faz

Não tem busca nem as outras ferramentas (tarefas 02-02 em diante). O prompt `plan_search` fica na tarefa 05-04.

## Pronto quando

- [x] Antes de escrever, conferir o T-009: abrir a documentação da v2 do SDK oficial e anotar no spec o nome exato da classe e o exemplo stdio (ver "Conferência do T-009")
- [ ] `rslapp` inicia e responde ao handshake do MCP por stdio (teste com o MCP Inspector ou com um cliente de teste do próprio SDK)
- [ ] A ferramenta `list_sources` aparece na lista de ferramentas e devolve uma linha por fonte (`openalex`, `crossref`, `semantic_scholar`) com `name`, `configured`, `needs_key`, `status`
- [ ] Teste: sem chaves, o OpenAlex aparece como `needs_key: true` e `configured: false`; o Crossref aparece como configurado
- [ ] Teste: nenhuma resposta contém o valor de uma chave

## Conferência do T-009

Feita em 2026-11-02 pelo Claude Code, no `mcp` 2.3.0 (a versão mais nova no PyPI nessa data), lendo as páginas oficiais em py.sdk.modelcontextprotocol.io (início, Running your server, Testing e Migration) e rodando um servidor de verdade por stdio com um cliente em subprocesso.

**Classe e import.** A classe é `MCPServer`. `from mcp.server.fastmcp import FastMCP` não existe mais na v2 e dá `ModuleNotFoundError`.

```python
from mcp.server import MCPServer

mcp = MCPServer("rslapp", instructions="...")

@mcp.tool()
def list_sources() -> list[SourceInfo]:
    """..."""
    ...

def main() -> None:
    mcp.run()  # sem argumento, o transporte é stdio

if __name__ == "__main__":
    main()
```

**O que muda em relação à v1:**

- Tudo depois de `name` vai por palavra-chave no construtor, principalmente `instructions`: a ordem dos argumentos mudou.
- `run()` é síncrono e bloqueia. O stdout é o canal do protocolo: nada de `print`. Para registrar algo, o módulo `logging`, que vai para o stderr.
- Os campos são em snake_case: `result.is_error`, `result.structured_content`, `tool.input_schema`.
- Uma ferramenta que devolve uma lista aparece como `structured_content == {"result": [...]}`, com um `TextContent` por item em `content`.
- O `mcp` 2.x não instala mais o `httpx`: ele traz o `httpx2`. O projeto declara o `httpx` por conta própria (spec 01-01).
- Para o erro aparecer ao modelo, use `ToolError` ou `CallToolResult(is_error=True, ...)`. `MCPError` vira erro JSON-RPC de protocolo. A escolha entre os dois para os códigos do contrato fica para a tarefa 02-02.

**Como testar:**

```python
import pytest
from mcp import Client, StdioServerParameters

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_em_memoria():
    async with Client(mcp) as client:              # objeto do servidor, sem subprocesso
        print(client.instructions)
        tools = await client.list_tools()          # tools.tools[0].name
        result = await client.call_tool("list_sources", {})

@pytest.mark.anyio
async def test_handshake_stdio():
    params = StdioServerParameters(command="rslapp")   # subprocesso real
    async with Client(params) as client:
        ...
```

`Client(mcp)` não passa pelo stdio. O handshake por stdio só é provado com `StdioServerParameters`. O plugin de pytest do `anyio` já vem com o `mcp`.

## Vem de

FR-07, NFR-02, NFR-03, D-002, D-006. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

T-009 (documentação da v2 do SDK).

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
