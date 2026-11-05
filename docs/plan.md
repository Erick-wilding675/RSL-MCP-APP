# Plano

**Projeto:** RSL.app · **Versão:** 0.1 · **Data:** 2026-11-02

> **Em resumo:** Seis fases e 16 tarefas. A primeira fatia que funciona de ponta a ponta vem cedo (fase 2: busca no OpenAlex, lista, log e exportação em RIS que abre no VOSviewer), para o critério de aceite ficar verificável antes de gastar tempo com as outras fontes.
> Depois entram Crossref e Semantic Scholar, as referências e citações, o resto das chamadas e formatos, e a publicação no PyPI.
> O Gemini escreve o código de cada tarefa, o Claude Code revisa, corrige e orquestra com o Playmaker, e o Erick confirma cada entrega.

## Como o trabalho anda

- Uma tarefa por vez, na ordem abaixo. Duas tarefas sem dependência entre si (03-01 e 03-02) podem rodar em paralelo no Playmaker, em árvores de trabalho separadas.
- Cada tarefa é entregue com o jeito de testar: o que rodar ou abrir, e o que deve ser visto.
- Cada tarefa que lê uma API começa conferindo as páginas oficiais por inteiro (T-001). Os itens de conferência de cada spec estão na seção "Pronto quando".
- O código leva os identificadores FR-xx, NFR-xx, UC-xx e D-xxx como âncoras em comentários, para a revisão responder por que cada trecho existe.
- O Gemini escreve o código, o Claude Code revisa e marca a tarefa como "para testar", e o Erick marca como "pronta" depois de testar. Os testes que dependem de abrir o VOSviewer ou de chamar uma API com chave real são do Erick.
- O Claude (desktop ou Claude Code, é o mesmo papel) atualiza as specs quando estão erradas ou incompletas, registrando o motivo na própria spec. O Gemini não muda spec: registra e devolve. Desde 2026-11-03, o Erick liberou todas as fases e recebe um resumo ao fim de cada uma.
- O Langfuse, para observar os agentes do Gemini e do Claude Code, será configurado quando o Erick pedir.

## Fases

| Fase | O que entrega | Pronto quando |
|---|---|---|
| 1 · Esqueleto | Pacote instalável, configuração, servidor MCP que responde por stdio e armazenamento em arquivos | O servidor conecta a um cliente de teste, `list_sources` responde e os testes de armazenamento passam |
| 2 · Fatia completa | Busca no OpenAlex, lista salva, log legível e exportação em RIS | Uma busca real vira lista e log, e o RIS abre no VOSviewer sem edição manual |
| 3 · Mais fontes | Crossref e Semantic Scholar, deduplicação entre fontes, lista incompleta quando uma fonte falha | Uma busca consulta as três fontes e devolve uma lista sem duplicatas, com o estado de cada fonte |
| 4 · Referências e citações | Troca de ids por DOI e a ferramenta `get_related_works` | Referências e citações de um artigo viram uma lista própria, com teto e motivo no log |
| 5 · Resto das chamadas e formatos | `find_work`, `repeat_search`, `get_list`, `get_search_log`, CSV, JSON, DOIs, URL do OpenAlex e o prompt `plan_search` | As oito ferramentas e o prompt respondem como no contrato e os cinco formatos exportam |
| 6 · Publicação | Pacote no PyPI e guia de instalação | O guia, copiado, conecta o servidor ao Claude Desktop, e o critério de aceite do projeto passa |

## Tarefas

### 1 · Esqueleto

1. Pacote e configuração: pacote Python instalável e leitura da configuração (pastas e chaves) sem expor as chaves. Spec: `specs/01-01-pacote-e-configuracao.md`
2. Servidor MCP mínimo: servidor MCP por stdio com as instruções de conexão e a ferramenta `list_sources`. Spec: `specs/01-02-servidor-mcp-minimo.md`
3. Armazenamento em arquivos: gravação e leitura atômica de buscas, listas, log legível e cache com prazo. Spec: `specs/01-03-armazenamento.md`

### 2 · Fatia completa

1. Modelos e fonte OpenAlex: modelos do miolo, interface das fontes e conector do OpenAlex com autores completos, ids de referências e citações. Spec: `specs/02-01-modelos-e-fonte-openalex.md`
2. Busca, lista e log: busca no miolo, deduplicação na lista, estado completa ou incompleta, gravação e ferramenta `search_works`. Spec: `specs/02-02-busca-e-lista.md`
3. Exportação em RIS: exportador RIS e ferramenta `export_list`, com teste no VOSviewer. Spec: `specs/02-03-exportacao-ris.md`

### 3 · Mais fontes

1. Fonte Crossref: conector da Crossref. Spec: `specs/03-01-fonte-crossref.md`
2. Fonte Semantic Scholar: conector da Semantic Scholar. Spec: `specs/03-02-fonte-semantic-scholar.md`
3. Deduplicação entre fontes: junção das três fontes numa lista sem duplicatas, com fontes e ids por artigo. Spec: `specs/03-03-deduplicacao-entre-fontes.md`

### 4 · Referências e citações

1. Troca de ids de referências por DOI: troca de ids de referências por DOI, na exportação ou a pedido, com cache. Spec: `specs/04-01-referencias-ids-para-doi.md`
2. Referências e citações de um artigo: ferramenta `get_related_works` com teto e lista própria. Spec: `specs/04-02-trabalhos-relacionados.md`

### 5 · Resto das chamadas e formatos

1. Achar um artigo e repetir uma busca: ferramentas `find_work` e `repeat_search`. Spec: `specs/05-01-find-work-e-repeat-search.md`
2. Ver uma lista e ver o log: ferramentas `get_list` e `get_search_log`. Spec: `specs/05-02-get-list-e-get-search-log.md`
3. CSV, JSON, lista de DOIs e URL do OpenAlex: exportadores CSV, JSON completo, lista de DOIs e URL do OpenAlex. Spec: `specs/05-03-formatos-csv-json-dois-url.md`
4. Prompt de planejamento e instruções: prompt `plan_search` e instruções de conexão revisadas. Spec: `specs/05-04-prompt-e-instrucoes.md`
5. Ajustes do teste real: proteção do CSV contra fórmula, erro `empty_list` na exportação e total desconhecido da Semantic Scholar no log. Entrou em 2026-11-05, depois do teste real. Spec: `specs/05-05-ajustes-do-teste-real.md`

### 6 · Publicação

1. Publicação no PyPI e guia de instalação: pacote no PyPI e guia de instalação com `uvx`. Spec: `specs/06-01-publicacao-pypi-e-guia.md`

## O que depende de pessoas

- **Chave do OpenAlex:** o Erick cria uma chave gratuita e a ativa pelo link do e-mail (a chave só funciona depois disso). A tarefa 02-01 espera por isso para as chamadas reais.
- **Chave da Semantic Scholar:** opcional. Sem ela as buscas falham mais. Se o Erick quiser, pede uma chave gratuita antes da tarefa 03-02.
- **Testes no VOSviewer:** o Erick abre os arquivos nas tarefas 02-03, 05-03 e 06-01.
- **Conta no PyPI:** o Erick cria a conta e o token para a tarefa 06-01. O token nunca entra em arquivo do projeto.
- **LGPD (T-007):** o Erick consulta uma fonte jurídica. Não trava nenhuma tarefa de código, mas é bom antes de divulgar o projeto.
- **Langfuse:** quando o Erick pedir.
