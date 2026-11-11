# Publicação da 1.1.0 e teste real

**Fase:** 8 · Uso por link (v2) · **Situação:** em andamento (publicada; falta o teste real do Erick)

## O que faz

Publica a v2 como `rslapp` 1.1.0 (o modo stdio não muda, então é uma versão menor) e faz o teste de ponta a ponta que fecha a fase 8.

- **Publicação** (Claude Code, como na 1.0.1): `version` no `pyproject.toml` e `__version__` em `src/rslapp/__init__.py`; `uv build --no-sources`; conferir o sdist (`tar -tzf`); `lore secrets run --env prod -- uv publish` só dos arquivos da 1.1.0; tag `v1.1.0`, que dispara a publicação da imagem no ghcr.io (08-06); `gh release create` com notas em português; conferir com `uvx` vindo do PyPI e com `docker pull` da imagem.
- **Teste real do Erick**, seguindo o `docs/hospedagem.md` copiado:
  1. subir o compose num servidor com domínio e HTTPS;
  2. cadastrar dois códigos (`erick` e um segundo);
  3. no Claude, adicionar o link como conector, fazer login com o código dele, fazer uma busca e baixar o RIS pelo link, e abrir no VOSviewer;
  4. com o segundo código (outra conta ou o Claude Code), conferir que as listas do Erick não aparecem;
  5. revogar o segundo código e conferir que ele perde o acesso na hora.

## O que não faz

- Não anuncia o modo hospedado: isso espera a LGPD (T-007, D-018).
- Não escolhe onde hospedar o teste: é decisão do Erick, porque pode ter custo (um servidor pequeno alugado, uma máquina da universidade ou a máquina dele com as portas abertas). Trazer as opções antes de começar esta tarefa.

## Pronto quando

- [X] `rslapp` 1.1.0 no PyPI e conferido com `uvx`
- [X] Imagem `1.1.0` e `latest` no ghcr.io, baixável sem login (o pacote já nasceu público, não precisou mexer nas configurações)
- [ ] Os itens de Docker que ficaram da 08-06: `docker build`, `docker run` com `/health`, `docker history` e o `env` da imagem sem chave, e o usuário sem privilégio
- [X] Tag e release `v1.1.0` no GitHub
- [ ] Teste manual do Erick: os cinco passos acima passam
- [ ] O que o teste real achar vira itens desta spec ou uma tarefa nova, como na 05-05

## Vem de

D-011, D-015, D-017 e D-018, e D-008 (publicação no PyPI).

## Antes de começar

08-01 a 08-06 integradas e prontas. O Lore conectado (o token do PyPI está nele). O Erick escolhe onde hospedar o teste: escolheu uma máquina da Azure for Students com o subdomínio `rsl.sinteselabs.com` (D-019).

## Resultado da entrega

**Publicação (Claude Code, 2026-11-11):**

