---
blueprint_state: 1
project: RSL.app
starting_point: start
document_language: pt-BR
developers: 1
documents_at: docs/
tasks_at: docs/specs/
memory: Lore
observability: journal
updated: 2026-11-14T17:00:00Z
updated_by: Claude Code
---

# Project state

## Project kind

| Fact | Value | Known how |
|---|---|---|
| has-screens | no | deduced |
| stores-data | yes | deduced |
| holds-personal-data | yes | deduced |
| used-by-command-or-code | yes | said |
| calls-a-model | no | deduced |

Deduced: servidor MCP em Python, self-hosted, que consulta APIs acadêmicas e exporta listas; a primeira versão não tem telas (o app desktop entra depois) e guarda listas, log e cache. Guarda dados pessoais públicos dos autores (nome, ORCID, afiliações) por decisão do Erick (D-004); a lei não foi conferida (T-007).

## Criteria the person declared

- Sem fins comerciais e gratuito para quem usa.
- Self-hosted: cada pessoa roda e configura o próprio servidor.
- Tudo em Python.
- Um desenvolvedor, trabalhando com agentes: o Claude desktop escreve docs e specs, o Gemini escreve o código, o Claude Code revisa, corrige e orquestra com o plugin Playmaker.
- Memória do projeto no Lore (workspace erick-mendes, projeto RSL.app). Langfuse para observabilidade dos agentes do Gemini e do Claude Code, a configurar depois.
- Primeira versão enxuta: só o servidor MCP e as três fontes abertas (OpenAlex, Crossref, Semantic Scholar).
- Sem prazo definido.
- Uma lista separada por pedido: nada de juntar buscas diferentes. A IA planeja e divide antes de buscar, e devolve cada lista separada.
- Uso esperado baixo: talvez uma centena por semana.
- O servidor entrega o arquivo ou a URL prontos para o VOSviewer, sem abrir o programa. Deduplicação e log das buscas já na primeira versão.
- A busca roda direto, sempre, sem etapa de aprovação das strings (D-003).
- Todos os dados dos autores entram, porque ligam os registros e formam os nós das redes (D-004). Referências e citações são cruciais e entram na primeira versão (D-005).
- **Desde 2026-11-14 o Erick aceita de antemão as recomendações do Claude**, em qualquer decisão de construção e arquitetura ("fico sempre com as recomendações"), e pediu para seguir sem interrupções. O Claude decide, registra em `docs/decisions.md` e conta em uma linha. Publicar uma versão (PyPI, release) continua pedindo o ok dele.

## Steps

| Step | Situation | Main questions |
|---|---|---|
| system-description | closed | 4 of 4 |
| requirements | closed | 3 of 3 |
| modeling | closed | 3 of 3 |
| architecture | closed | 3 of 3 |
| plan | closed | 1 of 1 |

## Documents

| Document | Situation | Where |
|---|---|---|
| system-description | ready | docs/system-description.md |
| requirements | ready | docs/requirements.md |
| research | ready | docs/research.md |
| architecture | ready | docs/architecture.md |
| decisions | ready | docs/decisions.md |
| plan | ready | docs/plan.md |
| use-cases | ready | docs/use-cases.md |
| data-model | ready | docs/data-model.md |
| interface-contract | ready | docs/interface-contract.md |
| data-classification | ready | docs/data-classification.md |
| test-plan | ready | docs/test-plan.md |

## Main questions

### system-description

- [x] Que problema o sistema resolve, e para quem
- [x] O que o Erick quer alcançar com ele
- [x] Como ele chega às pessoas que o usam
- [x] O que fica fora da primeira versão

### requirements

- [x] O que cada tipo de usuário precisa conseguir fazer
- [x] O que limita o projeto: orçamento, prazo, lei, o que já usa
- [x] Como saber que funcionou

### modeling

