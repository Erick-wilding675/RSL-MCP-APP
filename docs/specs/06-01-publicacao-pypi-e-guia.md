# Publicação no PyPI e guia de instalação

**Fase:** 6 · Publicação · **Situação:** não iniciada

## O que faz

O pacote publicado no PyPI, o comando de entrada conferido no `uvx` e um guia curto (`README.md`) com a configuração do Claude Desktop (`command: uvx`, caminho completo do `uvx` para clientes com interface, onde pôr as chaves), em português.

## O que não faz

Não faz o app desktop. Não cria servidor do projeto.

## Pronto quando

- [ ] Antes de escrever, conferir na documentação do uv e do PyPI como publicar o pacote e definir o comando de entrada
- [ ] Teste: numa máquina limpa, `uvx rslapp` inicia o servidor
- [ ] Teste manual do Erick: a configuração do guia, copiada, conecta o servidor ao Claude Desktop e `list_sources` responde
- [ ] O guia não pede mexer no código (FR-07) e não pede nenhum pagamento (NFR-01)
- [ ] Teste manual do Erick (critério de aceite do projeto): uma busca por linguagem natural devolve lista sem duplicatas, registrada no log, e o arquivo abre no VOSviewer sem edição

## Vem de

FR-07, NFR-01, NFR-02, D-008. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Depende de todas as anteriores. Precisa de conta no PyPI do Erick (ver o plano).

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
