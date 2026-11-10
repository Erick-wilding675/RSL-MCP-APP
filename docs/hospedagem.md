# Guia de hospedagem (uso por link)

<!-- D-011, D-012, D-013, D-014, D-015, D-016, D-017, D-018 -->

Este guia mostra como colocar o **RSL.app** no ar num servidor próprio, com HTTPS automático pelo Caddy, para que pesquisadores de um laboratório, grupo de pesquisa ou equipe usem o servidor como conector por link no Claude ou no Claude Code — sem precisar instalar Python, `uv` nem chaves de API no próprio computador (**D-011**, **D-013**, **D-017**).

O projeto não mantém servidor central: quem hospeda administra a própria instância, configura as chaves das bases e gerencia os códigos de acesso das pessoas (**D-011**, **D-016**).

> [!IMPORTANT]
> **Aviso sobre dados pessoais e LGPD (D-018, T-007)**
> Ao hospedar o RSL.app para outras pessoas, você passa a guardar, no seu servidor:
> - **nomes, ORCID, identificadores nas fontes e afiliações** dos autores dos artigos retornados nas buscas de todas as pessoas do servidor (**D-004**);
> - **os pedidos de busca** feitos por cada pessoa, registrados no log metodológico (`log.md`);
> - **o identificador de cada pessoa cadastrada** (como `maria`), as datas de criação e revogação e os hashes dos códigos e tokens OAuth (**D-012**, **D-016**).
>
> A conferência jurídica do projeto sobre o que a **LGPD** exige para esse cenário (**T-007**) **ainda está pendente** (**D-018**). Para atender a qualquer pessoa usuária que peça a remoção dos seus registros no servidor, use o comando de exclusão definitiva (`user purge`) descrito na seção [Manutenção](#5-manutenção-apagar-dados-atualizar-e-fazer-cópia).

---

## 1. Do que você precisa

1. **Um servidor Linux com Docker e Docker Compose** instalados (`docker compose version`).
2. **Um domínio ou subdomínio próprio** (por exemplo, `rsl.seu-laboratorio.org`) com registro DNS **A** (e **AAAA**, se houver IPv6) apontando para o IP público do servidor.
3. **As portas `80` (TCP) e `443` (TCP e UDP) abertas** no firewall do servidor, para que o Caddy obtenha e renove sozinho o certificado HTTPS (Let's Encrypt / ZeroSSL). O Claude só aceita conectores remotos por HTTPS (**D-017**).
4. **Uma chave gratuita do OpenAlex**, obrigatória (**D-013**). Crie em [openalex.org/settings/api](https://openalex.org/settings/api) e **ative pelo link enviado por e-mail**.
5. **Opcional:** uma chave gratuita da [Semantic Scholar](https://www.semanticscholar.org/product/api#api-key-form) e um e-mail de contato para identificação na Crossref (`RSL_CONTACT_EMAIL`). As chaves ficam somente no servidor e atendem a todas as pessoas cadastradas (**D-013**).

---

## 2. Subir o servidor

1. Copie a pasta [`deploy/`](../deploy/) deste repositório para o servidor (elle contém `docker-compose.yml`, `Caddyfile` e `.env.example`):

```bash
git clone https://github.com/Erick-wilding675/RSL-MCP-APP.git
cd RSL-MCP-APP/deploy
```

2. Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

3. Edite o `.env` com o seu domínio e as suas chaves:

```dotenv
RSL_DOMAIN=rsl.seu-laboratorio.org
RSL_PUBLIC_URL=https://rsl.seu-laboratorio.org
OPENALEX_API_KEY=sua-chave-do-openalex
SEMANTIC_SCHOLAR_API_KEY=
RSL_CONTACT_EMAIL=contato@seu-laboratorio.org
```

> [!NOTE]
> `RSL_PUBLIC_URL` deve começar com `https://` e ter exatamente o mesmo domínio de `RSL_DOMAIN`, sem barra no final. O servidor recusa chamadas cujo cabeçalho `Host` não corresponda a `RSL_PUBLIC_URL`.

4. Suba os containers em segundo plano:

```bash
docker compose up -d
```

5. Confira se os dois serviços estão no ar e se o certificado HTTPS responde:

```bash
docker compose ps
curl https://rsl.seu-laboratorio.org/health
```

A resposta esperada é `{"status":"ok","version":"..."}`.

### Cuidados com a rede

- **Não publique a porta 8000 do `rslapp`.** No compose, só o Caddy alcança o `rslapp`, e por isso o `RSL_FORWARDED_ALLOW_IPS=*` é seguro. Se alguém publicar a porta 8000 para fora, qualquer pessoa pode mandar um `X-Forwarded-For` falso e driblar o limite de tentativas de login por IP.
- **Atrás de outro proxy** (o da universidade, um balanceador), configure `RSL_FORWARDED_ALLOW_IPS` com o IP desse proxy e confira que ele repassa o IP real de quem acessa. Se não repassar, todos parecem vir do mesmo IP, e 20 códigos errados de qualquer pessoa bloqueiam o login de todos por 15 minutos.

---

## 3. Cadastrar e gerenciar as pessoas

Cada pessoa que vai usar o servidor recebe um identificador (de 1 a 40 caracteres: letras minúsculas sem acento, números, `-` ou `_`) e um **código pessoal** gerado pelo comando `rslapp token` (**D-012**, **D-016**).

### Cadastrar uma pessoa

```bash
docker compose exec rslapp rslapp token add maria
```

O comando mostra o código pessoal (`rsl_...`) **uma única vez**. O servidor guarda apenas o hash SHA-256 do código em `/data/auth/people.json`:

- Envie o código `rsl_...` para a pessoa por um canal privado.
- Se a pessoa perder o código (ou se você quiser trocar o código de alguém e reativar a conta), gere um novo com `--replace`. O código anterior e as sessões antigas deixam de valer na hora:

```bash
docker compose exec rslapp rslapp token add maria --replace
```

### Listar as pessoas cadastradas

```bash
docker compose exec rslapp rslapp token list
```

Mostra o identificador, a data de criação, a data do código atual e a situação (`ativa` ou `revogada`), sem jamais mostrar código nem hash.

### Revogar o acesso de uma pessoa

```bash
docker compose exec rslapp rslapp token revoke maria
```

A revogação corta o acesso e os links de download da pessoa imediatamente, sem precisar reiniciar o servidor e **sem apagar** as listas, as buscas e o `log.md` dela (**D-016**).

---

## 4. Como cada pessoa conecta o Claude

Cada pessoa logada tem a própria pasta de buscas, listas, exportações e `log.md`, isolada das demais (**D-012**). Quando a pessoa pede uma exportação (`export_list`), a IA devolve um link temporário (`download_url`, válido por 1 hora) para baixar o arquivo direto no navegador e abrir no VOSviewer (**D-014**).

### No Claude (web ou Claude Desktop)

1. Abra as configurações de conectores MCP personalizados no Claude e adicione um novo conector remoto.
2. Preencha os campos:
   - **URL:** `https://<domínio>/mcp` (por exemplo, `https://rsl.seu-laboratorio.org/mcp`)
   - **Authentication:** `Sign in now`
   - **OAuth client:** `Register automatically`
3. O navegador abrirá a tela de login do RSL.app em português.
4. Digite o **código pessoal** (`rsl_...`) recebido de quem hospeda e confirme.
5. Depois do login, a sessão permanece ativa sem prazo de expiração até que o código seja trocado ou revogado (**D-015**, **D-016**).

### No Claude Code

Adicione o servidor MCP remoto por HTTP:

```bash
claude mcp add --transport http rslapp https://rsl.seu-laboratorio.org/mcp
```

Na primeira vez em que o conector for usado (ou pelo comando `/mcp` dentro do Claude Code), conclua o login OAuth no navegador digitando o seu código pessoal (`rsl_...`).

---

## 5. Manutenção: apagar dados, atualizar e fazer cópia

### Apagar definitivamente os dados de uma pessoa (`user purge`)

Para remover uma pessoa do cadastro e apagar todas as listas, buscas, `log.md` e exportações dela (`/data/people/<id>/`), mantendo o cache compartilhado das APIs (**D-016**, **D-018**):

```bash
docker compose exec rslapp rslapp user purge maria
```

O comando pede para digitar o identificador (`maria`) de novo para confirmar. Para pular a confirmação interativa:

```bash
docker compose exec rslapp rslapp user purge maria --yes
```

### Atualizar para uma versão nova

Sempre que sair uma versão nova da imagem no `ghcr.io`:

```bash
docker compose pull
docker compose up -d
```

Os dados no volume `rsl_data` e os certificados no volume `caddy_data` são preservados.

### Fazer cópia de segurança (backup) do volume `/data`

Na pasta `deploy/`, rode o comando abaixo para gravar um arquivo `rsl-backup.tar.gz` na pasta atual com todo o conteúdo do volume do `rslapp` (cadastro de pessoas, listas, logs e cache):

```bash
docker compose run --rm --entrypoint tar rslapp -czf - -C /data . > rsl-backup.tar.gz
```

Guarde o arquivo `rsl-backup.tar.gz` em local seguro: ele contém os dados de pesquisa e os nomes, ORCID e afiliações de autores coletados nas buscas (**D-004**, **D-018**).
