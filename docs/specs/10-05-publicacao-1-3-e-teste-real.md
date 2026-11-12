# Publicação da 1.3.0 e teste real

**Fase:** 10 · Bases pagas e filtros (1.3) · **Situação:** a fazer

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

- [ ] `rslapp` 1.3.0 no PyPI, conferida com `uvx`
- [ ] Imagem `1.3.0` e `latest` no ghcr.io, e o servidor de teste atualizado
- [ ] Tag e release `v1.3.0` no GitHub
- [ ] README, contrato e guia de hospedagem atualizados
- [ ] Os passos do Erick passam (os passos 1 e 2 dependem de ele ter acesso ao Scopus e uma chave do Web of Science)
- [ ] O que o teste achar vira item desta spec ou uma tarefa nova

## Vem de

D-022, D-023, D-008, D-019.

## Antes de começar

10-01 a 10-04 integradas.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
