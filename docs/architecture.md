# Arquitetura

**Projeto:** RSL.app · **Versão:** 0.1 · **Data:** 2026-11-02

> **Em resumo:** Um programa Python que o cliente MCP da pessoa inicia na máquina dela (`uvx`, via stdio) e que fala com OpenAlex, Crossref e Semantic Scholar.
> Tudo o que ele guarda são arquivos numa pasta de dados: uma busca, uma lista, um arquivo.
> O que precisa ser lembrado antes de mexer: o servidor só traduz chamadas, o miolo não conhece o MCP, e fontes e exportadores entram por interfaces pequenas, para acrescentar outras ferramentas sem reescrever.

## Visão geral

```
  Pesquisador ──fala com──> IA (cliente MCP)
                               │  stdio
                               ▼
                    ┌─────────────────────┐
                    │ servidor MCP        │  ferramentas, prompt, instruções
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │ miolo (core)        │  planeja a chamada, junta as fontes,
                    │                     │  tira duplicatas, marca incompleta
                    └──┬────────┬─────────┘
          fontes       │        │       exportadores
   ┌───────────────────┘        └───────────────────┐
   ▼                                                ▼
 OpenAlex · Crossref · Semantic Scholar       RIS · CSV · JSON · DOIs · URL OpenAlex
   (internet, com as chaves do usuário)

                    ┌─────────────────────┐
                    │ armazenamento       │  arquivos na pasta de dados:
                    │                     │  buscas, listas, log legível, cache
                    └─────────────────────┘
```

O servidor roda só na máquina de quem usa e só fala por stdio com o cliente MCP. Não abre porta nem depende de servidor do projeto (NFR-02). A pasta de dados é a memória do sistema: sem banco, cada coisa é um arquivo que a pessoa pode abrir, copiar ou apagar (D-007).

## As partes

| Parte | Onde roda | O que faz |
|---|---|---|
| Servidor MCP | Máquina do usuário, iniciado pelo cliente MCP | Expõe as nove ferramentas (desde a 1.2), o prompt `plan_search` e as instruções de conexão. Valida a entrada e devolve as respostas (`interface-contract.md`) |
| Miolo (core) | Mesmo processo | Orquestra uma busca: chama as fontes, tira duplicatas (FR-04), define se a lista é completa (FR-08), aplica o teto das listas relacionadas (D-010) |
| Fontes | Mesmo processo, chamam a internet | Um módulo por API (OpenAlex, Crossref, Semantic Scholar). Cada um monta a consulta, respeita o limite da API, tenta de novo e devolve artigos no formato comum, com o estado da fonte |
| Exportadores | Mesmo processo | Um módulo por formato (RIS, CSV, JSON, lista de DOIs, URL do OpenAlex). Outra ferramenta de revisão entra como mais um módulo |
| Armazenamento | Mesmo processo, grava na pasta de dados | Grava buscas, listas, log legível e cache. Toda gravação é atômica (ver Dados) |
| Configuração | Variáveis de ambiente e arquivo local | Pasta de dados, pasta de exportação, chaves de API (FR-07, NFR-03) |

## Como o código é organizado

```
rsl-app/
├── pyproject.toml          # pacote publicado no PyPI, comando de entrada, dependências
├── src/rslapp/
│   ├── server.py           # MCP: ferramentas, prompt, instruções. Só traduz chamadas
│   ├── config.py           # lê pastas e chaves; nunca devolve chaves
│   ├── core/               # busca, deduplicação, estado da lista, teto das relacionadas, modelos (Artigo, Autor, Lista, Busca)
│   ├── sources/            # base.py (interface), openalex.py, crossref.py, semantic_scholar.py
│   ├── exporters/          # base.py (interface), ris.py, csv.py, json.py, dois.py, openalex_url.py
│   └── store/              # listas, buscas, log legível, cache; gravação atômica
├── tests/                  # um conjunto por pasta de src/, com fontes simuladas
├── docs/                   # documentos do Blueprint
└── .blueprint/             # estado e diário do Blueprint
```

A regra que organiza tudo: a dependência só desce. O servidor chama o miolo, o miolo chama fontes, exportadores e armazenamento, e ninguém acima conhece quem está abaixo além da interface. Por isso o miolo não importa nada do MCP, e dá para testar uma busca inteira sem cliente, com fontes simuladas.

## Dados

| O que é guardado | O que contém | Dados pessoais |
|---|---|---|
| `searches/s-NNNN.json` | Uma busca do log: pedido, strings por fonte, estado de cada fonte, contagens, lista gerada, `repetida_de` e artigo de origem. É a fonte de verdade do log | Sim: texto livre do pedido |
| `lists/l-NNNN.json` | Uma lista imutável, com os artigos completos (autores, referências, citações) | Sim: nome, ORCID, identificadores e afiliações dos autores |
| `log.md` | O log legível por pessoas, acrescentado a cada busca. Pode ser refeito a partir de `searches/` | Sim: o mesmo texto do pedido |
| `cache/<fonte>/<chave>.json` | A resposta de uma API a uma consulta, com data de obtenção e de expiração. A chave não inclui a chave de API | Sim: o que a API devolveu sobre os autores |
| Pasta de exportação (configurável) | Os arquivos exportados | Sim: os mesmos dados da lista |

