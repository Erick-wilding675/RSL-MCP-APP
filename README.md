# RSL.app

**Servidor MCP gratuito para revisão sistemática de literatura.** Você pede à sua IA, em linguagem natural, os artigos de um tema. Ela busca no OpenAlex, na Crossref e na Semantic Scholar (e, em temas de saúde e biologia, também no PubMed e no Europe PMC), junta os resultados sem duplicatas e grava um arquivo pronto para abrir no [VOSviewer](https://www.vosviewer.com/), com autores, afiliações, palavras-chave, referências e citações.

> Exemplo: *"Quero os artigos sobre burnout em professores da educação básica e, separado, sobre inteligência artificial na correção de redações. Exporte cada um em RIS."*
> A IA faz duas buscas, monta duas listas e entrega dois arquivos `.ris`. Cada busca fica registrada num log legível, que você pode anexar à metodologia do seu artigo.

O RSL.app roda **na sua máquina** (self-hosted), com as **suas** chaves gratuitas. Ele não tem servidor central, não cobra nada e não manda seus dados para lugar nenhum além das próprias bases consultadas.

## O que ele faz

- **Busca por tema, palavra-chave, subtema ou título** nas três bases abertas, ao mesmo tempo. Em temas de saúde, medicina e biologia, a IA pode pedir também o **PubMed** e o **Europe PMC** (desde a 1.2).
- **Usa o Scopus e o Web of Science com as suas chaves** (desde a 1.3), se você ou a sua instituição tiverem acesso. Veja "Bases pagas", abaixo.
- **Deixa de fora os pareceres de revisão** (desde a 1.3): pareceres, cartas de decisão e respostas de autores que algumas bases trazem como se fossem artigos. Quem estuda a revisão por pares pode pedir para incluí-los.
- **Tira as duplicatas.** O mesmo artigo vindo de mais de uma base aparece uma vez só, com os ids de cada base.
- **Avisa quando a lista está incompleta.** Se uma base falha ou um limite corta a busca, a lista sai marcada como incompleta, com o motivo. Nenhuma lista incompleta passa por completa.
- **Acha um artigo específico** pelo título ou pelo DOI.
- **Traz as referências de um artigo e quem o cita**, como uma lista própria.
- **Registra cada busca num log** (`log.md`): o pedido, a string enviada a cada base, a data, quantos artigos cada base achou e se veio do cache.
- **Repete uma busca do log** com as mesmas strings, para atualizar uma revisão.
- **Junta listas do mesmo assunto** (desde a 1.2): várias strings sobre um tema viram uma lista só, sem duplicatas, e a junção entra no log.
- **Exporta em seis formatos:** RIS, CSV no padrão do Scopus, JSON completo, lista de DOIs, URL de consulta do OpenAlex e BibTeX (desde a 1.2). O RIS, o CSV e a lista de DOIs abrem no VOSviewer sem edição; o BibTeX abre no Zotero, no Mendeley e no JabRef.
- **Guarda tudo na sua máquina:** listas, log, exportações e um cache das respostas, que expira em 7 dias e economiza sua cota.

Ele **não** baixa texto completo de artigos e não abre o VOSviewer sozinho. Cada pedido vira a sua própria lista; só listas do mesmo assunto devem ser juntadas.

## Do que você precisa

1. **Uma IA que fale MCP**, como o Claude Desktop, o Claude Code ou outro cliente compatível.
2. **O [uv](https://docs.astral.sh/uv/getting-started/installation/)** instalado. É ele que baixa e roda o RSL.app; você não precisa instalar o Python à mão.
3. **Uma chave gratuita do OpenAlex**, obrigatória. Crie em [openalex.org/settings/api](https://openalex.org/settings/api) e **ative pelo link que chega no e-mail**: a chave só funciona depois disso. Ela dá 10.000 créditos por dia, e uma busca gasta cerca de 10.
4. **Opcional: uma chave gratuita da [Semantic Scholar](https://www.semanticscholar.org/product/api#api-key-form).** Sem ela a Semantic Scholar funciona, mas recusa pedidos com mais frequência.

A Crossref e o Europe PMC não precisam de chave. O PubMed funciona sem chave; com uma chave gratuita do NCBI (`NCBI_API_KEY`), aceita mais pedidos por segundo.

## Bases pagas: Scopus e Web of Science

**O RSL.app não dá acesso a bases pagas.** O Scopus e o Web of Science só funcionam com as chaves e a assinatura do próprio pesquisador ou da instituição dele. O RSL.app usa a sua conta, do mesmo jeito que usa a sua chave do OpenAlex. Elas só funcionam no RSL.app instalado no seu computador: o servidor hospedado não as oferece, porque os termos das duas bases proíbem servir os dados a quem é de fora da instituição.

**Scopus (Elsevier):**
1. Crie uma chave gratuita em [dev.elsevier.com](https://dev.elsevier.com/), em "My API Key", com o e-mail da instituição. Ponha em `SCOPUS_API_KEY`.
2. A chave sozinha não traz dados. A Elsevier confere a assinatura pelo IP: rode as buscas **na rede da instituição** ou na VPN dela. O login pela CAFe, no Portal de Periódicos da CAPES, vale para o site do Scopus, mas a API não o usa.
3. Fora da rede, só com um token institucional, que a biblioteca pede à Elsevier. Ponha em `SCOPUS_INSTTOKEN`.
4. Sem acesso completo, o RSL.app tenta a visão reduzida (só o primeiro autor, sem resumo) e avisa. Sem acesso nenhum, diz para conferir a rede ou o token.

**Web of Science (Clarivate):**
1. Peça uma chave da Starter API em [developer.clarivate.com](https://developer.clarivate.com/apis/wos-starter) e ponha em `WOS_STARTER_API_KEY`. O plano de teste é aberto a qualquer um, mas dá só **50 pedidos por dia** e não traz o número de citações. O plano de membro, para quem é de instituição assinante, dá 5.000 por dia, com citações.
2. A Starter API não traz resumo, afiliações nem referências. Para mapas de coautoria por instituição ou de cocitação, use as bases abertas ou o Scopus.

**O que os termos pedem de você:**
- use os dados na sua própria pesquisa e cite a base como fonte (o log do RSL.app já faz o crédito);
- não repasse as listas a quem é de fora da sua instituição;
- pelos termos gerais da Clarivate, o conteúdo baixado do Web of Science só pode ser guardado por 3 meses, a não ser que a instituição tenha licença de arquivo.

O contrato da sua instituição vale mais do que este resumo.

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

4. Salve e abra o Claude Desktop de novo. O `rslapp` aparece na lista de ferramentas, com nove ferramentas.
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
| `.bib` | Não abre no VOSviewer: importe no Zotero (*Arquivo → Importar*), no Mendeley ou no JabRef |

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
| `NCBI_API_KEY` | Chave do NCBI para o PubMed (opcional) | - |
| `SCOPUS_API_KEY` | Sua chave do Scopus (só com acesso da instituição) | - |
| `SCOPUS_INSTTOKEN` | Token institucional do Scopus, para buscar fora da rede da instituição (opcional) | - |
| `WOS_STARTER_API_KEY` | Sua chave da Web of Science Starter API | - |
| `RSL_CONTACT_EMAIL` | Seu e-mail, enviado à Crossref, ao NCBI e ao Europe PMC, que atendem melhor quem se identifica (opcional) | - |
| `RSL_DATA_DIR` | Onde guardar listas, log e cache | `~/RSL.app` |
| `RSL_EXPORT_DIR` | Onde gravar as exportações | `<RSL_DATA_DIR>/exports` |
| `RSL_CACHE_DAYS` | Por quantos dias o cache vale | `7` |

## As ferramentas que a IA recebe

| Ferramenta | O que faz |
|---|---|
| `search_works` | Busca por termos nas três bases (e no PubMed, no Europe PMC, no Scopus e no Web of Science, quando pedidos) e cria uma lista, sem os pareceres de revisão (a não ser que se peça `include_peer_review`) |
| `find_work` | Acha um artigo específico por título ou DOI |
| `get_related_works` | Traz as referências ou as citações de um artigo, até um teto por base (padrão 1.000) |
| `repeat_search` | Repete uma busca do log |
| `get_list` | Mostra uma lista salva, por páginas |
| `get_search_log` | Mostra o log e o caminho do `log.md` |
| `merge_lists` | Junta listas do mesmo assunto numa lista nova, sem duplicatas |
| `export_list` | Grava a lista em `ris`, `csv`, `json`, `dois`, `openalex_url` ou `bibtex` |
| `list_sources` | Diz quais das cinco bases estão prontas |
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
