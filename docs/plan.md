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

### 7 · Manutenção depois da v1

1. Entradas numéricas sem verdadeiro/falso: as seis entradas inteiras das ferramentas recusam `true` e `false`. Publicada na 1.0.1. Spec: `specs/07-01-inteiros-sem-booleano.md`

### 8 · Uso por link (v2)

Decidida com o Erick em 2026-11-10 (D-011 a D-018). Um servidor hospedado por quem quiser, com login OAuth por código pessoal, dados separados por pessoa, exportação por link temporário e uma imagem Docker com HTTPS pelo Caddy. O modo stdio continua o padrão e não muda. Pronto quando: o Erick sobe o compose num domínio, adiciona o link como conector no Claude, entra com o código dele, faz uma busca e baixa o RIS pelo link, e outra pessoa, com outro código, não vê as listas dele.

1. Modo HTTP: comando `rslapp serve`, que serve as mesmas ferramentas por HTTP, com host, porta e URL pública configuráveis. Spec: `specs/08-01-modo-http.md`
2. Pessoas e códigos: comandos `rslapp token add`, `token list`, `token revoke` e `user purge`, com só o hash do código guardado. Spec: `specs/08-02-pessoas-e-codigos.md`
3. Login OAuth: servidor de autorização no mesmo processo, com registro automático de clientes, tela de login pelo código pessoal, tokens renovados sem prazo e revogação. Spec: `specs/08-03-login-oauth.md`
4. Dados separados por pessoa: cada pessoa logada tem as próprias listas, log e exportações; o cache das APIs é compartilhado. Spec: `specs/08-04-dados-por-pessoa.md`
5. Exportação por link temporário: no modo HTTP, `export_list` devolve um link de download assinado que vale 1 hora. Spec: `specs/08-05-exportacao-por-link.md`
6. Docker, Caddy e guia de hospedagem: Dockerfile, docker-compose com Caddy, imagem no ghcr.io a cada tag e guia em português com o aviso da LGPD. Spec: `specs/08-06-docker-e-guia.md`
7. Publicação da 1.1.0 e teste real: versão no PyPI e no ghcr.io, e o teste de ponta a ponta do Erick num conector do Claude. Spec: `specs/08-07-publicacao-e-teste-real.md`

**Fase 8 pronta em 2026-11-11:** `rslapp` 1.1.0 no PyPI e no ghcr.io, e o teste real do Erick passou em `rsl.sinteselabs.com` (D-019).

As tarefas andam nessa ordem: cada uma usa a anterior. A 08-02 não depende da 08-01 e pode rodar em paralelo com ela. Antes de anunciar o modo hospedado, a LGPD (T-007) precisa ser conferida (D-018).

### 9 · Versão 1.2: mais bases, BibTeX, juntar listas e polimento

Decidida com o Erick em 2026-11-11 (D-020 e D-021). Pronto quando: uma busca de saúde traz PubMed e Europe PMC sem duplicatas, a lista sai em BibTeX e abre no Zotero, duas buscas do mesmo assunto viram uma lista com `merge_lists`, e o log baixa por link no servidor hospedado.

1. Fonte PubMed: conector das E-utilities do NCBI, com chave opcional. Spec: `specs/09-01-fonte-pubmed.md`
2. Fonte Europe PMC: conector da API REST do Europe PMC. Spec: `specs/09-02-fonte-europe-pmc.md`
3. PubMed e Europe PMC no servidor: nomes novos em `sources`, `list_sources`, deduplicação, CSV e orientação à IA. Spec: `specs/09-03-fontes-novas-no-servidor.md`
4. Exportação em BibTeX: formato `bibtex` em `export_list`. Spec: `specs/09-04-exportacao-bibtex.md`
5. Juntar listas: ferramenta `merge_lists`. Spec: `specs/09-05-juntar-listas.md`
6. Polimento do modo hospedado: proteção de domínio em todas as rotas, link de download do log, limpeza das exportações, Actions atualizadas. Spec: `specs/09-06-polimento-do-modo-hospedado.md`
7. Publicação da 1.2.0 e teste real. Spec: `specs/09-07-publicacao-1-2-e-teste-real.md`

