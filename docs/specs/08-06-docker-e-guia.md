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

(preenche quem entrega)

## Como testar

(preenche quem entrega: como construir e subir a imagem localmente, o que deve aparecer e os pontos mais arriscados, o mais difícil primeiro)
