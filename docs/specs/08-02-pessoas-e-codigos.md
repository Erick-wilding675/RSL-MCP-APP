# Pessoas e códigos

**Fase:** 8 · Uso por link (v2) · **Situação:** para testar

## O que faz

Dá a quem hospeda os comandos para cadastrar as pessoas que vão usar o servidor, cada uma com um código pessoal, e para revogá-las e apagar os dados delas (D-012, D-016). O código é o que a pessoa digita na tela de login (08-03).

- **Comandos** (no `src/rslapp/cli.py` da 08-01; se a 08-01 ainda não estiver integrada, criar o `cli.py` com o mesmo desenho: `rslapp` sem argumento continua iniciando o stdio):

| Comando | O que faz |
|---|---|
| `rslapp token add <id>` | Cadastra a pessoa e mostra o código uma vez só, com uma linha dizendo que ele não aparece de novo. Recusa um `<id>` que já existe e está ativo |
| `rslapp token add <id> --replace` | Gera um código novo para uma pessoa que já existe (código perdido) ou que foi revogada, e a reativa. O código antigo para de valer |
| `rslapp token list` | Mostra uma linha por pessoa: `id`, data de criação, data do código atual e situação (`ativa` ou `revogada`). Nunca mostra código nem hash |
| `rslapp token revoke <id>` | Marca a pessoa como revogada. Não apaga nada dos dados dela |
| `rslapp user purge <id>` | Apaga a pessoa do cadastro e a pasta de dados dela (`<RSL_DATA_DIR>/people/<id>/`, usada a partir da 08-04). Pede para digitar o `<id>` de novo para confirmar; `--yes` pula a confirmação |

- **O `<id>`:** de 1 a 40 caracteres, só letras minúsculas sem acento, números, `-` e `_`, começando por letra ou número. Qualquer outro valor é recusado com mensagem clara; isso também impede caminhos como `../`.
- **O código:** gerado com `secrets` (pelo menos 24 bytes aleatórios), no formato `rsl_<texto url-safe>`. O servidor guarda só o SHA-256 dele (o código tem entropia alta, então não precisa de sal nem de função lenta). A comparação usa `hmac.compare_digest`.
- **Onde fica:** `<RSL_DATA_DIR>/auth/people.json`, gravado com as funções de gravação segura que já existem (`atomic_write_replace` e `file_lock` em `src/rslapp/store/_atomic.py`). Cada pessoa: `id`, `created_at`, `code_hash`, `code_created_at`, `revoked_at` (ou `null`). A pasta `auth/` é criada só quando preciso.
- **Funções para as próximas tarefas**, num módulo novo `src/rslapp/people.py`, sem importar nada do MCP: `add`, `replace_code`, `revoke`, `purge`, `list_people`, `find_by_code(code) -> pessoa ativa ou None` e `get(id)`. O `code_created_at` existe para a 08-03 invalidar as sessões abertas antes de um `--replace`.

## O que não faz

- Não tem login nem tela (08-03). Não separa os dados por pessoa (08-04): o `purge` só apaga a pasta `people/<id>/` se ela existir.
- Não guarda e-mail, telefone nem nada além do `id` que quem hospeda escolhe.
- Não escreve código nem hash em log, mensagem de erro ou `repr`.

## Pronto quando

