# Correções da revisão geral (2.1)

**Fase:** 12 · Conectar a IA ao app (2.1) · **Situação:** a fazer

## O que faz

Corrige o que a revisão geral do Claude, em 2026-11-16, achou no código já publicado, e marca as ferramentas só de leitura para o ChatGPT (achado da 12-03).

### 1. O `docker-compose.yml` não repassa as variáveis opcionais (bug)

O guia de hospedagem manda ajustar `RSL_DOWNLOAD_TTL_MINUTES` e `RSL_EXPORT_RETENTION_HOURS` no `.env`, mas o `deploy/docker-compose.yml` não as repassa ao container. Quem segue o guia muda o `.env` e nada acontece.

- No serviço `rslapp`, repasse com o mesmo padrão das chaves (`${VAR:-}`): `RSL_DOWNLOAD_TTL_MINUTES`, `RSL_EXPORT_RETENTION_HOURS`, `RSL_ACCESS_TOKEN_MINUTES`, `RSL_CACHE_DAYS` e `RSL_SECRET_KEY`.
- Valor vazio tem de valer o padrão. Hoje as quatro primeiras e a `RSL_SECRET_KEY` já tratam o vazio assim, menos a `RSL_CACHE_DAYS` (item 2).
- Acrescente as cinco ao `deploy/.env.example`, comentadas e sem valor, com o padrão no comentário.

### 2. `RSL_CACHE_DAYS` vazio derruba o servidor (bug)

`_parse_cache_days` em `src/rslapp/config.py` levanta `ValueError` com `RSL_CACHE_DAYS=""` ou só espaços, enquanto as outras variáveis numéricas voltam ao padrão. Com o item 1, o compose passa a mandar vazio quando a pessoa não define. Trate o vazio como o padrão (`7`), igual a `_parse_http_port`. Teste com `""` e `"  "`.

### 3. Ferramentas só de leitura declaradas ao cliente (ChatGPT)

O ChatGPT pede confirmação antes de toda ferramenta que não declara `readOnlyHint`. Declare só onde é verdade: a ferramenta não grava nada na pasta de dados nem fora dela.

- **Só de leitura:** `list_sources`, `get_list`, `get_search_log`.
- **Gravam** (lista nova, busca e entrada no log, ou arquivo): `search_works`, `find_work`, `get_related_works`, `repeat_search`, `merge_lists`, `export_list`. Nelas, declare `readOnlyHint=False` e `destructiveHint=False` (só acrescentam, não apagam nem mudam o que existe).
- Confira na documentação do SDK `mcp` 2.x como passar as anotações ao `@mcp.tool` (o nome da classe e o import, T-009). Não mude o nome, as entradas nem as respostas de nenhuma ferramenta.
- Teste: `tools/list` devolve as anotações certas para as nove ferramentas.

### 4. Conferir a 12-02 depois da integração

Se a 12-02 tiver ficado com o comando `rslapp` (sem argumentos) para quem instalou pelo `pip`, troque por `rslapp-desktop --mcp`, como diz a spec corrigida em 2026-11-16: o `rslapp` não lê o `desktop.json`.

### 5. O comando do VS Code quebra no PowerShell do Windows (bug)

O cartão do VS Code mostra `code --add-mcp '<JSON>'`. O Claude testou em 2026-11-16 com um `.cmd` que imita o `code.cmd`: no Windows PowerShell 5.1, que vem com o Windows, o JSON chega **sem as aspas duplas** (`{name:rslapp,...}`) e não é JSON válido. No Prompt de Comando (`cmd`), com as aspas internas escapadas como `\"` e o JSON entre aspas duplas, chega certo.

- No Windows (`sys.platform == "win32"`), o comando mostrado é `code --add-mcp "<JSON com cada \" escapado>"`, e a linha abaixo do bloco diz: "Cole no Prompt de Comando (cmd), não no PowerShell."
- Fora do Windows, fica como está (aspas simples, para bash e zsh).
- Teste: o comando do Windows, interpretado pelas regras de argumentos do Windows (`subprocess.list2cmdline` ao contrário, ou o caso montado à mão), devolve o mesmo JSON, inclusive com caminho que tem espaço e barras invertidas.

## O que não faz

- Não muda o OAuth nem o anúncio de `token_endpoint_auth_methods_supported`: isso espera o teste do ChatGPT (12-03).
- Não mexe nas duas dívidas da 11-03 (Histórico lento com centenas de buscas; dois caminhos em `settings.py`).

## Para instituições

Os itens 1 e 2 são para quem hospeda: depois da 2.1, as variáveis opcionais do guia passam a valer. O item 3 deixa o uso pelo ChatGPT do servidor da instituição com menos confirmações. A entrega confere a tabela de variáveis opcionais do `docs/hospedagem.md` (seção 2).

## Pronto quando

- [ ] O compose repassa as cinco variáveis, e o `.env.example` as mostra comentadas
- [ ] `RSL_CACHE_DAYS` vazio vale o padrão, com teste
- [ ] `tools/list` traz `readOnlyHint` certo nas nove ferramentas, com teste
- [ ] O caso `pip` usa `rslapp-desktop --mcp`, com teste
- [ ] No Windows, o comando do VS Code é o do Prompt de Comando, com teste
- [ ] Os gates passam: `tests_desktop`, a suíte principal em 3.10 e 3.14, e o ruff

## Vem de

D-011, D-014, D-016, D-017, D-029, FR-20; revisão do Claude em 2026-11-16.

## Antes de começar

- 12-02 integrada.
- Leia `deploy/docker-compose.yml`, `deploy/.env.example`, `src/rslapp/config.py`, `src/rslapp/downloads.py` e os `@mcp.tool` de `src/rslapp/server.py`.
- Um commit por item.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