- [x] As jornadas que não podem dar errado
- [x] O que o sistema guarda (cache, log de buscas)
- [x] Quais chamadas (ferramentas do MCP) ele oferece

### architecture

- [x] A stack: Python, SDK oficial mcp 2.x, arquivos soltos, empacotamento por PyPI
- [x] Onde roda e como é instalado
- [x] O que mais gera custo, como os créditos de API

### plan

- [x] O que vem primeiro

## Refinement questions left for later

- [x] (modeling) Autores e ORCID contam como dado pessoal? Tratado como sim, por dedução: o projeto ganhou data-classification.md. A conferência da lei ficou no T-007.

## Answers

### system-description · Problema, objetivo e entrega

O Erick quer um app que permita pesquisar um artigo, ou um tema, palavra-chave ou subtema, e listar os artigos das bases consultadas com metadados (autor, tema, título, coautores e o que mais houver), para exportar para ferramentas de revisão sistemática como o VOSviewer. Não terá banco próprio: usa as APIs de bases abertas. O servidor MCP é self-hosted e a IA converte a linguagem natural em termos técnicos de busca. Há também a ideia de um app executável para Windows e Linux. Uso não comercial, para ele, para um doutorando e para quem mais quiser. Como função extra, ele propôs baixar texto completo com uma API comunitária do Sci-Hub; ficou fora do projeto (ver research.md).

### system-description · Idioma, equipe e escopo

Documentos em português do Brasil. Só o Erick desenvolve, com agentes. Seguiu a recomendação de escopo: a primeira versão é só o servidor MCP com OpenAlex, Crossref e Semantic Scholar; ficam fora o app desktop, o Scopus, a Web of Science e o Periódicos CAPES. Tudo em Python. Aceitou o plano de fases e a arquitetura propostos ("vamos assim mesmo"); a arquitetura será formalizada na etapa própria.

### requirements · O que o pesquisador faz e o que entra na primeira versão

Confirmou a lista de capacidades: pedir em linguagem natural e a IA buscar por tema, palavra-chave, subtema, título ou um artigo específico; receber a lista com metadados; exportar para o VOSviewer; configurar o servidor e as chaves de API na própria máquina. Sobre "colocar direto no VOSviewer": o servidor entrega o arquivo ou a URL prontos, e não abre o programa. A deduplicação entre fontes e o log das buscas entram já na primeira versão.

### requirements · Limites e critério de aceite

Não há prazo. O uso esperado é "talvez uma centena por semana" (artigos ou buscas, a esclarecer). Aceitou o critério de aceite proposto: uma busca em linguagem natural, feita pela IA, devolve uma lista sem duplicatas, com os campos combinados, registrada no log, e o arquivo abre no VOSviewer sem edição manual. Não corrigiu o que foi deduzido sobre os limites (orçamento zero, termos de cada API respeitados, chaves próprias de cada usuário).

### modeling · Jornadas

Confirmou as três jornadas que não podem dar errado: buscar por tema e exportar para o VOSviewer, achar um artigo específico e exportar, e repetir uma busca a partir do log. Se uma fonte falha no meio da busca, o servidor segue com as outras e marca a falha na lista. Não quer juntar várias buscas numa lista só: as listas ficam separadas por pedido, e a IA deve ver isso e planejar antes de usar o MCP de busca, devolvendo cada lista separada da melhor forma.

### modeling · O que o sistema guarda

Quer cache das respostas das APIs, com prazo para expirar. As listas ficam salvas na máquina, para reexportar depois. O log deve ser interpretável por pessoas, para anexar na metodologia. Isso virou FR-12, FR-13 e NFR-06 nos requisitos.

### plan · O que vem primeiro

Aceitou a ordem proposta ("pra mim essa tá boa"): esqueleto, fatia completa com OpenAlex até o RIS no VOSviewer, mais fontes, referências e citações, resto das chamadas e formatos, publicação no PyPI. O plano tem seis fases e 16 tarefas, uma spec por tarefa em docs/specs/.