A 09-01, a 09-02 e a 09-06 não dependem uma da outra e rodam em paralelo. A 09-03 espera a 09-01 e a 09-02. A 09-04 e a 09-05 mexem em `server.py`, como a 09-06 e a 09-03, e por isso entram uma de cada vez nesse arquivo.

**Fase 9 pronta em 2026-11-11:** `rslapp` 1.2.0 no PyPI e no ghcr.io. O Erick conferiu o BibTeX no Zotero, a lista juntada no VOSviewer e a busca no Claude Desktop.

### 10 · Bases pagas e filtros (1.3)

Primeira leva da 2.0, decidida com o Erick em 2026-11-11 (D-022, D-023). O Scopus e o Web of Science só funcionam com as chaves e o acesso de quem usa, e só no RSL.app instalado no computador.

1. Pareceres de revisão fora da busca, com opção para incluir. Spec: `specs/10-01-pareceres-fora-da-busca.md`
2. Fonte Scopus (Scopus Search API, visão COMPLETE). Spec: `specs/10-02-fonte-scopus.md`
3. Fonte Web of Science (Starter API). Spec: `specs/10-03-fonte-web-of-science.md`
4. Scopus e Web of Science no servidor: nomes, `list_sources`, recusa no modo hospedado, deduplicação, CSV e crédito no log. Spec: `specs/10-04-bases-pagas-no-servidor.md`
5. Publicação da 1.3.0 e teste real (pronta em 2026-11-14; falta só o teste do Web of Science, quando a chave sair). Spec: `specs/10-05-publicacao-1-3-e-teste-real.md`
6. String das bases pagas no log, achado do teste real da 10-05 (2026-11-13). Spec: `specs/10-06-string-das-bases-pagas-no-log.md`. Entra antes da publicação da 1.3.0.

A 10-01, a 10-02 e a 10-03 não dependem uma da outra e rodam em paralelo. A 10-02 e a 10-03 mexem em `config.py` só para acrescentar uma linha cada. A 10-04 espera as três.

### 11 · App desktop (2.0)

Decidido em 2026-11-14 (D-024 a D-026): NiceGUI em janela própria, quatro telas, extra `rslapp[desktop]` e executáveis para Windows e Linux. Requisitos FR-16 a FR-18.

1. Base do app: extra, configuração das chaves, serviço sobre o núcleo, janela com navegação e comando `rslapp-desktop`. Spec: `specs/11-01-base-do-app-desktop.md`
2. Telas Buscar e Lista. Spec: `specs/11-02-telas-buscar-e-lista.md`
3. Telas Histórico e Configurações. Spec: `specs/11-03-telas-historico-e-configuracoes.md`
4. Executáveis para Windows e Linux e o README do app. Spec: `specs/11-04-executaveis-do-app.md`
5. Publicação da 2.0.0 e teste real. Spec: `specs/11-05-publicacao-2-0-e-teste-real.md`

A 11-02 e a 11-03 dependem da 11-01 e mexem em arquivos diferentes (uma página cada). A 11-04 espera as três. A 11-05 espera o ok do Erick para publicar.

### 12 · Conectar a IA ao app, e o guia das instituições (2.1)

Decidido em 2026-11-15 (D-027 a D-029): sem servidor do projeto; o executável do app serve como servidor MCP local, e uma tela liga cada IA a ele; as instituições são o público principal, e cada recurso explica como uma instituição o oferece. Requisitos FR-19 e FR-20.

