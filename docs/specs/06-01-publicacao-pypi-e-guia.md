# Publicação no PyPI e guia de instalação

**Fase:** 6 · Publicação · **Situação:** pronta

## O que faz

O pacote publicado no PyPI, o comando de entrada conferido no `uvx` e um guia curto (`README.md`) com a configuração do Claude Desktop (`command: uvx`, caminho completo do `uvx` para clientes com interface, onde pôr as chaves), em português.

## O que não faz

Não faz o app desktop. Não cria servidor do projeto.

## Pronto quando

- [X] Antes de escrever, conferir na documentação do uv e do PyPI como publicar o pacote e definir o comando de entrada (guia de pacotes do uv lido em 2026-11-05: `uv build --no-sources`, `uv publish` com `UV_PUBLISH_TOKEN`)
- [X] Teste: numa máquina limpa, `uvx rslapp` inicia o servidor (conferido em 2026-11-05 com `uvx --isolated --refresh rslapp@1.0.0` vindo do PyPI, de outra pasta e sem chaves: 8 ferramentas, `list_sources` responde)
- [x] Teste manual do Erick: a configuração do guia, copiada, conecta o servidor ao Claude Desktop e `list_sources` responde (2026-11-05, com o `rslapp` do PyPI)
- [X] O guia não pede mexer no código (FR-07) e não pede nenhum pagamento (NFR-01)
- [x] Teste manual do Erick (critério de aceite do projeto): uma busca por linguagem natural devolve lista sem duplicatas, registrada no log, e o arquivo abre no VOSviewer sem edição (2026-11-05)

## Vem de

FR-07, NFR-01, NFR-02, D-008. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Depende de todas as anteriores. Precisa de conta no PyPI do Erick (ver o plano).

## Resultado da entrega

Feita pelo Claude Code em 2026-11-05, a pedido do Erick ("escreve o readme", "faz a release da v1"), sem worker.

- **`README.md`:** o que o RSL.app faz e o que não faz, do que precisa (uv, chave do OpenAlex, chave opcional da Semantic Scholar), configuração do Claude Desktop com `uvx rslapp`, Claude Code e outros clientes, exemplos de pedidos, como abrir cada formato no VOSviewer, onde ficam os arquivos, as variáveis de ambiente, as ferramentas, dados pessoais e como desenvolver.
- **`pyproject.toml`:** versão 1.0.0, `readme`, licença, autor, palavras-chave, classificadores e links. O sdist passa a levar só `src/rslapp`, `tests`, o README, a licença e o `pyproject.toml`: antes levaria `.playmaker/` (quadro e logs dos workers), `.blueprint/` e os arquivos dos agentes.
- **`__version__`** em 1.0.0. O teste da versão passou a comparar o metadado instalado com `rslapp.__version__`, em vez de um número fixo.
- **Publicação:** `rslapp 1.0.0` no PyPI (wheel e sdist), com o token vindo do Lore (`lore secrets run --env prod -- uv publish`). Tag `v1.0.0` e release no GitHub com os dois arquivos.
- **O que não deu para verificar:** o guia copiado por outra pessoa, num computador sem nada instalado.

## Como testar

1. **Gates:** os três de sempre; deve aparecer `All checks passed!` e `455 passed` em Python 3.10 e 3.14.
2. **Do PyPI:** `uvx --refresh rslapp@1.0.0` sobe o servidor por stdio (fica esperando; feche com Ctrl+C).
3. **Guia (Erick):** no Claude Desktop, trocar o `--from <pasta>` da configuração atual por `rslapp`, reabrir e pedir "quais fontes do rslapp estão prontas?". Depois, uma busca por linguagem natural exportada em RIS e aberta no VOSviewer.

**Onde olhar primeiro:**

1. **O que foi publicado:** https://pypi.org/project/rslapp/1.0.0/ e a lista de arquivos do sdist (`tar -tzf dist/rslapp-1.0.0.tar.gz`): nada de `.playmaker/`, `.blueprint/` ou dados.
2. **O token do PyPI:** o primeiro foi criado com escopo da conta inteira, porque o projeto não existia. Trocado em 2026-11-05 por um token só do projeto `rslapp`, guardado no Lore como `UV_PUBLISH_TOKEN`.
3. **O README:** confere com o que o servidor faz (contrato em `docs/interface-contract.md`).