### architecture · Stack, armazenamento, instalação, núcleo e custo

Seguiu as recomendações da biblioteca do MCP (SDK oficial 2.x), da instalação (PyPI com uvx), de começar o núcleo do zero e de limitar o custo de referências e citações (referências no registro, citações sob demanda, teto de 1.000). Na decisão do armazenamento escolheu contra a recomendação: só arquivos soltos, sem banco. O tratamento da gravação segura ficou na Arquitetura.

### modeling · Chamadas do MCP, dados dos autores, referências e citações

Aprovou a lista de chamadas ("ótimas") e a pasta configurável para as exportações, devolvendo o caminho. A busca roda direto, sempre, sem mostrar as strings antes (D-003). Quer que entrem todos os dados dos autores, porque ligam os registros e formam os nós. Referências e citações são cruciais na primeira versão. Isso gerou a chamada `get_related_works`, o requisito FR-14 e FR-15, e a lista própria de relacionados (UC-04).

## Decisions

- D-001 · Linguagem do projeto: Python · decided
- D-002 · Chamadas do servidor MCP · decided
- D-003 · A busca roda direto, sem etapa de aprovação · decided
- D-004 · Todos os dados dos autores entram · decided
- D-005 · Referências e citações entram na primeira versão · decided
- D-006 · Biblioteca do servidor MCP: SDK oficial mcp 2.x · decided
- D-007 · Armazenamento: só arquivos · decided
- D-008 · Instalação: PyPI com uvx · decided
- D-009 · Núcleo escrito do zero, com os MCPs existentes como referência · decided
- D-010 · Referências no registro, citações sob demanda, com teto · decided
- D-024 · Interface do app desktop: NiceGUI em janela própria · decided (2026-11-14)
- D-025 · App desktop na 2.0: quatro telas, extra do pacote e executáveis · decided (2026-11-14)
- D-026 · Chaves no app desktop: arquivo de configuração do app · decided (2026-11-14)

## Open points

- Conferir se existe MCP comunitário do VOSviewer; a busca não foi exaustiva (item T-004 do plano de testes)
- Ler o código dos MCPs existentes antes dos conectores (T-010)
- Tempo máximo que o cliente MCP espera por uma resposta, em buscas longas (T-006)
- Configurar o Langfuse (Erick vai pedir)
- "Uma centena por semana" são artigos ou buscas? (Erick; pouco volume de qualquer jeito)
- Prazo de expiração do cache, formato do log legível, estrutura dos arquivos e gravação segura (Arquitetura, spec)
- Custo real de referências e citações e da troca de ids por DOI (T-005)
- O que a LGPD exige para guardar nomes e ORCID de autores (T-007; Erick)
- Se o usuário precisa de um meio fácil de apagar os dados guardados (Erick)

## Next question

**v1 lançada em 2026-11-05:** `rslapp` 1.0.0 no PyPI e release v1.0.0 no GitHub, com README. As 17 tarefas do plano (run `b20261102-221933` do Playmaker) estão prontas, testadas pelo Erick. Gates: ruff limpo e 455 testes em Python 3.10 e 3.14. O critério de aceite passou.