1. Modo servidor MCP no executável do app. Spec: `specs/12-01-modo-mcp-no-executavel.md`
2. Tela "Conectar IA". Spec: `specs/12-02-tela-conectar-ia.md`
3. Guia das instituições, com o ChatGPT pelo servidor da instituição. Spec: `specs/12-03-guia-das-instituicoes.md`
4. Publicação da 2.1.0 e teste real. Spec: `specs/12-04-publicacao-2-1-e-teste-real.md`
5. Correções da revisão geral (compose, `RSL_CACHE_DAYS` vazio, ferramentas só de leitura). Spec: `specs/12-05-correcoes-da-revisao.md`
6. Janela do app no Windows quando o zip vem do navegador (defeito da 2.0.0 achado no teste do Erick). Spec: `specs/12-06-janela-com-arquivo-baixado.md`

A 12-02 depende da 12-01. A 12-03 é só documento e teste no servidor de teste, então anda em paralelo com as duas. A 12-05 vem depois da 12-02. A 12-04 espera as outras cinco e o ok do Erick para publicar.

### 13 · 2.2: visual novo e ganhos rápidos

Decidido em 2026-11-16 (D-030, D-031): o rumo é o de `docs/ideias-proximas-versoes.md`, e a 2.2 começa pelo visual do app, pedido pelo Erick no teste.

1. Visual novo: casca, tema e tela Buscar. Spec: `specs/13-01-visual-casca-tema-e-buscar.md`
2. Visual novo: Lista e Histórico. Spec: `specs/13-02-visual-lista-e-historico.md`
3. Visual novo: Configurações e Conectar IA. Spec: `specs/13-03-visual-configuracoes-e-conectar.md`
4. Verificador de referências contra alucinação (ideia 5.1). Spec a escrever, depois de ler as páginas oficiais do Crossref e do OpenAlex.
5. Retratações nas listas (ideia 5.2). Spec a escrever, depois de ler como o Crossref publica os dados do Retraction Watch.
6. Importar exportações de fora: RIS, BibTeX e os formatos do Scopus e da Web of Science (ideia 7). Spec: `specs/13-06-importar-exportacoes.md`
7. Referências na ABNT (ideia 4.3). Spec: `specs/13-07-referencias-na-abnt.md`
8. Publicação da 2.2.0. Spec: `specs/13-08-publicacao-2-2-e-teste-real.md`

**Fase 13 pronta em 2026-11-16:** `rslapp` 2.2.0 no PyPI e no ghcr.io, release `v2.2.0` no GitHub com executáveis Windows e Linux.

### 14 · Versão 2.3: Academia Brasileira

Decidido em 2026-11-16 (D-030, D-035): integração da BDTD para literatura cinzenta nacional (teses e dissertações), prompts de planejamento metodológico por tipo de revisão e nova tela de Roteiros Metodológicos.

1. Fonte BDTD: conector da Biblioteca Digital Brasileira de Teses e Dissertações via API REST VuFind (`https://bdtd.ibict.br/vufind/api/v1/search`), mapeamento de campos (título, autores, orientadores, resumo, instituição, datas, DOIs/URLs) e modelo com tipo `thesis` ou `dissertation`. Spec: `specs/14-01-fonte-bdtd.md`
2. BDTD no servidor MCP e deduplicação: adicionar `bdtd` nas fontes suportadas, `list_sources`, busca unificada, deduplicação por título/ano/autor e orientações à IA sobre literatura cinzenta nacional. Spec: `specs/14-02-bdtd-no-servidor-mcp.md`
3. Roteiros e Prompts para Tipos de Revisão: prompts MCP especializados (`plan_scoping_review` com PCC, `plan_integrative_review` com Whittemore/Mendes, `plan_systematic_review` com PICO/PRISMA e `plan_bibliometric_study`). Spec: `specs/14-03-prompts-roteiros-revisao.md`
4. Interface Desktop: BDTD na busca, selos de teses e dissertações, e tela de Roteiros Metodológicos (`/roteiros`) guiando a escolha e os critérios do estudo. Spec: `specs/14-04-desktop-bdtd-e-roteiros.md`
5. Publicação da 2.3.0 e teste real. Spec: `specs/14-05-publicacao-2-3-e-teste-real.md`

