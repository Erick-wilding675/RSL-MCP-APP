# Exportação em BibTeX

**Fase:** 9 · Versão 1.2 · **Situação:** a fazer

## O que faz

`export_list` ganha o formato `bibtex`: um arquivo `.bib` que o Zotero, o Mendeley e o JabRef importam, e que o LaTeX usa direto. Funciona no stdio (grava o arquivo, como os outros formatos) e no modo HTTP (link de download, como na 08-05).

- **Uma entrada por artigo.** O tipo é `@article` quando o artigo tem periódico (`venue`) e o tipo é de artigo de periódico (`article`, `journal-article`, `journal article` ou `review`, sem distinguir maiúsculas). Fora isso, o tipo é `@misc`.
- **Campos:**
  - `title`, entre chaves duplas para o LaTeX não mudar as maiúsculas;
  - `author`, como `Sobrenome, Nome` unidos por ` and `; um nome de organização vai entre chaves para não ser dividido;
  - `year`;
  - `journal` (de `venue`) no `@article`, ou `howpublished` no `@misc`;
  - `doi`, sem `https://doi.org/`;
  - `url` (`https://doi.org/<doi>` quando houver DOI);
  - `abstract`;
  - `keywords`, unidas por `, `;
  - `note`, com as fontes onde o artigo foi achado (por exemplo `Fontes: openalex, pubmed`).
  - Campo vazio não é escrito.
- **Chave de citação:** sobrenome do primeiro autor, ano e primeira palavra significativa do título, só com letras e números ASCII e em minúsculas. Exemplo: `silva2021machine`. Sem autor, entra `anon`; sem ano, `nd`. Quando a chave repete na mesma lista, ganha `a`, `b`, `c`… na ordem da lista.
- **Escape:** em todos os valores, `\ { } % & $ # _ ^ ~` são escapados para o LaTeX. Os acentos ficam em UTF-8, porque o arquivo é gravado em UTF-8 e o Zotero, o JabRef e o biber leem UTF-8. Quebras de linha viram espaço.
- **Arquivo:** `<list_id>.bib` na pasta de exportação, com o mesmo caminho e o mesmo retorno dos outros formatos. No modo HTTP, o download usa o tipo `application/x-bibtex; charset=utf-8`.

## O que não faz

- Não lê BibTeX, só escreve.
- Não promete o formato que o Bibliometrix espera do Scopus ou da Web of Science: o arquivo é BibTeX genérico. Se o Bibliometrix pedir campos próprios, isso vira outra tarefa depois do teste do Erick.
- Não muda os outros formatos.

## Pronto quando

- [ ] Teste: uma lista com artigo de periódico, preprint sem periódico, autor organização, título com `&`, `%`, `_` e `{`, resumo com quebra de linha e artigo sem autor e sem ano gera o `.bib` esperado, campo a campo
- [ ] Teste: duas entradas com a mesma chave base viram `…a` e `…b`
- [ ] Teste: o arquivo lido de volta com um analisador simples (contagem de `@`, chaves balanceadas por entrada) tem uma entrada por artigo
- [ ] Teste: `export_list(format="bibtex")` grava `<list_id>.bib` no stdio, e no modo HTTP o download devolve `application/x-bibtex; charset=utf-8`
- [ ] Teste: `export_list` com um formato desconhecido continua dando o mesmo erro de hoje
- [ ] Os três gates passam

## Vem de

FR-06, D-014. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/exporters/__init__.py` (`_EXPORTERS`, `run_export`), `src/rslapp/exporters/base.py`, `src/rslapp/exporters/ris.py` e o teste dele, `src/rslapp/server.py` (`export_list`) e `src/rslapp/downloads.py` (`_MEDIA_TYPES`). O formato de referência é o do BibTeX clássico (documentação `btxdoc`, seção sobre tipos de entrada e campos): `@article` exige `author`, `title`, `journal` e `year`, e `@misc` não exige nenhum campo.

Cerca de 250 linhas, testes incluídos. Um commit, com FR-06 no comentário e no nome dos testes.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
