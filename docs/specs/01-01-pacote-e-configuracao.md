# Pacote e configuração

**Fase:** 1 · Esqueleto · **Situação:** não iniciada

## O que faz

O pacote Python `rslapp` com `pyproject.toml` (layout `src/`, Python 3.10 ou mais, dependências `mcp>=2,<3` e `httpx`, `pytest` e `ruff` para desenvolvimento) e o módulo `config.py`. A configuração lê, de variáveis de ambiente: `RSL_DATA_DIR` (padrão: pasta `RSL.app` na pasta do usuário), `RSL_EXPORT_DIR` (padrão: `exports/` dentro da pasta de dados), `RSL_CACHE_DAYS` (padrão 7), `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` e `RSL_CONTACT_EMAIL` (opcional, para a fila educada da Crossref). O comando de entrada `rslapp` aponta para o servidor (criado na tarefa 01-02).

## O que não faz

Não tem servidor MCP, fontes nem armazenamento. As chaves só são lidas, nunca gravadas nem devolvidas.

## Pronto quando

- [ ] `pip install -e .` e `pytest` rodam sem erro num ambiente limpo
- [ ] `ruff check` passa
- [ ] `config.load()` devolve as pastas e quais chaves estão configuradas (sim ou não), sem expor o valor de nenhuma chave
- [ ] Teste: sem nenhuma variável, os padrões são usados; com `RSL_DATA_DIR` definido, a pasta muda
- [ ] Teste: o texto devolvido por `repr` e por `str` da configuração não contém o valor de nenhuma chave

## Vem de

FR-07, NFR-02, NFR-03, D-001, D-008. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Nenhuma.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