A 14-01 e a 14-03 são independentes e podem andar em paralelo. A 14-02 espera a 14-01. A 14-04 espera a 14-02 e a 14-03. A 14-05 fecha a fase e espera o ok do Erick.

**Fase 14 pronta em 2026-11-17:** tarefas 14-01 a 14-05 concluídas, 761 testes do núcleo e 60 testes do desktop passando, pacote 2.3.0 publicado no PyPI e release GitHub `v2.3.0`.

### 15 · Versão 2.4: Triagem com Rastro e Fluxograma PRISMA 2020

Decidido em 2026-11-18 (D-030, D-036 a D-038): suporte à etapa de seleção e triagem de artigos (título/resumo e texto completo) com registro de autoria da decisão (humano vs. IA), cálculo automático do fluxograma PRISMA 2020 e checklist PRISMA-S com números reais, e gerador de declaração de uso ético e metodológico de IA (padrão COPE/ICMJE/SciELO).

1. Triagem no Núcleo e Store: modelo de dados de decisão (`included`, `excluded`, `maybe`), motivos de exclusão, autoria (`human` ou `ai`, com modelo/pessoa), carimbo de data/hora e métodos no `Store` para persistência junto à lista. Spec: `specs/15-01-triagem-no-nucleo-e-store.md`
2. Módulo PRISMA 2020 e Declaração de Uso de IA: cálculo exato das caixas do fluxograma oficial a partir dos números reais de identificação, deduplicação e triagem; gerador de SVG vetorial do fluxograma e gerador da declaração metodológica de IA em português e inglês. Spec: `specs/15-02-modulo-prisma-e-declaracao-ia.md`
3. Ferramentas MCP de Triagem e PRISMA: novas ferramentas MCP `screen_work` (registro de decisão e justificativa com rastro), `get_screening_status` (resumo quantitativo e motivos), `get_prisma_flow` (dados estruturados do PRISMA) e `get_ai_disclosure` (declaração pronta). Spec: `specs/15-03-ferramentas-mcp-triagem-e-prisma.md`
4. Interface Desktop: Telas de Triagem e Fluxograma PRISMA: botões de ação na tela Lista (`/lista/{list_id}`), tela de triagem rápida focada (`/triagem/{list_id}`) com atalhos de teclado e seleção de motivos, e tela do fluxograma PRISMA (`/prisma/{list_id}`) com diagrama visual e exportação em SVG. Spec: `specs/15-04-desktop-triagem-e-prisma.md`
5. Publicação da 2.4.0 e teste real. Spec: `specs/15-05-publicacao-2-4-e-teste-real.md`

A 15-01 é o alicerce das outras. A 15-02 e a 15-03 dependem da 15-01 e podem andar em paralelo. A 15-04 integra tudo na interface desktop. A 15-05 fecha a fase e espera o ok do Erick.

**Fase 15 pronta em 2026-11-18:** tarefas 15-01 a 15-05 concluídas, 780 testes do núcleo e 65 testes do desktop passando, pacote 2.4.0 construído e interface refinada.

### 16 · Versão 2.5: Pacote de Reprodutibilidade Científica com Manifesto SHA-256

Decidido em 2026-11-18 (D-030, D-039): exportação em `.zip` autocontido com os 11 arquivos da revisão (metadados brutos, busca, triagem, fluxograma PRISMA, declaração de IA e exportações) e manifesto de integridade criptográfica `checksums.sha256` para depósito no Zenodo, OSF e repositórios institucionais (FR-28).

1. Pacote de Reprodutibilidade no Núcleo, MCP e Desktop: módulo `rslapp.core.reproducibility`, ferramenta MCP `export_reproducibility_package` e botões de download na interface desktop. Spec: `specs/16-01-pacote-reprodutibilidade.md`
2. Publicação da 2.5.0 e teste real. Spec: `specs/16-02-publicacao-2-5-e-teste-real.md`