Regras que o armazenamento cumpre, decididas por mim por serem baratas de mudar:
- **Gravação atômica:** escreve num arquivo temporário e renomeia, para nunca ficar um arquivo pela metade.
- **Ordem de gravação de uma busca:** primeiro a lista, depois a busca em `searches/`, por último a linha em `log.md`. Se algo falhar no meio, `log.md` é refeito a partir de `searches/`.
- **Identificadores:** `s-NNNN` e `l-NNNN`, em sequência, como no contrato.
- **Nada apaga nem reescreve** busca, lista ou entrada de log depois de gravada (FR-05, FR-09).

O prazo de expiração do cache, o formato exato de `log.md` e os campos de cada JSON vão para o spec da tarefa do armazenamento.

## Fluxos principais

### Buscar por tema (`search_works`)

1. A IA chama `search_works` com os termos, depois de planejar com o prompt `plan_search` (FR-10).
2. O servidor valida a entrada e passa ao miolo.
3. O miolo pede a cada fonte configurada, em paralelo, respeitando o limite de cada uma. Antes de chamar a API, olha o cache.
4. Cada fonte devolve artigos no formato comum, com o estado (`ok`, `failed`, `rate_limited`, `missing_key`). No OpenAlex, as referências vêm no próprio registro como ids, sem chamada extra (D-010).
5. O miolo tira as duplicatas (DOI, senão título normalizado) e define se a lista é completa ou incompleta.
6. O armazenamento grava a lista, a busca e a linha do log.
7. A resposta volta à IA em resumo, com o estado de cada fonte.

### Referências ou citações de um artigo (`get_related_works`)

1. A IA informa o artigo (DOI ou id) e a direção.
2. O miolo consulta só as fontes que entregam aquele dado (`not_supported` nas outras) até o teto (padrão de 1.000 trabalhos, ajustável) ou o limite da fonte (10 mil na consulta de citações da Semantic Scholar).
3. Se o teto ou o limite cortou, a lista sai incompleta, com o motivo no log.
4. A lista nova fica ligada ao artigo de origem na busca.

### Exportar (`export_list`)

1. O servidor lê a lista salva.
2. O exportador do formato pedido monta o arquivo. Se o formato precisa de DOI nas referências, o miolo troca os ids por DOI nesse momento, e isso pode gastar cota (T-005).
3. O arquivo é gravado na pasta de exportação e o caminho volta à IA.

### Repetir uma busca (`repeat_search`)

1. O servidor lê a busca em `searches/`.
2. Roda de novo com as mesmas strings e as mesmas fontes, como uma busca nova, com `repetida_de` apontando para a original.

## Segurança e privacidade

- **Chaves:** ficam nas variáveis de ambiente da configuração do cliente MCP ou num arquivo local do usuário. Nunca entram no log, nas listas, no cache nem nas respostas à IA (NFR-03).
- **Rede:** o servidor só faz chamadas de saída para as três APIs. Não escuta porta nenhuma.
- **Texto de terceiros:** títulos e resumos vêm das APIs e vão para a IA como dados. Podem conter texto que parece instrução. A instrução do servidor diz à IA para tratar esse conteúdo como dado, e isso reduz o risco sem eliminá-lo.
- **Dados pessoais:** nomes, ORCID e afiliações de autores ficam só na pasta de dados da máquina do usuário. Ver `data-classification.md`.
- **Limites das APIs:** o servidor espera e tenta de novo com recuo crescente em 429 e 500 (NFR-04). A Semantic Scholar é chamada uma por vez.

## Pilha e custo

- **Linguagem:** Python 3.10 ou mais (D-001). **Servidor MCP:** SDK oficial `mcp>=2,<3` (D-006). **Instalação:** pacote no PyPI, rodado com `uvx` (D-008).
- **Escolhas pequenas, de fácil troca:** `httpx` como cliente HTTP, `pytest` para testes, `ruff` para formatação e verificação.
- **Custo:** zero de hospedagem, porque roda na máquina do usuário. O único gasto possível é o crédito da API do OpenAlex: US$ 1 por dia com a chave gratuita e US$ 0,10 sem chave (NFR-01, NFR-05).

## Decisões por trás

- D-001 · Linguagem do projeto: Python
- D-002 · Chamadas do servidor MCP
- D-003 · A busca roda direto, sem etapa de aprovação
- D-004 · Todos os dados dos autores entram
- D-005 · Referências e citações entram na primeira versão
- D-006 · Biblioteca do servidor MCP: SDK oficial `mcp` 2.x
- D-007 · Armazenamento: só arquivos
- D-008 · Instalação: PyPI com `uvx`
- D-009 · Núcleo escrito do zero, com os MCPs existentes como referência
- D-010 · Referências no registro, citações sob demanda, com teto

## Pontos em aberto

| Nº | Ponto | Depende de |
|---|---|---|
| 1 | Prazo de expiração do cache, formato do `log.md` e campos de cada JSON | Spec do armazenamento |
| 2 | Tempo máximo que o cliente MCP espera por uma resposta, para buscas longas | T-006 |
| 3 | Custo real de referências e citações e a troca de ids por DOI | T-005 |
| 4 | Como publicar o pacote no PyPI e definir o comando de entrada | Documentação do uv e do PyPI |
| 5 | O que reaproveitar do código dos MCPs existentes | T-010 |
