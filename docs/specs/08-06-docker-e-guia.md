# Docker, Caddy e guia de hospedagem

**Fase:** 8 · Uso por link (v2) · **Situação:** a fazer

## O que faz

Entrega o que alguém precisa para hospedar o RSL.app num servidor com um domínio próprio (D-017): uma imagem Docker publicada no ghcr.io, um docker-compose com o Caddy fazendo o HTTPS, e um guia em português, com o aviso da LGPD (D-018).

- **`Dockerfile`** na raiz: imagem `python` slim; instala o `rslapp` a partir do próprio repositório (o código da tag); roda como usuário sem privilégio; `RSL_DATA_DIR=/data` num volume; `RSL_HTTP_HOST=0.0.0.0` e `RSL_HTTP_PORT=8000`; `HEALTHCHECK` em `/health`; `CMD ["rslapp", "serve"]`. Nenhuma chave dentro da imagem.
- **`deploy/docker-compose.yml`**, **`deploy/Caddyfile`** e **`deploy/.env.example`**: dois serviços. `rslapp` (imagem do ghcr.io, volume dos dados, sem porta publicada para fora) e `caddy` (portas 80 e 443, volume dos certificados, `reverse_proxy rslapp:8000` para o domínio de `RSL_DOMAIN`). O `.env.example` lista as variáveis com valores de exemplo, nunca reais: `RSL_DOMAIN`, `RSL_PUBLIC_URL`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` (opcional), `RSL_CONTACT_EMAIL` (opcional). Como só o Caddy alcança o `rslapp`, o compose define `RSL_FORWARDED_ALLOW_IPS=*`, com um comentário dizendo por que é seguro só nesse arranjo.
- **`.github/workflows/docker.yml`**: a cada tag `v*`, constrói a imagem para `linux/amd64` e `linux/arm64` e a publica em `ghcr.io/<dono>/<repositório>` (em minúsculas) com as tags da versão e `latest`, usando o `GITHUB_TOKEN` do próprio Actions (permissão `packages: write`). Nenhum segredo novo.
- **`docs/hospedagem.md`** (português do Brasil), para quem hospeda:
  1. o que precisa: um servidor com Docker, um domínio apontando para ele, as portas 80 e 443 abertas e uma chave gratuita do OpenAlex;
  2. subir: copiar a pasta `deploy/`, preencher o `.env` e rodar `docker compose up -d`;
  3. cadastrar as pessoas: `docker compose exec rslapp rslapp token add maria`, entregar o código à pessoa por um canal privado, e listar e revogar;
  4. como cada pessoa adiciona o conector no Claude: URL `https://<domínio>/mcp`, a opção de login que a 08-03 confirmou e "Register automatically" no cliente OAuth; e como fica no Claude Code;
  5. apagar os dados de uma pessoa (`user purge`), atualizar a versão, fazer cópia do volume `/data`;
  6. **aviso da LGPD:** quem hospeda passa a guardar, no próprio servidor, nomes, ORCID e afiliações de autores das buscas de outras pessoas, os pedidos que elas fazem e o identificador de cada uma; a conferência jurídica do projeto (T-007) ainda está pendente; e o comando de apagar os dados existe para atender a quem pedir.
- **README:** uma seção curta "Usar por link (servidor hospedado)" apontando o guia. O modo stdio continua sendo o primeiro jeito de instalar no README.

## O que não faz

- Não hospeda nada: o projeto não mantém servidor (D-011).
- Não publica a imagem agora: a publicação acontece na tag da 08-07.
- Não faz HTTPS no `rslapp` (D-017).
- Não muda código Python, a não ser que algo da imagem exija (dizer no relatório).

## Pronto quando

- [ ] `docker build .` constrói a imagem, e `docker run` com `RSL_PUBLIC_URL=http://127.0.0.1:8000` e a porta mapeada responde `GET /health` (se não houver Docker na máquina, dizer no relatório e deixar o item para o Erick)
- [ ] `docker compose -f deploy/docker-compose.yml config` valida o compose com o `.env.example`
- [ ] A imagem roda como usuário sem privilégio e não contém nenhum valor de chave (conferir com `docker history` e `docker run ... env`)
- [ ] O workflow do Actions passa no `actionlint`, ou é conferido à mão se a ferramenta não estiver disponível
- [ ] O guia cobre os seis itens acima, com comandos que funcionam copiados, e tem o aviso da LGPD
- [ ] Os três gates passam (ruff, pytest em 3.10 e em 3.14)
- [ ] Teste manual do Erick: seguir o guia num servidor de verdade (fica para a 08-07)

## Vem de

D-017 (Docker, Caddy e ghcr.io), D-018 (aviso da LGPD no guia), D-011 (hospedado por quem quiser), D-013 (chaves de quem hospeda). São os ids que os arquivos levam como âncoras, em comentários.

## Antes de começar

