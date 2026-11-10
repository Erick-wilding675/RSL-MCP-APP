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

(preenche quem entrega)

## Como testar

(preenche quem entrega: os comandos dos três gates, como baixar um arquivo à mão com o servidor local, o que deve aparecer e os pontos mais arriscados, o mais difícil primeiro)
