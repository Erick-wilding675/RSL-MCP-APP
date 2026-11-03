# Requisitos

**Projeto:** RSL.app · **Versão:** 0.2 · **Data:** 2026-11-02

> **Em resumo:** O pesquisador pede em linguagem natural, a IA chama o servidor MCP, e o servidor busca no OpenAlex, Crossref e Semantic Scholar, tira as duplicatas, registra a busca e entrega uma lista pronta para o VOSviewer.
> Quinze requisitos funcionais e seis não funcionais, todos da primeira versão. Referências, citações e todos os dados dos autores são centrais.
> Limites: gratuito, sem fins comerciais, self-hosted, tudo em Python, sem prazo definido, uso de cerca de uma centena por semana.
> O aceite é uma busca que devolve lista sem duplicatas, com os campos combinados, registrada no log, e que abre no VOSviewer sem edição manual.

## O que o sistema é

Um servidor MCP self-hosted em Python, usado por pesquisadores (o Erick, um doutorando e quem mais quiser) para fazer buscas de revisão sistemática com a ajuda da IA, sem banco de artigos próprio.

## Requisitos funcionais

O que o pesquisador, por meio da IA dele, precisa conseguir fazer.

| Nº | Requisito | Prioridade | Vem de |
|---|---|---|---|
| FR-01 | O servidor oferece à IA uma ferramenta de busca que recebe termos técnicos (tema, palavra-chave, subtema ou título) e consulta OpenAlex, Crossref e Semantic Scholar | Primeira versão | Erick: pesquisar por tema, palavra-chave ou subtema; escopo aceito em 2026-11-02 |
| FR-02 | O servidor encontra um artigo específico, a partir do título ou do DOI, para ser exportado | Primeira versão | Erick: "pesquise um artigo e exporte ele"; o DOI foi deduzido |
| FR-03 | Cada resultado traz título, ano, periódico, resumo, palavras-chave e DOI, quando a fonte tiver. Dos autores, traz todos os dados que a fonte oferecer: nome, ORCID, identificadores do autor nas fontes e afiliações, na ordem dos autores, com os coautores incluídos | Primeira versão | Erick: "autor, tema, título, coautores e tudo mais"; 2026-11-02: "quero que entre tudo, esses dados são essenciais para ligar os registros entre si" |
| FR-04 | O mesmo artigo vindo de mais de uma fonte aparece uma só vez na mesma lista | Primeira versão | Erick, 2026-11-02: deduplicação na primeira versão |
| FR-05 | Cada busca é registrada num log com a string enviada a cada base, a data e o número de resultados | Primeira versão | Erick, 2026-11-02: log na primeira versão |
| FR-06 | O servidor exporta a lista em arquivo RIS, em CSV, em JSON completo e em lista de DOIs; nas buscas do OpenAlex, também a URL da consulta. O VOSviewer abre o resultado sem edição manual | Primeira versão | Erick: "entrega pronto"; formatos da pesquisa (research.md). O JSON completo foi deduzido, porque RIS e CSV levam só parte dos dados (T-008) |
| FR-07 | A pessoa configura o servidor e as chaves de API na própria máquina, sem mexer no código | Primeira versão | Erick: servidor self-hosted, configurado pelo usuário |
| FR-08 | Se uma fonte falha ou atinge o limite durante uma busca, o servidor segue com as outras. A lista sai marcada como incompleta, com a fonte que falhou e o motivo, e isso também vai para o log | Primeira versão | Erick, 2026-11-02: "segue e marca a falha"; a pesquisa mostrou o risco (a Semantic Scholar devolve muitos erros 429 sem chave) |
| FR-09 | Cada pedido de busca gera uma lista própria, com identificador. O servidor não junta listas de pedidos diferentes | Primeira versão | Erick, 2026-11-02: listas separadas por pedido |
| FR-10 | O servidor orienta a IA, por instruções e por um prompt do MCP, a planejar antes de buscar: o que for melhor buscado e entregue separadamente vira buscas separadas, e cada lista volta separada | Primeira versão | Erick, 2026-11-02: a IA deve ver isso e planejar antes de usar o MCP de busca; o mecanismo (instruções ou prompt) foi deduzido |
| FR-11 | Uma busca do log pode ser repetida com as mesmas strings e as mesmas bases, e gera uma nova entrada no log | Primeira versão | Erick, 2026-11-02: jornada de repetir uma busca a partir do log; a nova entrada foi deduzida |
| FR-12 | As listas ficam salvas na máquina do usuário e podem ser exportadas de novo, em outro formato, depois | Primeira versão | Erick, 2026-11-02: as listas "ficam salvas" |
| FR-13 | O log é um arquivo legível por pessoas, que o pesquisador pode anexar na metodologia do artigo | Primeira versão | Erick, 2026-11-02: log "interpretável" |
| FR-14 | Cada artigo traz as referências (os trabalhos que ele cita) e o número de citações recebidas, quando a fonte tiver. Quando nenhuma fonte entrega, o campo fica vazio e o log diz o motivo. Nunca é preenchido com valor suposto | Primeira versão | Erick, 2026-11-02: "é crucial que tenhamos esses dados também" |
| FR-15 | A partir de um artigo, o servidor traz as referências dele ou os trabalhos que o citam, como uma lista própria, registrada no log e ligada ao artigo de origem | Primeira versão | Erick, 2026-11-02: referências e citações são cruciais; a lista própria segue FR-09 e o formato foi deduzido |

