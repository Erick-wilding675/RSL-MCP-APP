# Dados separados por pessoa

**Fase:** 8 · Uso por link (v2) · **Situação:** a fazer

## O que faz

No modo HTTP, cada pessoa logada tem as próprias buscas, listas, log e exportações, e não vê as de mais ninguém (D-012). O cache das respostas das APIs continua um só para o servidor inteiro, para não gastar a cota de quem hospeda duas vezes com a mesma busca (D-013).

- **Pastas:** a pessoa `maria` usa `<RSL_DATA_DIR>/people/maria/` como pasta de dados (com `searches/`, `lists/`, `log.md` e `exports/` dentro). O cache fica em `<RSL_DATA_DIR>/cache/`, compartilhado. O `Store` passa a aceitar a pasta do cache separada da pasta de dados (parâmetro opcional; sem ele, tudo continua como hoje).
- **Nas ferramentas:** cada ferramenta monta o `Store` a partir de `current_person_id()` (08-03). No stdio (`None`), usa `RSL_DATA_DIR` e `RSL_EXPORT_DIR` como hoje, sem nenhuma mudança. No modo HTTP, a pasta de exportação é `people/<id>/exports/`, e `RSL_EXPORT_DIR` é ignorado.
- **Sem pessoa no modo HTTP:** se uma ferramenta rodar no modo HTTP sem pessoa identificada (o que o login deveria impedir), ela falha com erro, sem cair na pasta comum.
- **Ids das listas e buscas:** continuam `l-0001`, `s-0001` etc., contados por pessoa. A `l-0001` da Maria e a `l-0001` do João são listas diferentes.
- **Log legível:** cada pessoa tem o próprio `log.md`, que é o que ela anexa na metodologia.

## O que não faz

- Não muda nenhuma ferramenta, entrada ou campo de resposta. O `log_file` de `get_search_log` no modo HTTP continua devolvendo o caminho, que só tem sentido no servidor; o download do log fica para depois, se o Erick quiser.
- Não migra dados de quem já usava o modo HTTP sem login (a 08-01 não foi publicada).
- Não muda o stdio.

## Pronto quando

- [ ] Teste: Maria faz uma busca e o João, logado, chama `get_list` com o `list_id` dela e recebe `list_not_found`; `get_search_log` do João não mostra a busca dela
- [ ] Teste: a mesma busca feita pela Maria e depois pelo João usa o cache na segunda vez (nenhuma chamada nova às fontes, com fontes falsas que contam as chamadas)
- [ ] Teste: as pastas de cada pessoa ficam em `people/<id>/`, e o cache em `cache/` na raiz
- [ ] Teste: no stdio, tudo continua na raiz de `RSL_DATA_DIR`, como na 1.0.1 (os testes que já existem passam sem mudança)
- [ ] Teste: uma ferramenta no modo HTTP sem pessoa identificada falha com erro e não grava nada
- [ ] Teste: `user purge maria --yes` (08-02) apaga as listas, o log e as exportações dela e mantém o cache
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-012 (o código separa os dados), D-013 (chaves e cota de quem hospeda), D-007 (só arquivos), FR-12 e FR-13 (listas salvas e log legível). São os ids que o código leva como âncoras.

## Antes de começar

08-02 e 08-03 integradas. Ler `src/rslapp/store/__init__.py` (construtor do `Store` e onde ele usa `cache_dir`), `src/rslapp/store/cache.py`, `src/rslapp/server.py` e o `current_person_id()` da 08-03.

Cerca de 250 linhas. Um commit para o `Store` com cache separado, outro para as ferramentas usarem a pasta da pessoa, com D-012 no comentário e no nome dos testes.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega: os comandos dos três gates, o que deve aparecer e os pontos mais arriscados, o mais difícil primeiro)