- **Fase 9 · Versão 1.2 (2026-11-11): código pronto, 09-01 a 09-06 "para testar".** PubMed e Europe PMC como fontes pedidas (D-020), BibTeX, `merge_lists` (D-021, 9 ferramentas) e o polimento do modo hospedado (Host em todas as rotas, link do log, limpeza das exportações, Actions em Node 24). Run `b20261111-144701` do Playmaker: a cota do Gemini 4 Argon acabou no início (reset em ~5 dias), e tudo foi feito no Gemini 3.8 Flash, com o agente revisor em toda entrega (09-01, 09-04 e 09-06 voltaram uma vez). README, contrato, arquitetura e guia de hospedagem atualizados.
- **Fase 10 · Bases pagas e filtros (1.3): código pronto em 2026-11-12, 10-01 a 10-04 "para testar".** Run `b20261111-211913` do Playmaker (Gemini 3.8 Flash, agente revisor em toda entrega; a 10-02 e a 10-04 voltaram uma vez).
  - 10-01: pareceres fora da busca, com `include_peer_review` (D-022).
  - 10-02 e 10-03: fontes Scopus e Web of Science Starter.
  - 10-04: as duas no servidor, só no stdio e com as chaves de quem usa; no modo hospedado são recusadas (D-023).
  - README, contrato e guia de hospedagem atualizados.
  - **Teste real do Scopus feito em 2026-11-13, aprovado pelo Erick** (rede da faculdade, chave `SCOPUS_API_KEY` no Lore, visão COMPLETE liberada, RIS conferido no VOSviewer). Achado: a string do Scopus/WoS no `log.md` mostrava só a última página, e isso virou a 10-06.
  - **10-06 integrada em 2026-11-13** (commits `9d46159` e `0461e06`, para testar): o log grava a busca inteira do Scopus e do WoS (visão, tamanho da página, páginas 1-N).
  - 10-06 conferida pelo Erick no VOSviewer em 2026-11-14.
  - **10-05 pronta em 2026-11-14:** `rslapp` 1.3.0 no PyPI (conferida com `uvx`), tag e release `v1.3.0`, imagem `1.3.0`/`latest` no ghcr.io, `rsl.sinteselabs.com` com `/health` 1.3.0; no conector hospedado, `list_sources` mostra só as 5 fontes abertas. 675 testes em 3.10, 3.12 e 3.14. Falta só testar o Web of Science quando a chave sair (`WOS_STARTER_API_KEY`, pelo Lore).
  - **Próximo: a 2.0, fase 11 · App desktop** (D-024 a D-026, specs 11-01 a 11-05). O código vai pelo `agy`, uma tarefa por vez. O servidor do projeto vem depois (LGPD e custo).
  - **11-01 integrada em 2026-11-14** (para testar): base do app, `rslapp-desktop` abre a janela nativa no Windows, só em `127.0.0.1`.
  - **11-02 e 11-03 paradas em 2026-11-14:** rodavam em paralelo pelo `agy` nas worktrees `../RSL.app-wt/11-02` (branch `feat/11-02-buscar-lista`) e `../RSL.app-wt/11-03` (`feat/11-03-historico-config`) e foram encerradas pelo Claude Code por falta de memória no computador (1,8 GB livres de 15,7 GB), ainda na leitura da documentação: nenhum código feito. Para retomar: os prompts estão nos arquivos da sessão; rodar uma de cada vez para gastar menos memória. A 11-04 espera as duas.