08-01 a 08-05 integradas. Ler por inteiro as páginas oficiais do Caddy sobre o `reverse_proxy` e o HTTPS automático, da documentação do Docker sobre `HEALTHCHECK` e usuário sem privilégio, e do GitHub sobre publicar imagens no ghcr.io pelo Actions (`docker/build-push-action`, `docker/login-action`, `docker/metadata-action`), conferindo as versões atuais das actions. Ler a página "Deploy & scale" do SDK (proxy com HTTPS e `allowed_hosts`). Ler `README.md`.

Cerca de 350 linhas, quase tudo arquivo novo. Um commit para a imagem e o compose, outro para o workflow, outro para o guia e o README, com D-017 nos comentários.

## Resultado da entrega

- **O que mudou:**
  - `Dockerfile` e `.dockerignore` (novos, na raiz): imagem `python:3.12-slim` que instala o `rslapp` a partir do próprio repositório (`pip install --no-cache-dir .`), cria o usuário sem privilégio `rslapp` (`uid=10001`, `gid=10001`) e a pasta `/data` com permissão antes de declarar `VOLUME ["/data"]`, define `RSL_DATA_DIR=/data`, `RSL_HTTP_HOST=0.0.0.0` e `RSL_HTTP_PORT=8000`, configura `HEALTHCHECK` consultando `http://127.0.0.1:${RSL_HTTP_PORT}/health` com a biblioteca padrão do Python sob o usuário sem privilégio e inicia com `CMD ["rslapp", "serve"]`, sem nenhuma chave ou segredo na imagem (**D-011**, **D-013**, **D-017**, **NFR-03**).
  - `deploy/docker-compose.yml`, `deploy/Caddyfile` e `deploy/.env.example` (novos): dois serviços (`rslapp` usando `ghcr.io/erick-wilding675/rsl-mcp-app:latest`, volume `rsl_data:/data`, sem porta publicada no host, e `RSL_FORWARDED_ALLOW_IPS=*` documentado como seguro somente porque apenas o container do Caddy alcança `rslapp:8000`; e `caddy` com portas `80` e `443` TCP/UDP, volumes `caddy_data` e `caddy_config`, e `reverse_proxy rslapp:8000` para `{$RSL_DOMAIN}`). O `.env.example` traz valores de exemplo para `RSL_DOMAIN`, `RSL_PUBLIC_URL`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` e `RSL_CONTACT_EMAIL` (**D-011**, **D-013**, **D-017**).
  - `.github/workflows/docker.yml` (novo): workflow disparado em tags `v*` que constrói a imagem para `linux/amd64` e `linux/arm64` com QEMU e Docker Buildx e publica em `ghcr.io/erick-wilding675/rsl-mcp-app` (convertido para minúsculas pelo `docker/metadata-action`) com as tags da versão (`vX.Y.Z`, `X.Y.Z`, `X.Y`) e `latest`, autenticando apenas com `GITHUB_TOKEN` (`packages: write`) (**D-017**).
  - `docs/hospedagem.md` (novo) e `README.md`: guia completo em português do Brasil cobrindo os seis pontos da spec (pré-requisitos, subida com `docker compose up -d`, gestão de pessoas com `token add|list|revoke`, configuração do conector no Claude com URL `https://<domínio>/mcp`, Authentication `Sign in now` e OAuth client `Register automatically` e no Claude Code, manutenção com `user purge`, atualização e backup de `/data`, e aviso em destaque sobre a LGPD e a pendência de **T-007**); seção curta "Usar por link (servidor hospedado)" adicionada ao `README.md` mantendo o modo stdio como instalação principal (**D-011**, **D-012**, **D-013**, **D-014**, **D-015**, **D-016**, **D-017**, **D-018**).
  - Nenhum arquivo em `src/` ou `tests/` precisou ser alterado.
- **Ids servidos:** D-011, D-012, D-013, D-014, D-015, D-016, D-017, D-018 (além de NFR-03 e T-007 referenciados).
- **O que foi assumido:**
  - Na etapa do conector no Claude em `docs/hospedagem.md`, foram documentadas as opções Authentication `Sign in now` e OAuth client `Register automatically` com URL `https://<domínio>/mcp`, conforme a spec `08-03-login-oauth.md` e a documentação do Claude; isso deve ser confirmado no teste real da `08-07`.
  - No `deploy/docker-compose.yml`, as variáveis interpoladas do `.env` têm valores padrão seguros (`${RSL_DOMAIN:-rsl.exemplo.org}`, `${RSL_PUBLIC_URL:-https://rsl.exemplo.org}`, `${OPENALEX_API_KEY:-}`), permitindo que `docker compose -f deploy/docker-compose.yml config` valide o arquivo tanto com `--env-file deploy/.env.example` quanto antes da criação do `deploy/.env`.
