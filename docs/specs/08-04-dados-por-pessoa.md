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

- **`src/rslapp/store/__init__.py`:** `Store.__init__` agora aceita o parâmetro opcional `cache_dir: Path | str | None = None` (D-012, D-013, D-007). Quando omitido (`None`), continua usando `<data_dir>/cache`, mantendo inalterado o comportamento do modo stdio e os testes existentes do `Store`.
- **`src/rslapp/server.py`:** adicionados `_resolve_person_id()` e `_build_tool_store()` (D-012, D-013, D-007, FR-12, FR-13) e marcação do modo HTTP em `_HostOriginProtectionASGIApp` e `_HttpMCPServer`:
  - No modo stdio (`current_person_id() is None` e fora do modo HTTP), todas as ferramentas continuam usando `RSL_DATA_DIR` e `RSL_EXPORT_DIR`.
  - No modo HTTP com pessoa autenticada (`<id>`), o `Store` usa `<RSL_DATA_DIR>/people/<id>/` para `lists/`, `searches/` e `log.md`, `<RSL_DATA_DIR>/cache/` compartilhado na raiz, e `<RSL_DATA_DIR>/people/<id>/exports/` na exportação (ignorando `RSL_EXPORT_DIR`).
  - Se uma ferramenta rodar no modo HTTP sem pessoa identificada (ou com identificador inválido), levanta `ToolError` antes de criar pastas, consultar fontes ou gravar arquivos.
- **`tests/test_server_people_data.py`:** seis testes cobrindo isolamento de listas e `log.md` entre Maria e João com contadores de ids independentes (`l-0001`, `s-0001`), reuso do cache compartilhado sem nova chamada às fontes, estrutura de pastas em `people/<id>/` e `cache/` na raiz ignorando `RSL_EXPORT_DIR`, preservação do modo stdio na raiz, falha sem gravação no modo HTTP sem pessoa identificada e `rslapp user purge maria --yes` apagando os dados da pessoa e preservando o cache e as outras pessoas.

## Como testar

Rode os três gates, um depois do outro:

```powershell
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
```

**O que deve aparecer:**
- `All checks passed!` no `ruff check .`.
- `524 passed` (incluindo os 6 novos testes em `tests/test_server_people_data.py`) tanto no Python 3.10 quanto no Python 3.14.

**Onde olhar primeiro (do ponto mais arriscado para o menos arriscado):**
1. **Isolamento de dados entre pessoas e bloqueio sem pessoa no modo HTTP (`src/rslapp/server.py`, `_resolve_person_id`, `_build_tool_store` e `_HttpMCPServer`):** valida o `person_id` com `people.validate_person_id` e confere `person_dir_resolved.parent == people_root` antes de montar o `Store`; recusa execução com `ToolError` se `_is_http_mode()` estiver ativo sem `current_person_id()`, impedindo qualquer queda silenciosa na pasta comum `<RSL_DATA_DIR>`.
2. **Exportações por pessoa e `user purge` (`src/rslapp/server.py`, `export_list` e `tests/test_server_people_data.py`):** no modo HTTP, `export_list` grava em `<RSL_DATA_DIR>/people/<id>/exports/` ignorando `RSL_EXPORT_DIR`, o que garante que `rslapp user purge <id> --yes` remova listas, buscas, `log.md` e exportações daquela pessoa mantendo `<RSL_DATA_DIR>/cache/`.
3. **Cache compartilhado separado da pasta da pessoa (`src/rslapp/store/__init__.py`, `Store.__init__`):** `self.cache_dir` aponta para `<RSL_DATA_DIR>/cache/` quando informado, mantendo o `.lock`, `lists/`, `searches/` e `log.md` dentro de `<RSL_DATA_DIR>/people/<id>/`.