## Requisitos não funcionais

| Nº | Requisito | Prioridade | Vem de |
|---|---|---|---|
| NFR-01 | O servidor funciona só com chaves gratuitas das fontes. Nenhuma funcionalidade da primeira versão exige pagamento | Primeira versão | Erick: gratuito e sem fins comerciais |
| NFR-02 | O servidor roda na máquina de quem usa, sem depender de nenhum servidor do projeto | Primeira versão | Erick: self-hosted |
| NFR-03 | Cada usuário usa as próprias chaves. As chaves ficam só na máquina dele e nunca aparecem no log nem nas respostas à IA | Primeira versão | Plano aceito em 2026-11-02; a parte do log e das respostas foi deduzida |
| NFR-04 | O servidor respeita os termos e os limites de cada API: espera e tenta de novo quando atinge o limite | Primeira versão | Deduzido; o Erick não corrigiu em 2026-11-02 |
| NFR-05 | O uso esperado, de cerca de uma centena por semana, cabe na cota gratuita das fontes, contando as chamadas de referências e citações | Primeira versão | Erick: "talvez uma centena por semana"; a cota real será conferida no T-002 e o custo de referências e citações no T-005 |
| NFR-06 | O servidor guarda em cache as respostas das APIs, com prazo para expirar, para gastar menos cota. O que vem do cache fica marcado no log | Primeira versão | Erick, 2026-11-02: cache sim; a marca no log foi deduzida, para a busca ser reprodutível |

## Limites

- **Orçamento:** zero. Gratuito e sem fins comerciais.
- **Prazo:** o Erick não tem prazo definido.
- **Tecnologia:** tudo em Python (D-001); servidor self-hosted.
- **Termos das APIs:** as regras de cada fonte valem. As bases que dependem de licença ou de acesso institucional ficam para depois.
- **Equipe:** só o Erick, trabalhando com agentes (Claude desktop para docs e specs, Gemini para o código, Claude Code com Playmaker para revisar e orquestrar).

## Fora da primeira versão

- App desktop para Windows e Linux.
- Abrir o VOSviewer na máquina do usuário. O servidor só entrega o arquivo ou a URL prontos.
- Scopus, Web of Science e Periódicos CAPES.
- Juntar várias buscas numa lista só (decisão do Erick em 2026-11-02).
- Etapa de aprovação das strings de busca antes de rodar. A busca roda direto, sempre, e o log guarda o que foi enviado (D-003).
- Download de texto completo. O Sci-Hub está fora do projeto.

## Como saber que funcionou

Uma busca em linguagem natural, feita pela IA, devolve uma lista sem duplicatas, com os campos combinados, registrada no log, e o arquivo abre no VOSviewer sem edição manual. O Erick confirmou esse critério em 2026-11-02. No fundo, é a revisão "robusta, completa e rigorosa" que ele descreveu.

## Pontos em aberto

| Nº | Ponto | Depende de |
|---|---|---|
| 1 | Lista exata de campos obrigatórios nos resultados | Spec das tarefas |
| 2 | "Uma centena por semana" são artigos ou buscas? De qualquer forma é pouco, e o T-002 confirma a cota | Erick |
| 3 | Quanto custa trazer referências e citações dentro das cotas (OpenAlex, Semantic Scholar) e como limitar | T-005 e Arquitetura |
| 4 | O que a LGPD exige para guardar nomes e ORCID de autores numa ferramenta local | T-007, Erick |