- [X] Teste: `token add maria` cria a pessoa, mostra um código que começa com `rsl_`, e o `people.json` não contém o código em texto, só o hash
- [X] Teste: `find_by_code` acha a pessoa com o código certo e devolve `None` com um código errado, com um código de pessoa revogada e com texto vazio
- [X] Teste: `token add maria` de novo é recusado; `token add maria --replace` gera outro código, o antigo deixa de valer e `code_created_at` muda
- [X] Teste: `token revoke maria` deixa a pessoa revogada e mantém a pasta `people/maria/`; `token list` mostra `revogada` e não mostra código nem hash
- [X] Teste: `user purge maria --yes` apaga o cadastro e a pasta `people/maria/`, e não toca em `people/joao/`; sem `--yes`, digitar outro texto cancela sem apagar nada
- [X] Teste: `token add "../x"`, `token add Maria`, `token add ""` e um id com 41 caracteres são recusados
- [X] Teste: duas chamadas de `token add` ao mesmo tempo (threads) não perdem nenhuma das pessoas
- [X] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-012 (código por pessoa, que separa os dados), D-016 (comando, só o hash, revogar sem apagar, apagar à parte), D-007 (só arquivos), D-004 (dados pessoais só onde roda o servidor). São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/store/_atomic.py`, `src/rslapp/config.py` e `docs/data-classification.md` (a linha das pessoas que usam um servidor hospedado). Ler as páginas da biblioteca padrão de `secrets` e `hmac.compare_digest`.

Cerca de 300 linhas, testes incluídos. Um commit para o cadastro e os comandos, outro para o `purge`, com D-016 no comentário e no nome dos testes.

## Resultado da entrega

- **O que mudou:**
  - `src/rslapp/people.py` (novo, sem importar nada do MCP nem de `server.py`): criada a dataclass imutável `Person` (`code_hash` oculto no `repr`) e as funções `validate_person_id`, `add`, `replace_code`, `revoke`, `purge`, `list_people`, `find_by_code` e `get`, gravando `<RSL_DATA_DIR>/auth/people.json` com `file_lock` e `atomic_write_replace` de `src/rslapp/store/_atomic.py`, gerando códigos `rsl_<token_urlsafe>` com `secrets.token_urlsafe(24)` (24 bytes de entropia), guardando apenas o SHA-256 em disco e comparando hashes com `hmac.compare_digest` (**D-012**, **D-016**, **D-007**, **D-004**).
  - `src/rslapp/cli.py`: acrescentados os subcomandos `rslapp token add <id> [--replace]`, `rslapp token list`, `rslapp token revoke <id>` e `rslapp user purge <id> [--yes]`, mantendo inalterados os caminhos do modo stdio padrão (sem argumentos) e do `rslapp serve` (**D-016**).
  - `tests/test_people.py` (novo): 13 testes cobrindo todos os itens de "Pronto quando" (cadastro e hash em `people.json`, `find_by_code`, recusa de id repetido e `--replace` mudando `code_created_at` e reativando pessoa revogada, `token revoke` mantendo `people/<id>/` e `token list` sem código nem hash, `user purge` com e sem `--yes`, recusa de ids inválidos e chamadas concorrentes de `token add` em threads).
- **Ids servidos:** D-012, D-016, D-007, D-004.
- **O que foi assumido:**
  - `add` e `replace_code` em `rslapp.people` devolvem o código pessoal gerado (`str`) para exibição única no `stdout` do `token add`, enquanto `get`, `find_by_code`, `revoke` e `list_people` devolvem instâncias de `Person` (que ocultam `code_hash` no `repr`/`str` e aceitam acesso por atributo e por chave `person["campo"]`).
  - As datas (`created_at`, `code_created_at`, `revoked_at`) são gravadas em UTC ISO 8601 com microssegundos (`%Y-%m-%dT%H:%M:%S.%fZ`), e `replace_code` garante avanço monotônico mínimo de 1 microssegundo caso o relógio do sistema operacional não tenha avançado entre duas chamadas seguidas.
- **O que não deu para verificar:** nada; todos os itens de "Pronto quando" foram provados por testes automatizados locais em pasta temporária.

## Como testar

1. **Rode os três gates na raiz do repositório:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
   - **O que deve aparecer:** `All checks passed!` no `ruff check .` e `500 passed` nas duas execuções do `pytest` (Python 3.10 e Python 3.14).

2. **Como cadastrar, listar, revogar e apagar à mão numa pasta temporária (`RSL_DATA_DIR`):**
   ```powershell
   $env:RSL_DATA_DIR = Join-Path $env:TEMP "rsl-teste-08-02"
   Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $env:RSL_DATA_DIR
   uv run --isolated --no-editable --reinstall-package rslapp rslapp token add maria
   uv run --isolated --no-editable --reinstall-package rslapp rslapp token list
   uv run --isolated --no-editable --reinstall-package rslapp rslapp token add maria --replace
   uv run --isolated --no-editable --reinstall-package rslapp rslapp token revoke maria
   uv run --isolated --no-editable --reinstall-package rslapp rslapp token list
   New-Item -ItemType Directory -Force "$env:RSL_DATA_DIR\people\maria" | Out-Null
   uv run --isolated --no-editable --reinstall-package rslapp rslapp user purge maria --yes
   Get-Content "$env:RSL_DATA_DIR\auth\people.json"
   ```
   - **O que deve aparecer:**
     - Em `token add maria` e `token add maria --replace`: o identificador `maria`, um código pessoal começando por `rsl_` e o aviso de que ele é mostrado uma vez só e não aparece de novo.
     - Em `token list`: uma linha por pessoa com `id`, `created_at`, `code_created_at` e a situação (`ativa` antes do `revoke`, `revogada` depois), sem código nem hash.
     - Em `user purge maria --yes`: confirmação de que `maria` e sua pasta `people/maria/` foram apagadas, restando `[]` em `auth/people.json`.

3. **Onde olhar primeiro (pontos mais arriscados, do mais difícil para o mais simples):**
   1. **Proteção do código pessoal e comparação em tempo constante (`src/rslapp/people.py` — `Person`, `add`, `replace_code`, `find_by_code`):** conferir que o código `rsl_...` nunca é gravado em `people.json` nem exposto em `repr`, logs ou mensagens de erro, e que `find_by_code` compara apenas o SHA-256 via `hmac.compare_digest` e exige `person.is_active`.
   2. **Validação estrita de `<id>` e contenção de caminho no `purge` (`src/rslapp/people.py` — `validate_person_id` e `purge`):** confirmar que qualquer valor fora de `^[a-z0-9][a-z0-9_-]{0,39}$` (como `../x`, `Maria`, vazio ou 41 caracteres) é recusado antes de tocar no disco e que `shutil.rmtree` só remove subpastas diretas de `<RSL_DATA_DIR>/people/`.
   3. **Concorrência na gravação de `auth/people.json` (`src/rslapp/people.py` — `add`, `replace_code`, `revoke`, `purge`):** verificar que leitura, alteração e escrita atômica (`atomic_write_replace`) ocorrem inteiramente dentro de `file_lock(<RSL_DATA_DIR>/auth/.lock)`.

**Revisão do Claude (2026-11-10):** aprovada. Gates refeitos: ruff limpo, 500 testes em 3.10 e em 3.14. Conferido à mão numa pasta temporária: o código aparece uma vez, o `people.json` não contém nenhum `rsl_`, o `purge` cancela quando a confirmação não confere e `token add ../x` é recusado. Acompanhamentos, não bloqueiam: `token list` sai sem linha de cabeçalho; `Person.__getitem__` é dispensável.
