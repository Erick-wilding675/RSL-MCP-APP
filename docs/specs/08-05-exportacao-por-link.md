# Exportação por link temporário

**Fase:** 8 · Uso por link (v2) · **Situação:** a fazer

## O que faz

No modo HTTP, o arquivo exportado fica no servidor, longe de quem usa. Então `export_list` passa a devolver um link de download que vale 1 hora (D-014). A pessoa clica e baixa o mesmo arquivo que o stdio grava, pronto para o VOSviewer.

- **Resposta no modo HTTP:** `export_list` grava o arquivo como hoje, na pasta de exportação da pessoa (08-04), e devolve os mesmos campos de hoje, menos `path`, mais `download_url` (o link) e `expires_at` (data e hora UTC em ISO 8601). O `path` sai porque é um caminho do servidor, que não serve para quem usa e mostraria a estrutura do servidor. No stdio, a resposta não muda.
- **O link:** `<RSL_PUBLIC_URL>/downloads/<token>`. O token leva a pessoa, o nome do arquivo e a validade, assinado com HMAC-SHA256. Não precisa de login para baixar: a assinatura é a permissão, porque o link é aberto no navegador, fora do conector.
- **A chave da assinatura:** `RSL_SECRET_KEY`, se definida (pelo menos 32 bytes). Senão, o servidor gera uma chave aleatória na primeira vez e a guarda em `<RSL_DATA_DIR>/auth/secret.key`, com permissão só do dono onde o sistema permitir. Nunca vai para log nem para resposta.
- **A validade:** `RSL_DOWNLOAD_TTL_MINUTES`, padrão 60.
- **A rota `GET /downloads/{token}`:** confere a assinatura (com `hmac.compare_digest`), a validade, que a pessoa está ativa e que o arquivo existe dentro da pasta de exportação dela (sem `..`, sem caminho absoluto, sem sair da pasta). Se tudo estiver certo, devolve o arquivo com `Content-Disposition: attachment`, o tipo certo de cada formato (RIS, CSV, JSON, texto) e `Cache-Control: no-store`. Link vencido: 410 com uma mensagem curta em português dizendo para pedir a exportação de novo. Assinatura errada ou arquivo fora do lugar: 404, sem dizer o motivo.
- **Formato `openalex_url`:** continua devolvendo o campo `url` como hoje, além do link do arquivo.

## O que não faz

- Não apaga os arquivos exportados quando o link vence: a pessoa pode pedir outro link exportando de novo. Limpar exportações antigas fica para depois.
- Não muda o stdio nem os formatos.
- Não manda o conteúdo do arquivo na resposta (D-014).

## Pronto quando

- [ ] Teste: no modo HTTP, `export_list` em RIS devolve `download_url` e `expires_at` e não devolve `path`; baixar o link devolve exatamente o arquivo gravado, com `Content-Disposition: attachment`
- [ ] Teste: o link baixa nos cinco formatos, com o tipo de conteúdo certo
- [ ] Teste: link vencido (relógio adiantado no teste) recebe 410; link com um caractere trocado recebe 404
- [ ] Teste: um token assinado direito mas apontando para `../`, para um caminho absoluto ou para a pasta de outra pessoa recebe 404
- [ ] Teste: depois de `token revoke` da pessoa, os links dela deixam de baixar
- [ ] Teste: sem `RSL_SECRET_KEY`, a chave é criada uma vez e reaproveitada depois de reiniciar (um link feito antes continua valendo)
- [ ] Teste: no stdio, a resposta de `export_list` continua com `path` e sem `download_url` (os testes que já existem passam)
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)

## Vem de

D-014 (exportação por link temporário), FR-06 (exportação), D-012 (dados por pessoa). São os ids que o código leva como âncoras.

## Antes de começar

08-04 integrada. Ler `src/rslapp/exporters/__init__.py` (`run_export` e o que ele devolve), `src/rslapp/server.py` (`export_list`) e, no SDK, `custom_route` em `mcp/server/mcpserver/server.py`: as rotas dele não exigem login, e é isso que esta rota quer. Ler as páginas da biblioteca padrão de `hmac` e `secrets`.

Atualizar `docs/interface-contract.md` não é do Gemini: o Claude acrescenta a resposta do modo HTTP no contrato.

Cerca de 250 linhas. Um commit para o link assinado e a rota, outro para a resposta de `export_list`, com D-014 no comentário e no nome dos testes.

## Resultado da entrega

