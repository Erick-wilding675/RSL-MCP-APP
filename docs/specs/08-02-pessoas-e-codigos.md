# Pessoas e códigos

**Fase:** 8 · Uso por link (v2) · **Situação:** a fazer

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

- [ ] Teste: `token add maria` cria a pessoa, mostra um código que começa com `rsl_`, e o `people.json` não contém o código em texto, só o hash
- [ ] Teste: `find_by_code` acha a pessoa com o código certo e devolve `None` com um código errado, com um código de pessoa revogada e com texto vazio
- [ ] Teste: `token add maria` de novo é recusado; `token add maria --replace` gera outro código, o antigo deixa de valer e `code_created_at` muda
- [ ] Teste: `token revoke maria` deixa a pessoa revogada e mantém a pasta `people/maria/`; `token list` mostra `revogada` e não mostra código nem hash
- [ ] Teste: `user purge maria --yes` apaga o cadastro e a pasta `people/maria/`, e não toca em `people/joao/`; sem `--yes`, digitar outro texto cancela sem apagar nada
- [ ] Teste: `token add "../x"`, `token add Maria`, `token add ""` e um id com 41 caracteres são recusados
- [ ] Teste: duas chamadas de `token add` ao mesmo tempo (threads) não perdem nenhuma das pessoas
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-012 (código por pessoa, que separa os dados), D-016 (comando, só o hash, revogar sem apagar, apagar à parte), D-007 (só arquivos), D-004 (dados pessoais só onde roda o servidor). São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/store/_atomic.py`, `src/rslapp/config.py` e `docs/data-classification.md` (a linha das pessoas que usam um servidor hospedado). Ler as páginas da biblioteca padrão de `secrets` e `hmac.compare_digest`.

Cerca de 300 linhas, testes incluídos. Um commit para o cadastro e os comandos, outro para o `purge`, com D-016 no comentário e no nome dos testes.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega: os comandos dos três gates, os comandos à mão numa pasta temporária, o que deve aparecer e os pontos mais arriscados, o mais difícil primeiro)
