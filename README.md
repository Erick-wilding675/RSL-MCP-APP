# RSL.app

**Servidor MCP gratuito para revisão sistemática de literatura.** Você pede à sua IA, em linguagem natural, os artigos de um tema. Ela busca no OpenAlex, na Crossref e na Semantic Scholar, junta os resultados sem duplicatas e grava um arquivo pronto para abrir no [VOSviewer](https://www.vosviewer.com/), com autores, afiliações, palavras-chave, referências e citações.

> Exemplo: *"Quero os artigos sobre burnout em professores da educação básica e, separado, sobre inteligência artificial na correção de redações. Exporte cada um em RIS."*
> A IA faz duas buscas, monta duas listas e entrega dois arquivos `.ris`. Cada busca fica registrada num log legível, que você pode anexar à metodologia do seu artigo.

O RSL.app roda **na sua máquina** (self-hosted), com as **suas** chaves gratuitas. Ele não tem servidor central, não cobra nada e não manda seus dados para lugar nenhum além das próprias bases consultadas.

## O que ele faz

- **Busca por tema, palavra-chave, subtema ou título** nas três bases abertas, ao mesmo tempo.
- **Tira as duplicatas.** O mesmo artigo vindo de mais de uma base aparece uma vez só, com os ids de cada base.
- **Avisa quando a lista está incompleta.** Se uma base falha ou um limite corta a busca, a lista sai marcada como incompleta, com o motivo. Nenhuma lista incompleta passa por completa.
- **Acha um artigo específico** pelo título ou pelo DOI.
- **Traz as referências de um artigo e quem o cita**, como uma lista própria.
- **Registra cada busca num log** (`log.md`): o pedido, a string enviada a cada base, a data, quantos artigos cada base achou e se veio do cache.
- **Repete uma busca do log** com as mesmas strings, para atualizar uma revisão.
- **Exporta em cinco formatos:** RIS, CSV no padrão do Scopus, JSON completo, lista de DOIs e URL de consulta do OpenAlex. O RIS, o CSV e a lista de DOIs abrem no VOSviewer sem edição.
- **Guarda tudo na sua máquina:** listas, log, exportações e um cache das respostas, que expira em 7 dias e economiza sua cota.

Ele **não** baixa texto completo de artigos, não abre o VOSviewer sozinho e não junta buscas diferentes numa lista só: cada pedido vira a sua própria lista.

## Do que você precisa

1. **Uma IA que fale MCP**, como o Claude Desktop, o Claude Code ou outro cliente compatível.
2. **O [uv](https://docs.astral.sh/uv/getting-started/installation/)** instalado. É ele que baixa e roda o RSL.app; você não precisa instalar o Python à mão.
3. **Uma chave gratuita do OpenAlex**, obrigatória. Crie em [openalex.org/settings/api](https://openalex.org/settings/api) e **ative pelo link que chega no e-mail**: a chave só funciona depois disso. Ela dá 10.000 créditos por dia, e uma busca gasta cerca de 10.
4. **Opcional: uma chave gratuita da [Semantic Scholar](https://www.semanticscholar.org/product/api#api-key-form).** Sem ela a Semantic Scholar funciona, mas recusa pedidos com mais frequência.

A Crossref não precisa de chave.

## Instalação no Claude Desktop

1. Feche o Claude Desktop por completo (no Windows, clique com o botão direito no ícone perto do relógio e escolha **Quit**).
2. Abra a configuração: **Settings → Developer → Edit Config**. O arquivo é o `claude_desktop_config.json`.
3. Acrescente o `rslapp` dentro de `"mcpServers"`:

```json
{
  "mcpServers": {
    "rslapp": {
      "command": "uvx",
      "args": ["rslapp"],
      "env": {
        "OPENALEX_API_KEY": "sua-chave-do-openalex",
        "SEMANTIC_SCHOLAR_API_KEY": "sua-chave-da-semantic-scholar"
      }
    }
  }
}
```

4. Salve e abra o Claude Desktop de novo. O `rslapp` aparece na lista de ferramentas, com oito ferramentas.
5. Para conferir, peça: *"Quais fontes do rslapp estão prontas?"*. A IA chama `list_sources` e deve mostrar as três fontes como `ok`.

**Se o Claude Desktop não achar o `uvx`:** troque `"uvx"` pelo caminho completo. No Windows, costuma ser `C:\\Users\\<seu-usuário>\\.local\\bin\\uvx.exe`. No macOS e no Linux, rode `which uvx` no terminal para descobrir.

**Suas chaves ficam só no arquivo de configuração da sua máquina.** O RSL.app nunca as escreve no log, nas listas nem nas respostas à IA.

### No Claude Code

```bash
claude mcp add rslapp -e OPENALEX_API_KEY=sua-chave -e SEMANTIC_SCHOLAR_API_KEY=sua-chave -- uvx rslapp
```

### Em outros clientes MCP

O RSL.app é um servidor MCP por **stdio**. O comando é `uvx rslapp`, e as chaves vão como variáveis de ambiente.

## Usar por link (servidor hospedado)

<!-- D-011, D-017, D-018 -->
Um laboratório, grupo de pesquisa ou pessoa também pode hospedar o RSL.app num servidor próprio com Docker e HTTPS pelo Caddy, gerando um código de acesso individual para cada pesquisador conectar por link (`https://<domínio>/mcp`) sem instalar nada na própria máquina. As chaves das bases e os dados das buscas ficam no servidor de quem hospeda. Veja o passo a passo e o aviso sobre a LGPD em [`docs/hospedagem.md`](docs/hospedagem.md).

## Como usar

Fale com a IA normalmente. Alguns pedidos que funcionam bem:

- *"Busque artigos sobre aprendizagem baseada em projetos no ensino de ciências e exporte em RIS."*
- *"Ache o artigo 'Software survey: VOSviewer, a computer program for bibliometric mapping' e me traga até 200 trabalhos que o citam, de cada base."*
- *"Me mostre o log das buscas de hoje."*
- *"Repita a busca s-0003 e exporte em CSV."*

A IA planeja antes de buscar: se o pedido tem assuntos diferentes, ela faz uma busca e uma lista para cada um.

### Abrir no VOSviewer

| Arquivo | Como abrir no VOSviewer |
|---|---|
| `.ris` | Create → *Create a map based on bibliographic data* → *Read data from reference manager files* → RIS |
| `.csv` | Create → *Create a map based on bibliographic data* → *Read data from bibliographic database files* → aba **Scopus** |
| `.dois.txt` | Create → *Create a map based on bibliographic data* → *Read data through API* |
| `.openalex.txt` | A URL da consulta ao OpenAlex (uma por linha, até 100 artigos cada), com os artigos da lista que vieram do OpenAlex |

O CSV leva as referências como DOIs, o que permite mapas de citação e de acoplamento bibliográfico.

## Onde ficam os arquivos

Por padrão, na pasta `RSL.app` dentro da sua pasta de usuário (no Windows, `C:\Users\<seu-usuário>\RSL.app`):

| Pasta ou arquivo | O que tem |
|---|---|
| `log.md` | O log legível de todas as buscas |
| `exports/` | Os arquivos exportados (`l-0001.ris`, `l-0001.csv`…) |
| `lists/` e `searches/` | As listas e as buscas salvas, para reexportar depois |
| `cache/` | As respostas das bases, por 7 dias |

## Configuração

Tudo por variáveis de ambiente, no bloco `env` da configuração do cliente. Nenhuma exige mexer no código.

| Variável | O que faz | Padrão |
|---|---|---|
| `OPENALEX_API_KEY` | Chave do OpenAlex (obrigatória para o OpenAlex) | - |
| `SEMANTIC_SCHOLAR_API_KEY` | Chave da Semantic Scholar (opcional) | - |
| `RSL_CONTACT_EMAIL` | Seu e-mail, enviado à Crossref, que atende mais rápido quem se identifica (opcional) | - |
| `RSL_DATA_DIR` | Onde guardar listas, log e cache | `~/RSL.app` |
| `RSL_EXPORT_DIR` | Onde gravar as exportações | `<RSL_DATA_DIR>/exports` |
| `RSL_CACHE_DAYS` | Por quantos dias o cache vale | `7` |

## As ferramentas que a IA recebe

| Ferramenta | O que faz |
|---|---|
| `search_works` | Busca por termos nas três bases e cria uma lista |
| `find_work` | Acha um artigo específico por título ou DOI |
| `get_related_works` | Traz as referências ou as citações de um artigo, até um teto por base (padrão 1.000) |
| `repeat_search` | Repete uma busca do log |
| `get_list` | Mostra uma lista salva, por páginas |
| `get_search_log` | Mostra o log e o caminho do `log.md` |
| `export_list` | Grava a lista em `ris`, `csv`, `json`, `dois` ou `openalex_url` |
| `list_sources` | Diz quais bases estão prontas |
| `plan_search` (prompt) | Orienta a IA a planejar e dividir o pedido antes de buscar |

O contrato completo, com entradas, respostas e códigos de erro, está em [`docs/interface-contract.md`](docs/interface-contract.md).

## Dados pessoais

As listas guardam nome, ORCID e afiliação dos autores, que são dados públicos das próprias bases e formam os nós das redes de coautoria. Eles ficam só na sua máquina, na pasta de dados, e não vão para nenhum outro lugar. Para apagar tudo, apague a pasta.

## Para quem desenvolve

```bash
git clone https://github.com/Erick-wilding675/RSL-MCP-APP.git
cd RSL-MCP-APP
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
```

A pasta [`docs/`](docs/) tem a descrição do sistema, os requisitos, a arquitetura, as decisões e uma spec por tarefa. Python 3.10 ou mais novo, SDK oficial do MCP (`mcp>=2,<3`).

## Licença

[MIT](LICENSE). Uso livre, sem fins comerciais por parte do projeto. Respeite os termos de uso de cada base consultada.