**Fase 16 pronta em 2026-11-18:** tarefas 16-01 e 16-02 concluídas, 785 testes do núcleo e 65 testes do desktop passando, pacote 2.5.0 construído, tag `v2.5.0` enviada.

### 17 · Versão 2.6: Fichamento Científico Estruturado com Marcação de IA

Decidido em 2026-11-18 (D-030, D-040): suporte a fichamento científico analítico com campos padronizados (objetivo, método, amostra, resultados, limitações, citações diretas com página, palavras-chave e síntese crítica), distinção explícita de autoria (`ai_suggested` vs. `human_reviewed`), exportação Markdown para Obsidian e ferramentas MCP dedicadas (FR-29).

1. Fichamento no Núcleo, Armazenamento e Exportação Markdown: modelo `WorkNote`, persistência em `notes/{list_id}/{work_id}.json`, exportador Markdown com frontmatter e integração ao Pacote de Reprodutibilidade. Spec: `specs/17-01-fichamento-cientifico.md`
2. Interface Desktop e Ferramentas MCP: ferramentas `save_work_note`, `get_work_note`, `list_work_notes`, `export_notes_markdown`, tela/diálogo de fichamento no app desktop e badges informativos na tela Lista. Spec: `specs/17-02-desktop-fichamento-e-mcp.md`
3. Publicação da 2.6.0 e teste real. Spec: `specs/17-03-publicacao-2-6-e-teste-real.md`

### Depois da 1.2: a versão maior (2.0)

O Erick quer as três frentes grandes na próxima versão maior (2026-11-11). Cada uma pede uma decisão dele antes da spec, porque mexe com pilha, licença ou custo. A primeira, Scopus e Web of Science, virou a fase 10 (D-023):

- **App desktop** para Windows e Linux, com busca e lista sem IA no meio: virou a fase 11 (D-024 a D-026).
- **Scopus e Web of Science** com a chave de cada pessoa. Falta ler os termos de uso de cada API e decidir como a chave é guardada.
- ~~**Servidor mantido pelo projeto** (opções A e B da D-011)~~: fora do plano desde a D-027 (2026-11-15). No lugar, a 2.1 deixa fácil ligar a IA do pesquisador ao RSL.app local.

## Próximos passos (depois da v1)

A v1 (fases 1 a 6) foi publicada em 2026-11-05 como `rslapp` 1.0.0 no PyPI. O que vem depois:

1. **Uso por link, opção C (D-011):** virou a fase 8, acima. Um servidor mantido pelo projeto (opções A e B da D-011) fica para depois, com pesquisa de hospedagem.
2. **Entradas numéricas sem verdadeiro/falso:** feita na fase 7 e publicada na 1.0.1.
3. **Do escopo combinado para depois** (`system-description.md`): app desktop para Windows e Linux; Scopus e Web of Science com a chave de cada usuário; PubMed e Europe PMC; Periódicos CAPES via CAFe; texto completo de acesso aberto; exportação para outras ferramentas além do VOSviewer.
4. **Observabilidade:** Langfuse, quando o Erick pedir.

## O que depende de pessoas

- **Chave do OpenAlex:** o Erick cria uma chave gratuita e a ativa pelo link do e-mail (a chave só funciona depois disso). A tarefa 02-01 espera por isso para as chamadas reais.
- **Chave da Semantic Scholar:** opcional. Sem ela as buscas falham mais. Se o Erick quiser, pede uma chave gratuita antes da tarefa 03-02.
- **Testes no VOSviewer:** o Erick abre os arquivos nas tarefas 02-03, 05-03 e 06-01.
- **Conta no PyPI:** o Erick cria a conta e o token para a tarefa 06-01. O token nunca entra em arquivo do projeto.
- **LGPD (T-007):** o Erick consulta uma fonte jurídica. Não trava nenhuma tarefa de código, mas é bom antes de divulgar o projeto.
- **Langfuse:** quando o Erick pedir.