- **O que não deu para verificar:**
  - `docker build .`, `docker run` e `docker history`: o cliente `docker` e o `docker compose` (v5.1.3) estão instalados na máquina, mas o daemon do Docker Desktop (`dockerDesktopLinuxEngine`) não está em execução; por isso a validação de `docker compose -f deploy/docker-compose.yml config` (com e sem `--env-file deploy/.env.example`) foi executada e passou, enquanto a construção e execução local da imagem ficaram para o Erick.
  - `actionlint`: a ferramenta não está instalada na máquina; a sintaxe YAML e a estrutura do `.github/workflows/docker.yml` foram conferidas com parser YAML e inspeção manual de cada passo e permissão.
  - Nota sobre o item 1 de "Pronto quando" (`docker run` com `RSL_PUBLIC_URL=http://127.0.0.1:8000`): a imagem define `RSL_HTTP_HOST=0.0.0.0`, e a spec `08-03-login-oauth.md` estabelece que `rslapp serve` em host fora de loopback (`0.0.0.0`) exige `RSL_PUBLIC_URL` começando com `https://` (enquanto `http://` só é aceito em loopback). Ao testar a imagem após a integração da `08-03`, passe `-e RSL_PUBLIC_URL=https://rsl.exemplo.org` (ou sobreponha `-e RSL_HTTP_HOST=127.0.0.1` se usar `http://127.0.0.1:8000` de dentro do próprio container).

## Como testar

1. **Rode os três gates na raiz do repositório (um por vez):**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
   - **O que deve aparecer:** `All checks passed!` no `ruff check .` e `500 passed` nas duas execuções do `pytest` (Python 3.10 e Python 3.14).

2. **Valide o `docker-compose.yml` com o `.env.example`:**
   ```powershell
   docker compose -f deploy/docker-compose.yml config
   docker compose -f deploy/docker-compose.yml --env-file deploy/.env.example config
   ```
   - **O que deve aparecer:** a configuração expandida dos serviços `rslapp` (sem `ports:` publicados, com `expose: ["8000"]`, `RSL_FORWARDED_ALLOW_IPS: '*'` e volume `rsl_data:/data`) e `caddy` (com portas `80` e `443` e `Caddyfile` montado como somente leitura), saindo com código `0`.

3. **Construa e teste a imagem localmente (com o Docker Desktop aberto):**
   ```powershell
   docker build -t rslapp:local .
   docker history rslapp:local
   docker run --rm --entrypoint env rslapp:local
   docker run --rm -d --name rslapp-test -p 8000:8000 -e RSL_PUBLIC_URL=https://rsl.exemplo.org rslapp:local
   curl.exe -H "Host: rsl.exemplo.org" http://127.0.0.1:8000/health
   docker exec rslapp-test id
   docker stop rslapp-test
   ```
   *(Se testar antes da integração da `08-03`, em que `0.0.0.0` ainda é recusado sem login, ou se testar com `RSL_PUBLIC_URL=http://127.0.0.1:8000`, ajuste `-e RSL_PUBLIC_URL` conforme a regra de host da `08-03`.)*
   - **O que deve aparecer:**
     - Em `docker history` e `docker run --rm --entrypoint env`: nenhuma chave (`OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` ou `RSL_SECRET_KEY`) presente nas camadas nem no ambiente da imagem.
     - Em `GET /health`: `{"status":"ok","version":"1.0.1"}` (ou `1.1.0` na `08-07`).
     - Em `docker exec rslapp-test id`: `uid=10001(rslapp) gid=10001(rslapp) groups=10001(rslapp)`.

4. **Onde olhar primeiro (pontos mais arriscados, do mais difícil para o mais simples):**
   1. **Isolamento de rede e `RSL_FORWARDED_ALLOW_IPS=*` no Compose (`deploy/docker-compose.yml` e `deploy/Caddyfile`):** conferir que o serviço `rslapp` usa apenas `expose: ["8000"]` e **não** publica `ports:` no host, garantindo que somente o container do Caddy na rede interna do Docker possa enviar cabeçalhos `X-Forwarded-*` ao `rslapp`.
   2. **Ausência de segredos na imagem, execução sem privilégio e permissão do volume `/data` (`Dockerfile` e `.dockerignore`):** verificar que a imagem copia apenas `pyproject.toml`, `README.md`, `LICENSE` e `src/`, cria `/data` com dono `rslapp:rslapp` (`10001:10001`) antes de `VOLUME ["/data"]` e `USER rslapp`, e não inclui chaves em `ENV` ou camadas.
   3. **Aviso da LGPD, comandos de gestão e fluxo OAuth no guia (`docs/hospedagem.md`):** conferir o alerta sobre os dados pessoais de autores (**D-004**), pedidos de busca e identificadores de usuários guardados no servidor de quem hospeda, a menção à pendência jurídica (**T-007**, **D-018**), o comando `user purge` e as opções de conexão no Claude (`Sign in now` e `Register automatically`, a confirmar no teste real da `08-07`).