- **Servidor de teste na Azure: fica no ar** por decisão do Erick (2026-11-14), que vai usá-lo nos próximos meses. Não perguntar de novo.
- **Gates:** `uv run --python <v> --extra dev python -m pytest`; o `uv run pytest` puro pode pegar o pytest do sistema, sem o `mcp`.
- **Fase 9 pronta (2026-11-11), conferida pelo Erick.** 09-07: 1.2.0 publicada. `rslapp` 1.2.0 no PyPI, tag e release `v1.2.0`, imagem `1.2.0`/`latest` no ghcr.io, servidor `rsl.sinteselabs.com` atualizado (`/health` 1.2.0). 622 testes em 3.10 e 3.14. O compose passou a repassar `NCBI_API_KEY`. O Claude Code testou sem tela, pelo stdio com buscas reais, pelo modo HTTP local com duas pessoas e pelo conector RSL-APP no claude.ai do Erick; tudo passou, e o Erick conferiu no Zotero, no VOSviewer e no Claude Desktop. Achado para decidir: o OpenAlex traz registros de revisão por pares (Publons, tipo `peer-review`) como artigos.
- **v2, fase 8 · Uso por link: pronta em 2026-11-11.** Decidida com o Erick (D-012 a D-018): login OAuth com código pessoal por pessoa (`rslapp token add|list|revoke`, `user purge`), sessão sem prazo, dados separados por pessoa com cache compartilhado, chaves de quem hospeda, exportação por link assinado de 1 hora, Docker com Caddy e imagem no ghcr.io, LGPD conferida antes de anunciar. 08-01 e 08-02 com o `agy` direto; 08-03 a 08-06 pela run `b20261110-163816` do Playmaker (08-03 em duas rodadas). 531 testes em 3.10 e 3.14. Teste à mão do servidor local: `/health`, 401 com metadados OAuth em `/mcp`, download falso 404.
- **08-07 pronta (2026-11-11):** `rslapp` 1.1.0 no PyPI, tag e release `v1.1.0`, imagem `1.1.0`/`latest` no ghcr.io (pública, amd64 e arm64). Teste real em `rsl.sinteselabs.com`, máquina `rsl-app` da Azure for Students em North Central US (D-019; a assinatura de estudante só permite cinco regiões). Os passos 6 a 8 passaram. **O servidor de teste continua no ar** (cerca de US$ 13/mês pela tabela: máquina US$ 6,86, IP fixo US$ 3,65, disco US$ 2,40; a conta de estudante tem US$ 538 de crédito até 11/11/2027) até o Erick decidir parar ou apagar (grupo `rsl-app`; registro A `rsl` na Hostinger). Entrada por `ssh -i ~/.ssh/rsl-teste azureuser@<IP>`.
- **Acompanhamentos da v2** (no fim das specs 08-0x): a proteção de host (421) vale só para `/mcp`; `/health`, `/login`, `/authorize`, os metadados OAuth e `/downloads` respondem a qualquer `Host` (sem cookie nem sessão, risco baixo). O servidor HTTP registra as ferramentas numa lista em `_build_http_mcp_server`.
- **O que espera o Erick:** a LGPD (T-007) antes de divulgar o modo hospedado.
- **07-01 · Entradas numéricas sem verdadeiro/falso (2026-11-09): pronta.** Feita pelo Gemini 4 Argon via `agy --dangerously-skip-permissions`, revisada e integrada na `main` e enviada ao GitHub. 471 testes em 3.10 e 3.14. Publicada como `rslapp` 1.0.1 no PyPI em 2026-11-09 (tag e release `v1.0.1`); testada pelo Erick no Claude Desktop em 2026-11-10.
- **Para publicar uma versão nova:** subir `version` no `pyproject.toml` e `__version__` em `src/rslapp/__init__.py`, `uv build --no-sources`, conferir o sdist (`tar -tzf`), `lore secrets run --env prod -- uv publish dist/*`, tag e `gh release create`.
- **Acompanhamentos das revisões** estão no fim de cada spec; nenhum bloqueia.
- **Testes de pé:** T-004, T-005 com o teto padrão de 1.000, T-006 (tempo de espera do cliente), T-007 (LGPD, Erick), T-008 (mapa de citação), T-010.
- **`uv run --with .` usa wheel antiga** mesmo com `--reinstall-package`: para testar o código atual, rodar no modo projeto (Lore: `gotchas/uv-wheel-antiga-no-gate.md`). O Claude Desktop do Erick usa o `rslapp` do PyPI, lançado por `lore secrets run`.
- Segredos no Lore (prod): `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` e `UV_PUBLISH_TOKEN` (token do PyPI só do projeto). Pasta dos testes reais: `C:\Users\hulkd\RSL-teste`.
- Pasta do projeto desde 2026-11-03: `C:\Users\hulkd\Sintese-Labs-Projetos\RSL.app` (sem sublinhado; conferido em 2026-11-09); árvores do Playmaker em `..\RSL.app-playmaker`.
