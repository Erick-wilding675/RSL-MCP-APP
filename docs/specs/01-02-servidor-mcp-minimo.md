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

- **O que mudou:**
  - `src/rslapp/server.py`: servidor MCP mínimo com `MCPServer("rslapp", instructions=INSTRUCTIONS)` do SDK oficial `mcp>=2,<3` (**D-006**, **NFR-02**), constante `INSTRUCTIONS` em português orientando a IA a planejar e dividir assuntos em buscas separadas e a tratar títulos, resumos e metadados como dados (**D-002**, **NFR-03**), tipo `SourceInfo` (`typing_extensions.TypedDict` para compatibilidade com Pydantic no Python 3.10), ferramenta `list_sources()` que chama `config.load()` dinamicamente e devolve o estado das três fontes (`openalex`, `crossref`, `semantic_scholar`) sem expor chaves (**FR-07**, **NFR-03**, **D-002**), e função de entrada `main()` que executa `mcp.run()` via transporte stdio (**D-006**, **NFR-02**).
  - `tests/test_server.py`: 5 testes cobrindo handshake real por stdio em subprocesso com o comando instalado `rslapp` (`StdioServerParameters`), verificação de `client.instructions` e `list_tools`, chamada de `list_sources` com e sem chaves em subprocesso e em memória (`Client(mcp)`), releitura dinâmica do ambiente a cada chamada e ausência de escrita em `stdout` e de exposição de valores de chaves ou e-mail nas respostas e instruções (**FR-07**, **NFR-02**, **NFR-03**, **D-002**, **D-006**).
- **O que foi assumido:**
  - Valores do campo `status` em `list_sources`: assumiu-se `"ok"` quando a fonte está pronta para uso e `"missing_key"` quando `needs_key` é `True` e `configured` é `False` (estados previstos em `docs/interface-contract.md`, já que a spec não detalhava os literais de `status`).
  - Para `semantic_scholar`, `needs_key` é `False`, `configured` é `True` e `status` é `"ok"` mesmo sem `SEMANTIC_SCHOLAR_API_KEY`, pois a chave é opcional.
- **O que não deu para verificar:**
  - Teste manual interativo na interface gráfica do MCP Inspector (o handshake e as chamadas MCP por stdio foram verificados de ponta a ponta em subprocesso real usando `mcp.Client` com `StdioServerParameters(command=shutil.which("rslapp"))`).

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev python -c "from rslapp.server import list_sources; print(list_sources())"
   ```
2. **O que deve aparecer:**
   - `All checks passed!` no `ruff check .`
   - `23 passed` nas duas execuções do `pytest` (Python 3.10 e Python 3.14).
   - No comando manual (sem chaves no ambiente): `[{'name': 'openalex', 'configured': False, 'needs_key': True, 'status': 'missing_key'}, {'name': 'crossref', 'configured': True, 'needs_key': False, 'status': 'ok'}, {'name': 'semantic_scholar', 'configured': True, 'needs_key': False, 'status': 'ok'}]`.
3. **Onde olhar primeiro (pontos de risco, do mais crítico ao menos crítico):**
   1. **Não exposição de chaves nas respostas e instruções do MCP (`src/rslapp/server.py` — `INSTRUCTIONS` e `list_sources()`, NFR-03):** confirmar que `INSTRUCTIONS` é uma constante estática sem interpolação de variáveis de ambiente e que `list_sources()` repassa apenas os booleanos `configured` e `needs_key` e o estado (`"ok"` ou `"missing_key"`), nunca o valor de `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` ou `RSL_CONTACT_EMAIL`.
   2. **Pureza do canal stdio e leitura dinâmica de configuração (`src/rslapp/server.py` — `list_sources()` e `main()`, D-006, FR-07, NFR-02):** verificar que nada escreve em `stdout` na importação nem na execução da ferramenta (para não corromper o protocolo JSON-RPC por stdio) e que `config.load()` é chamado dentro de `list_sources()` a cada invocação.
   3. **Compatibilidade do schema de saída com Python 3.10 (`src/rslapp/server.py` — `SourceInfo`, D-006):** conferir o uso de `typing_extensions.TypedDict` em `SourceInfo`, exigido pelo Pydantic 2 em Python `< 3.12` ao gerar o schema da ferramenta no `MCPServer`.
