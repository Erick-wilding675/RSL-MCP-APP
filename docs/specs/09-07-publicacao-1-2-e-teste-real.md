# Publicação da 1.2.0 e teste real

**Fase:** 9 · Versão 1.2 · **Situação:** pronta

## O que faz

Publica a fase 9 como `rslapp` 1.2.0 (só acrescenta, então é uma versão menor), atualiza o servidor de teste e faz o teste de ponta a ponta.

- **Publicação** (Claude Code, como na 1.1.0):
  - `version` no `pyproject.toml` e `__version__` em `src/rslapp/__init__.py`;
  - os gates;
  - `uv build --no-sources` e conferência do sdist;
  - `lore secrets run --env prod -- uv publish`, só com os arquivos da 1.2.0;
  - tag `v1.2.0`, que gera a imagem no ghcr.io;
  - `gh release create`;
  - conferência com `uvx` e com a imagem.
- **Servidor de teste:** `docker compose pull && docker compose up -d` na máquina `rsl-app` (D-019), e `/health` respondendo `1.2.0`.
- **Teste real do Erick:**
  1. No Claude Desktop (stdio, pelo PyPI), uma busca de saúde com `pubmed` e `europe_pmc`. A lista mostra as cinco fontes, sem duplicatas visíveis.
  2. Exportar essa lista em BibTeX e importar no Zotero.
  3. Fazer duas buscas do mesmo assunto com strings diferentes, juntar com `merge_lists`, exportar em RIS e abrir no VOSviewer.
  4. No conector de `rsl.sinteselabs.com`, pedir o log de buscas e baixar o `log.md` pelo link.

## O que não faz

- Não anuncia o modo hospedado (espera a LGPD, T-007).

## Pronto quando

- [x] `rslapp` 1.2.0 no PyPI, conferida com `uvx`
- [x] Imagem `1.2.0` e `latest` no ghcr.io, e o servidor de teste atualizado
- [x] Tag e release `v1.2.0` no GitHub
- [x] Os quatro passos do Erick passam (Zotero, VOSviewer e Claude Desktop conferidos pelo Erick em 2026-11-11)
- [ ] O que o teste achar vira item desta spec ou uma tarefa nova

## Vem de

D-008, D-019, D-020, D-021.

## Antes de começar

09-01 a 09-06 integradas. O contrato, o README e o guia de hospedagem atualizados pelo Claude.

## Resultado da entrega

Feita pelo Claude Code em 2026-11-11, depois do "pode publicar" do Erick.

- **Publicação:**
  - versão 1.2.0 no `pyproject.toml` e em `__init__.py`;
  - gates: ruff limpo e 622 testes em 3.10 e 3.14;
  - sdist conferido (95 arquivos, sem `.env`, `.playmaker` nem `.blueprint`);
  - `uv publish` pelo Lore, tag `v1.2.0` e release no GitHub com os dois arquivos;
  - imagem `1.2.0`/`latest` gerada pelas Actions;
  - `uvx --from rslapp==1.2.0` devolve `1.2.0`.
- **Fora do plano, pequena:** o `deploy/docker-compose.yml` não repassava `NCBI_API_KEY` ao contêiner, embora o `.env.example` a listasse. Ganhou a linha, no commit da versão.
- **Servidor de teste:** `git pull` e `docker compose pull && up -d` na `rsl-app`; `/health` responde `{"status":"ok","version":"1.2.0"}`.
- **Passos 1 a 3 sem tela** (script do Claude Code, `rslapp` do PyPI pelo stdio, buscas reais):
  - 9 ferramentas, com `merge_lists`;
  - busca "telemedicine type 2 diabetes glycemic control" nas cinco fontes, as cinco `ok`, 172 artigos de 200 trazidos;
  - nenhum DOI repetido; 50 artigos achados em mais de uma fonte;
  - 62 do PubMed com termos do MeSH; 40 do Europe PMC com citações;
  - `.bib` lido pelo `bibtexparser`: 172 entradas, chaves de citação únicas e `{ }` balanceadas;
  - segunda string ("telehealth diabetes mellitus HbA1c"), com 106 artigos;
  - `merge_lists` deu 252 artigos, com 26 duplicatas removidas;
  - RIS com 252 `TY` e 252 `ER`;
  - `repeat_search` da junção é recusado;
  - o `log.md` tem a entrada "junção".
- **Modo HTTP** (o mesmo pacote em `127.0.0.1`, com duas pessoas de teste):
  - 421 para `Host` estranho em `/health` e nas rotas OAuth;
  - o `.bib` vem por link com `application/x-bibtex`;
  - `get_search_log` devolve `log_download_url` e `expires_at`, sem `log_file`;
  - o `log.md` baixa com `text/markdown` e `attachment`;
  - o João não lê nem junta a lista da Maria (`list_not_found`), e o log dele não mostra a busca dela;
  - os códigos pessoais não aparecem no log do servidor.
- **Passo 4 no servidor real:** no conector RSL-APP do claude.ai do Erick (Chrome), uma busca só em `pubmed` e `europe_pmc` deu `ok` nas duas fontes e 19 artigos. Os links do `.bib` e do log baixaram com 200, o tipo e o nome de arquivo certos. O `.bib` tem 19 entradas balanceadas, e o `log.md` tem a busca nova. Sem login: `/mcp` dá 401, um download falso dá 404 e o `POST /login` com outro `Origin` dá 403.

**Achados do teste**, nenhum bloqueia a 1.2.0:
- **O OpenAlex traz registros de revisão por pares** (Publons: "Review for…", "Decision letter for…", "Author response for…", tipo `peer-review`). Cada registro tem DOI próprio, então a deduplicação não junta, e foram 9 dos 40 artigos do OpenAlex na busca de diabetes. É ruído numa revisão sistemática e já existia antes da 1.2. Candidato a tarefa: filtrar o tipo `peer-review` na busca do OpenAlex, com decisão do Erick.
- **Um preprint e o artigo publicado entram como dois itens** (Research Square e Trials, DOIs diferentes). Fica como está: a revisão sistemática costuma tratar os dois na triagem.
- **O link de download mostra o id da pessoa:** o token é assinado, não cifrado, e o JSON dentro dele leva `person_id`. É assim desde a 1.1.0 e não é segredo, mas vale saber antes de anunciar o modo hospedado.

## Como testar

O que falta é do Erick, porque precisa das telas. Os arquivos estão em `C:\Users\hulkd\AppData\Local\Temp\rsl-0907-ui3pr2u2\exportacoes\`.

1. **Zotero (passo 2):** importar `l-0001.bib` (Arquivo → Importar). Devem entrar 172 itens, com os acentos certos, os autores como "Sobrenome, Nome" e as organizações inteiras.
2. **VOSviewer (passo 3):** Create → Based on bibliographic data → Read data from reference manager files → RIS, com `l-0003.ris` (252 artigos de duas strings juntadas). Um mapa de coautoria ou de palavras-chave deve abrir.
3. **Claude Desktop (passo 1):** reiniciar o Claude Desktop (o `uvx rslapp` pega a 1.2.0) e pedir uma busca de saúde com PubMed e Europe PMC.

Onde olhar primeiro:
1. No Zotero, títulos com `&`, `%` ou `_` (o escape do BibTeX) e nomes com Filho ou Júnior.
2. No VOSviewer, se a lista juntada abre sem nós repetidos.