- Versão 1.1.0 no `pyproject.toml` e em `src/rslapp/__init__.py` (commit `470aade`, com a D-019). Os três gates passaram antes de publicar: `ruff` sem apontamentos e 531 testes em 3.10 e em 3.14.
- O sdist foi conferido com `tar -tzf`: código, testes, `README.md`, `LICENSE` e `pyproject.toml`, sem `.env`, sem chave e sem pasta de dados. O wheel tem o comando `rslapp = rslapp.cli:main`.
- O `uv publish` enviou só os dois arquivos da 1.1.0, com o token do Lore. Conferido com `uvx --no-cache --from rslapp==1.1.0`, que mostrou `1.1.0`.
- A tag `v1.1.0` e o release estão em [https://github.com/Erick-wilding675/RSL-MCP-APP/releases/tag/v1.1.0](https://github.com/Erick-wilding675/RSL-MCP-APP/releases/tag/v1.1.0), com notas em português e os dois arquivos.
- A tag disparou o workflow `docker.yml`, que terminou com sucesso. A imagem `ghcr.io/erick-wilding675/rsl-mcp-app` tem as tags `1.1.0`, `1.1`, `v1.1.0` e `latest`, para `linux/amd64` e `linux/arm64`. Listei as tags e baixei o manifesto sem login, então o pacote já é público.

**Falta:** os itens de Docker que ficaram da 08-06 (rodam na máquina da Azure, no passo 4 abaixo, porque o Docker Desktop estava desligado) e o teste real do Erick.

## Como testar

O roteiro abaixo segue a D-019: uma máquina da Azure for Students com o subdomínio `rsl.sinteselabs.com`, do domínio da Síntese. As chaves de API você digita só no `.env` da máquina, nunca no chat nem num arquivo do repositório.

**1. O DNS da Síntese.** O DNS do `sinteselabs.com` fica na Hostinger (servidores `dns-parking.com`). Hoje o `rsl.sinteselabs.com` não existe e o domínio não tem registro CAA, então o Let's Encrypt pode emitir o certificado. O site principal, na Vercel, não muda. Deixe o painel da Hostinger aberto: o IP entra no passo 3.

**2. A máquina na Azure.** Ative a Azure for Students em [h[https://azure.microsoft.com/free/students](https://azure.microsoft.com/free/students)ttps://azure.microsoft.com/free/students](https://azure.microsoft.com/free/students) com o e-mail da universidade (não pede cartão). No portal, crie uma máquina virtual:

- Imagem: **Ubuntu Server 24.04 LTS**.
- Tamanho e região: a Azure for Students costuma não ter a **B1s** nas regiões mais procuradas. Em *Tamanho → Ver todos os tamanhos*, procure nesta ordem: **B2ats_v2** (2 vCPU, 1 GB, x64), **B2pts_v2** (2 vCPU, 1 GB, ARM; a imagem tem versão arm64) e **B1s**. Se nenhum aparecer, troque a região e procure de novo: **East US 2**, **Central US**, **West US 2**, **West US 3**, **Canada Central**, **North Europe**. A região não importa para o teste.
- Último recurso, pago com o crédito: **B1ms** (1 vCPU, 2 GB) ou **B2s** (2 vCPU, 4 GB). Custam alguns centavos de dólar por hora; um teste de poucos dias gasta poucos dólares dos US$ 100.
- Autenticação: **chave SSH**, usuário `azureuser`. Baixe o arquivo `.pem` quando o portal oferecer e guarde-o fora do projeto.
- Portas de entrada: **SSH (22)**, **HTTP (80)** e **HTTPS (443)**.

**3. Apontar o nome.** Copie o **IP público** da máquina (na página dela no portal). No hPanel da Hostinger, em *Domínios → sinteselabs.com → DNS / Nameservers*, adicione um registro **A** com nome `rsl`, apontando para esse IP, com TTL 300. Confira no seu computador com `nslookup rsl.sinteselabs.com 8.8.8.8`: deve aparecer o IP da máquina. Pode levar alguns minutos.

**4. Subir o servidor.** No PowerShell, entre na máquina com `ssh -i C:\caminho\da\chave.pem azureuser@<IP>` e rode:

```bash
# Docker (script oficial) e permissão para o seu usuário
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker azureuser
exit
```

Entre de novo com o mesmo `ssh` e continue:

```bash
# 1 GB de memória de reserva, porque a B1s tem só 1 GB
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile

git clone https://github.com/Erick-wilding675/RSL-MCP-APP.git
cd RSL-MCP-APP/deploy
cp .env.example .env
nano .env    # RSL_DOMAIN=rsl.sinteselabs.com, RSL_PUBLIC_URL=https://rsl.sinteselabs.com, sua OPENALEX_API_KEY; Ctrl+O, Enter, Ctrl+X
docker compose up -d
docker compose ps
curl https://rsl.sinteselabs.com/health
```

O que deve aparecer: os dois serviços `Up`, e o `/health` responde `{"status":"ok","version":"1.1.0"}`. O primeiro certificado pode levar meio minuto; se o `curl` falhar, veja `docker compose logs caddy`.

Os itens de Docker que ficaram da 08-06:

```bash
docker compose exec rslapp id                      # uid=10001(rslapp) gid=10001(rslapp)
docker history --no-trunc ghcr.io/erick-wilding675/rsl-mcp-app:1.1.0 | grep -iE "key|secret|token"   # nada
docker run --rm --entrypoint env ghcr.io/erick-wilding675/rsl-mcp-app:1.1.0                        # sem OPENALEX_API_KEY nem outra chave
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health   # 000: a porta 8000 não fica aberta fora do compose
```

**5. Os dois códigos.**

```bash
docker compose exec rslapp rslapp token add erick
docker compose exec rslapp rslapp token add teste2
```

Cada comando mostra o código (`rsl_...`) uma vez só. Anote os dois num lugar seguro.

**6. No Claude, com o código `erick`.** Em *Configurações → Conectores → Adicionar conector personalizado*, use a URL `https://rsl.sinteselabs.com/mcp`. O navegador abre a página de login do RSL.app; digite o código `erick`. Depois:

- peça uma busca curta (por exemplo, "busque artigos sobre revisão sistemática com IA de 2023 a 2025 e salve como lista");
- peça "exporte a lista em RIS": a resposta traz um link de download, sem caminho de pasta;
- abra o link no navegador: baixa `l-0001.ris`;
- abra o arquivo no VOSviewer (*Create → Create a map based on bibliographic data → Read data from reference manager files → RIS*).

**7. No Claude Code, com o código `teste2`.** No seu computador:

```powershell
claude mcp add --transport http rsl-teste2 https://rsl.sinteselabs.com/mcp
```

Abra o Claude Code, rode `/mcp`, autentique o `rsl-teste2` e digite o código `teste2`. Peça "abra a lista l-0001 pelo rsl-teste2" e "mostre o log de buscas pelo rsl-teste2". O que deve aparecer: `list_not_found` e um log vazio. As listas do `erick` não aparecem.

**8. Revogar.** Na máquina, rode `docker compose exec rslapp rslapp token revoke teste2`. No Claude Code, peça qualquer coisa ao `rsl-teste2`: deve falhar e pedir login de novo, e o código `teste2` não entra mais. No Claude, o `erick` continua funcionando.

**9. Depois do teste.** Para não gastar o crédito à toa, pare a máquina no portal (*Parar*), ou apague o grupo de recursos inteiro se não for usá-la mais; nesse caso, apague também o registro `rsl` na Hostinger, para o nome não apontar para um IP que a Azure pode dar a outra pessoa. Parada, ela não cobra processamento, mas o disco e o IP podem cobrar uns centavos por dia.

**Onde olhar primeiro, se algo falhar:**

1. **O login (passos 6 e 7):** se o Claude não abrir a página de login ou voltar com erro, anote a mensagem e rode `docker compose logs rslapp --tail 50`.
2. **O link de download (passo 6):** ele tem de começar com `https://rsl.sinteselabs.com/downloads/`. Se começar com `http://` ou com outro nome, o `RSL_PUBLIC_URL` do `.env` está errado.
3. **A separação entre pessoas (passo 7):** se o `teste2` vir a lista do `erick`, pare o teste e me avise, porque é o defeito mais grave possível aqui.
