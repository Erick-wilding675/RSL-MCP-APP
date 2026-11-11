# Polimento do modo hospedado

**Fase:** 9 · Versão 1.2 · **Situação:** a fazer

## O que faz

Fecha os acompanhamentos que ficaram das revisões da fase 8 e um pedido que o teste real deixou claro: no modo HTTP, o log metodológico fica no servidor, longe de quem usa.

1. **Proteção de domínio em todas as rotas.** Hoje só `/mcp` confere o cabeçalho `Host` e o `Origin` (421 para domínio estranho). Passa a valer para todas as rotas do app HTTP: `/login`, `/authorize`, `/token`, `/register`, `/revoke`, os metadados OAuth, `/downloads/...` e `/health`. Os domínios aceitos continuam os de hoje: o domínio de `RSL_PUBLIC_URL` e os de loopback (`127.0.0.1`, `localhost` e `[::1]`, com ou sem porta). Assim o teste de saúde do Docker (`HEALTHCHECK`, que chama `http://127.0.0.1:8000/health` de dentro do contêiner) continua funcionando.
2. **Link de download do log.** No modo HTTP, `get_search_log` devolve `log_download_url` e `expires_at` no lugar de `log_file`. O link é assinado como o de exportação (08-05), vale o mesmo tempo (`RSL_DOWNLOAD_TTL_MINUTES`) e baixa o `log.md` da pessoa, com `Content-Type: text/markdown; charset=utf-8` e `Content-Disposition: attachment; filename="log.md"`. No stdio, a resposta não muda.
   - **O token do link** passa a dizer o que baixa: um arquivo de `exports/` (como hoje) ou o `log.md` da pessoa. Um token de log nunca abre outro arquivo, e um token de exportação nunca abre o log.
   - **Links de exportação já emitidos** continuam valendo até vencer. A mudança no formato do token não pode invalidar um link criado antes da atualização.
3. **Limpeza das exportações antigas.** No modo HTTP, cada `export_list` apaga, antes de gravar, os arquivos da pasta `exports/` da própria pessoa com mais de `RSL_EXPORT_RETENTION_HOURS` horas (padrão 24, mínimo 1). Só arquivos normais dessa pasta; nunca sai dela; erro ao apagar um arquivo não impede a exportação. No stdio, nada é apagado: as exportações são arquivos de quem usa.
4. **Relógio sem atributo privado.** `handle_download` deixa de ler `AuthStore._clock`; o relógio passa a ser um parâmetro, injetado nos testes. A verificação `is_symlink()` depois de `resolve()`, que nunca é verdadeira, sai.
5. **Cabeçalho no `token list`.** `rslapp token list` imprime uma linha de cabeçalho (`pessoa  criada_em  codigo_desde  situacao`) antes das linhas.
6. **GitHub Actions sem Node 20.** O workflow `docker.yml` passa a usar as versões das actions que rodam em Node 24 (`actions/checkout`, `docker/setup-qemu-action`, `docker/setup-buildx-action`, `docker/login-action`, `docker/metadata-action` e `docker/build-push-action`). Confira a versão de cada uma na página de releases oficial dela no GitHub antes de mudar (T-001). Se uma ainda não tiver versão com Node 24, ela fica como está, e isso é anotado na entrega.

## O que não faz

- Não muda o stdio.
- Não muda o login, os códigos nem a sessão.
- Não atualiza `docs/hospedagem.md` nem o contrato: o Claude faz isso.

## Pronto quando

- [ ] Teste: `/login`, `/authorize`, os metadados OAuth, `/downloads/<token>` e `/health` com `Host` estranho recebem 421; com o domínio público ou com `127.0.0.1:8000`, respondem como antes
- [ ] Teste: no modo HTTP, `get_search_log` devolve `log_download_url` e `expires_at` e não devolve `log_file`; o link baixa exatamente o `log.md` da pessoa; no stdio, `log_file` continua
- [ ] Teste: um token de log não abre um arquivo de exportação, e o contrário também não; um token de log da Maria não abre o log do João; link vencido dá 410; pessoa revogada dá 404
- [ ] Teste: um link de exportação criado com o formato de token da 1.1.0 continua baixando
- [ ] Teste: com arquivos antigos e novos em `exports/` (datas de modificação ajustadas no teste), `export_list` no HTTP apaga só os antigos da própria pessoa; no stdio, não apaga nada
- [ ] Teste: `handle_download` não acessa atributo privado de `AuthStore`
- [ ] Teste: `token list` começa pelo cabeçalho
- [ ] O `docker.yml` usa as versões conferidas, e o `docker build` local ainda passa (anotar se não deu para rodar)
- [ ] Os três gates passam

## Vem de

D-012, D-014, D-016, D-017, FR-05, FR-13. São os ids que o código leva como âncoras.

## Antes de começar

Ler `src/rslapp/server.py` (`_HostOriginProtectionASGIApp`, `create_http_app`, `get_search_log`, `export_list`), `src/rslapp/downloads.py` inteiro, `src/rslapp/cli.py` (`token list`), `src/rslapp/auth/store.py` (o relógio), `Dockerfile`, `.github/workflows/docker.yml` e os testes `tests/test_server_http.py` e `tests/test_server_downloads.py`.

Cerca de 400 linhas, no limite. Um commit por item (1 a 6), com os ids no comentário e no nome dos testes. Se passar de 400 linhas, entregue os itens 1 a 3 e devolva o resto, dizendo o que ficou.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