- **`src/rslapp/downloads.py` (novo):** implementa o gerenciamento da chave de assinatura HMAC-SHA256 (`RSL_SECRET_KEY` com pelo menos 32 bytes ou geração única e persistência atômica em `<RSL_DATA_DIR>/auth/secret.key` com permissão `0600`), leitura de `RSL_DOWNLOAD_TTL_MINUTES` (padrão 60), assinatura de tokens temporários (`sign_download_token` e `create_download_link`) e o handler `handle_download` da rota `GET /downloads/{token}` (D-014, D-012, FR-06):
  - Confere a assinatura em tempo constante com `hmac.compare_digest`, o formato do identificador da pessoa, o bloqueio de `..`, separadores de pasta e caminhos absolutos, a existência e atividade da pessoa (`people.get(id).is_active`), a validade UTC (devolvendo 410 em português quando vencido e 404 para assinatura inválida, pessoa revogada ou arquivo fora da pasta `people/<id>/exports/`) e entrega os bytes exatos do arquivo com `Content-Disposition: attachment; filename="..."`, `Cache-Control: no-store` e o `Content-Type` de cada formato (`.ris`, `.csv`, `.json` e `.txt`).
- **`src/rslapp/server.py`:**
  - Registra a rota pública `GET /downloads/{token}` via `custom_route` no `MCPServer` (stdio e `_HttpMCPServer`) e garante a chave em `create_http_app` (D-014, D-012, FR-06).
  - Em `export_list`, no modo HTTP (`person_id is not None`), grava o arquivo em `<RSL_DATA_DIR>/people/<id>/exports/` como antes e substitui `path` por `download_url` (`<RSL_PUBLIC_URL>/downloads/<token>`) e `expires_at` (ISO 8601 UTC), mantendo `url` em `openalex_url` e preservando o comportamento de `export_list` no modo stdio (com `path` e sem `download_url`).
- **`tests/test_server_downloads.py` (novo) e `tests/test_server_people_data.py`:** 7 novos testes cobrindo todos os itens de "Pronto quando" (exportação RIS por HTTP e download do arquivo, download nos 5 formatos com `Content-Type` certo e `url` em `openalex_url`, 410 para link vencido e 404 para caractere trocado, 404 para `../`, caminho absoluto ou pasta de outra pessoa, corte imediato após `token revoke`, criação única e reaproveitamento de `auth/secret.key` após reinício, e manutenção de `path` sem `download_url` no stdio), além do ajuste na asserção do retorno de `export_list` HTTP em `tests/test_server_people_data.py`.

## Como testar

Rode os três gates em sequência (nunca em paralelo):

```powershell
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
```

**O que deve aparecer:**
- `All checks passed!` no `ruff check .`.
- `531 passed` (incluindo os 7 testes em `tests/test_server_downloads.py`) tanto no Python 3.10 quanto no Python 3.14.

**Como baixar um arquivo à mão com o servidor local:**
1. Cadastre uma pessoa e suba o servidor HTTP local:
   ```powershell
   uv run rslapp token add maria
   uv run rslapp serve --port 8000
   ```
2. Conecte ao endpoint `http://127.0.0.1:8000/mcp` (autorizando com o código pessoal da `maria`), rode uma busca (`search_works`) e chame `export_list(list_id="l-0001", format="ris")`.
3. A resposta trará `download_url` (`http://127.0.0.1:8000/downloads/<token>`) e `expires_at`, sem `path`. Abra o `download_url` no navegador (ou com `curl -i "<download_url>"`): o arquivo `l-0001.ris` será baixado com `Content-Disposition: attachment; filename="l-0001.ris"`, `Content-Type: application/x-research-info-systems; charset=utf-8` e `Cache-Control: no-store`.

**Onde olhar primeiro (do ponto mais arriscado para o menos arriscado):**
1. **Assinatura HMAC-SHA256, chave secreta e confinamento à pasta da pessoa (`src/rslapp/downloads.py`, `load_secret_key`, `_is_safe_export_filename` e `handle_download`):** valida a assinatura em tempo constante (`hmac.compare_digest`) sobre o payload base64url canônico antes de decodificá-lo, recusa qualquer `..`, barra, drive ou caminho absoluto e confere `target_path.parent == exports_dir` dentro de `<RSL_DATA_DIR>/people/<id>/exports/`, além de exigir pessoa ativa (`person.is_active`) e proteger `auth/secret.key` com `0600` sem jamais expor a chave em logs, erros ou `repr`.
2. **Resposta de `export_list` no modo HTTP vs stdio (`src/rslapp/server.py`, `export_list` e `_resolve_public_url`):** remove `path` apenas quando há pessoa autenticada no modo HTTP (`person_id is not None`), acrescentando `download_url` e `expires_at` e mantendo `url` em `openalex_url`, enquanto o modo stdio continua devolvendo `path` inalterado.
3. **Respostas HTTP 410 vs 404 e tipos MIME dos cinco formatos (`src/rslapp/downloads.py`, `_MEDIA_TYPES` e `handle_download`):** devolve 410 com mensagem curta em português quando o link vence e 404 genérico nos demais casos de recusa, entregando os bytes exatos gravados em disco nos cinco formatos.
