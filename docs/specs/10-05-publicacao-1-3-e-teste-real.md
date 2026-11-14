# Publicação da 1.3.0 e teste real

**Fase:** 10 · Bases pagas e filtros (1.3) · **Situação:** pronta (2026-11-14), falta só o Web of Science

## O que faz

Publica a fase 10 como `rslapp` 1.3.0 (só acrescenta) e faz o teste real com as chaves do Erick.

- **Publicação:** como na 1.2.0 (09-07).
  - Versão no `pyproject.toml` e em `__init__.py`, os gates e o sdist conferido.
  - `uv publish` pelo Lore, tag `v1.3.0`, imagem no ghcr.io e `gh release create`, com uma nota clara: as bases pagas só funcionam com as chaves e o acesso do próprio usuário ou da instituição, e só no RSL.app instalado no computador.
  - Conferência com `uvx`.
  - Servidor de teste atualizado.
- **Documentos (Claude):**
  - README com a seção "Bases pagas: Scopus e Web of Science": como criar as chaves, o acesso pela rede da instituição ou pelo `SCOPUS_INSTTOKEN`, o limite de 50 pedidos por dia do plano de teste do Web of Science e o que os termos permitem (dados para a própria pesquisa, crédito à fonte, o prazo de 3 meses da Clarivate sem licença de arquivo);
  - o contrato (`include_peer_review`, os nomes novos, as colunas do CSV);
  - o guia de hospedagem (por que as bases pagas não aparecem no servidor).
- **Teste real do Erick:**
  1. No Claude Desktop, com `SCOPUS_API_KEY` (e `SCOPUS_INSTTOKEN`, se a biblioteca der um) na rede da universidade ou pela VPN, uma busca com `scopus`. A lista traz autores com afiliações e resumo, ou diz "visão reduzida".
  2. Com `WOS_STARTER_API_KEY`, uma busca com `web_of_science`.
  3. A busca de diabetes da 09-07 repetida sem pareceres: os registros "Review for…" somem, e o log diz quantos saíram.
  4. O RIS da busca com `scopus` abre no VOSviewer.
  5. No conector hospedado, `list_sources` não mostra as bases pagas.

## O que não faz

- Não anuncia o modo hospedado (espera a LGPD, T-007).

## Pronto quando

- [x] `rslapp` 1.3.0 no PyPI, conferida com `uvx`
- [x] Imagem `1.3.0` e `latest` no ghcr.io, e o servidor de teste atualizado
- [x] Tag e release `v1.3.0` no GitHub
- [x] README, contrato e guia de hospedagem atualizados
- [~] Os passos do Erick passam: 1, 3 e 4 no teste de 2026-11-13; 5 conferido pelo conector RSL-APP em 2026-11-14 (só as 5 fontes abertas). O 2, Web of Science, espera a chave.
- [x] O que o teste achar vira item desta spec ou uma tarefa nova

## Vem de

D-022, D-023, D-008, D-019.

## Antes de começar

10-01 a 10-04 integradas.

## Resultado da entrega

`rslapp` 1.3.0 publicada em 2026-11-14 (commit `d279909`).

- PyPI conferida com `uvx --from rslapp==1.3.0`; tag e release `v1.3.0`; imagem `1.3.0` e `latest` no ghcr.io pelo Actions; servidor `rsl.sinteselabs.com` atualizado (`/health` 1.3.0).
- Gates: ruff limpo e 675 testes em Python 3.10, 3.12 e 3.14. O sdist (101 arquivos) não leva chave, token nem arquivo de memória.
- O teste real do Scopus passou em 2026-11-13 e a 10-06 foi conferida no VOSviewer pelo Erick. O Web of Science fica para quando a chave sair (`WOS_STARTER_API_KEY`).

## Como testar

1. `curl https://rsl.sinteselabs.com/health` deve responder `"version":"1.3.0"`.
2. `uvx --from rslapp==1.3.0 rslapp --help` deve rodar.
3. Mais arriscado primeiro: no conector hospedado, `list_sources` não pode mostrar `scopus` nem `web_of_science`, e uma busca que as peça deve dar `invalid_input` (D-023).
4. Depois, no stdio com a chave: uma busca com `scopus` grava a busca inteira no `log.md`.
