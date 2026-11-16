# Ideias para as próximas versões

**Projeto:** RSL.app · **Data:** 2026-11-16 · **Situação:** sugestões do Claude para o Erick decidir. Nada aqui é decisão nem entrou no plano.

> **Em resumo:** o RSL.app já busca, junta, registra e exporta. O próximo salto é cobrir a revisão inteira: protocolo, triagem, leitura, fichamento, síntese e o relato no método. Em cada passo, a IA do pesquisador ajuda, e o app registra o que ela fez e o que a pessoa decidiu. Esse registro é o que tira o tabu: a IA deixa de ser escondida e passa a ser declarada e conferível.
>
> As cinco que mais sobem o patamar, na minha opinião: **(1)** o fluxograma PRISMA com os números reais; **(2)** a triagem com rastro (quem decidiu, a pessoa ou a IA, e por quê); **(3)** o verificador de referências contra alucinação; **(4)** as bases brasileiras (SciELO, BDTD, LILACS/BVS, com os descritores DeCS); **(5)** o login institucional pela CAFe.

Cada ideia diz para que serve, como conversa com o **Fundamento** (rastreabilidade, reprodutibilidade, IA do próprio pesquisador, academia brasileira) e o que a instituição ganha (D-029). O que está marcado **(de memória, a conferir)** não foi lido numa página oficial nesta sessão. A regra do projeto vale: ler a página oficial antes de virar spec (T-001).

---

## 1. Metodologia de ponta a ponta: do protocolo ao relato

### 1.1 Protocolo da revisão antes da busca
- **O que é:** uma tela (e uma ferramenta MCP) onde a pessoa registra:
  - a pergunta, no formato que a área usa (PICO, PICo, SPIDER, PCC da revisão de escopo);
  - os critérios de inclusão e exclusão;
  - as bases e as strings planejadas.
- **Data e versão:** o protocolo fica datado e versionado. Toda busca aponta para a versão que valia quando rodou.
- **Por que sobe o patamar:** é o que o PROSPERO e o OSF pedem e o que a banca cobra. A IA ajuda a montar a pergunta e as strings, e o protocolo registra que ajudou.
- **Para instituições:** a biblioteca da universidade pode oferecer modelos de protocolo por área.

### 1.2 Fluxograma PRISMA 2020 e relatório PRISMA-S com os números reais
- **O que é:** o app já sabe quantos registros vieram de cada base, quantos se repetiram e quantos ficaram. Com a triagem (1.3), sabe também os excluídos e o motivo de cada exclusão.
- **O que ele gera:**
  - o **fluxograma PRISMA 2020** pronto, em SVG ou PNG e editável;
  - o **checklist PRISMA-S** da busca: as bases, as datas, as strings exatas, os filtros e os números.
- **Por que sobe o patamar:** é a parte mais trabalhosa e mais errada das revisões. Sai sem erro porque vem do log, não da memória.

### 1.3 Triagem com rastro (título e resumo, depois texto completo)
- **O que é:** cada artigo recebe uma decisão (incluir, excluir ou talvez) com o motivo ligado a um critério do protocolo.
- **O papel da IA:** a IA pode sugerir uma decisão com uma justificativa curta. A decisão final é da pessoa.
- **O registro:**
  - quem decidiu (pessoa ou IA, e qual modelo);
  - se a pessoa aceitou ou trocou a sugestão;
  - a data.
- **Dupla triagem:** dois revisores, como orientador e orientando, triam às cegas. O app mostra as discordâncias e calcula o kappa de Cohen.
- **Por que sobe o patamar:** é a resposta concreta a "a IA fez a revisão por você?". O log mostra exatamente o que ela sugeriu e o que a pessoa decidiu. É também a métrica que a pesquisa sobre IA em revisões precisa: a concordância entre a IA e o humano.

### 1.4 Declaração de uso de IA, gerada a partir do log
- **O que é:** um texto pronto para a seção de métodos. Ele diz:
  - quais etapas tiveram ajuda de IA, com qual modelo e em que datas;
  - o que a pessoa conferiu;
  - onde está o log completo.
- **Formato:** segue as orientações dos periódicos e da SciELO sobre uso de IA **(de memória, a conferir: o guia da SciELO de 2023)**.
- **Por que sobe o patamar:** transforma o uso de IA de algo escondido em algo declarado, padronizado e conferível. É a peça que mais ataca o tabu.

### 1.5 Pacote de reprodutibilidade
- **O que leva:** um `.zip` com o protocolo, o log, as strings, as listas, as decisões de triagem, as fichas, as versões do app e das fontes, e um hash de cada arquivo.
- **Publicação opcional:** a pessoa pode publicar o pacote no Zenodo ou no OSF, com a conta dela, e ganhar um DOI.
- **Para instituições:** o pacote pode ir para o repositório institucional (DSpace) como material suplementar da tese.

### 1.6 Revisão viva: repetir e comparar
- **Repetir com comparação:** "repetir busca" mostra o que entrou e o que saiu desde a última vez.
- **Alerta:** o app avisa quando uma busca salva tem artigos novos (semanal, opcional).
- **Por que sobe o patamar:** atualizar uma revisão para publicação, ou entre a qualificação e a defesa, vira um clique, com o registro do que mudou.

---

## 2. Leitura e fichamento

### 2.1 Fichamento estruturado com a IA, marcado como sugestão
- **Duas ferramentas MCP novas:** `save_note` e `get_notes`. A ficha de cada artigo tem:
  - a referência ABNT;
  - objetivo, método, amostra, resultados e limitações;
  - citações diretas com página;
  - as palavras-chave próprias da pessoa.
- **Marcação de origem:** a IA do pesquisador preenche, e cada campo fica marcado como "sugerido pela IA" até a pessoa revisar.
- **Exportação:** em Word, Markdown (para Obsidian) e como nota do Zotero.
- **Por que sobe o patamar:** é o pedido do Fundamento. Fichar é onde o pesquisador brasileiro mais gasta tempo, e onde a IA mais ajuda se o texto dela for conferível.

### 2.2 Listas de leitura com prioridade
- **Ordem sugerida:** mais citados, mais recentes, mais centrais na rede de citação (3.1) ou mais aderentes ao protocolo.
- **Ligação com as fichas:** cada item tem estado (a ler, lido, fichado) e aponta para a sua ficha.

### 2.3 Texto completo legal, em acesso aberto
- **O que faz:** acha a versão aberta de cada artigo, quando ela existe, e baixa para a pasta da revisão.
- **Onde procura:** Unpaywall, as localizações de acesso aberto do OpenAlex, PubMed Central, SciELO e CORE.
- **O que nunca usa:** o Sci-Hub continua fora do projeto.
- **Por que sobe o patamar:** a triagem pelo texto completo e o fichamento dependem do texto. Hoje a pessoa baixa um por um.

### 2.4 Tabela de extração para a meta-análise
- **O que é:** os campos vêm do protocolo, como tamanho do efeito, n e desenho. A IA propõe os valores com o trecho de onde tirou, e a pessoa confere.
- **Exportação:** em CSV, pronto para o R (metafor, meta) e o RevMan.

### 2.5 Avaliação de qualidade e de risco de viés assistida
- **Os instrumentos:** RoB 2, ROBINS-I, os checklists do JBI e do CASP, e GRADE para a certeza da evidência.
- **Como funciona:** a IA sugere cada item com a justificativa e o trecho do artigo, e a pessoa decide. Tudo fica no log.

---

## 3. Redes e bibliometria (o público do VOSviewer)

### 3.1 Redes prontas, dentro do app e para fora
- **As redes:**
  - coautoria (autores, instituições e países);
  - cocitação;
  - acoplamento bibliográfico;
  - coocorrência de palavras-chave.
- **Para fora:** os arquivos `map` e `network` nativos do VOSviewer **(de memória, a conferir: o formato no manual 1.6.20)**, GEXF para o Gephi e o formato do Bibliometrix (R).
- **Por que sobe o patamar:** hoje a pessoa exporta e monta a rede noutro programa. Ver a rede logo depois da busca ajuda a refinar a string, por exemplo descobrindo o termo que a área usa.

### 3.2 Autores, instituições e palavras-chave desambiguados
- **Autores:** pelo ORCID.
- **Instituições:** pelo ROR.
- **Palavras-chave:** unir sinônimos e variações (singular e plural, inglês e português) com uma tabela de equivalências que a pessoa revisa e o log guarda.
- **Por que sobe o patamar:** é o problema número um de quem faz mapa no VOSviewer. A IA sugere as junções, e a pessoa aprova.

### 3.3 Indicadores bibliométricos prontos
- **O que mostra:** a produção por ano, os periódicos e as leis de Bradford e Lotka, os países, as colaborações e os mais citados.
- **Formato:** um relatório em português pronto para a seção de resultados de um estudo bibliométrico.

---

## 4. Academia brasileira

### 4.1 Bases brasileiras e latino-americanas
- **As bases:**
  - **SciELO** (ArticleMeta ou a busca da SciELO);
  - **LILACS/BVS** (BIREME);
  - **BDTD**, de teses e dissertações (IBICT);
  - **Oasisbr** (IBICT);
  - **Catálogo de Teses e Dissertações da CAPES**;
  - **Redalyc** e **La Referencia**.
- **A conferir:** quais têm API ou OAI-PMH aberto e o que os termos permitem **(de memória, a conferir por base, T-001)**.
- **Por que sobe o patamar:** boa parte da produção brasileira, sobretudo nas humanas, na educação e na enfermagem, não está bem coberta no OpenAlex. Teses e dissertações são literatura cinzenta que as revisões brasileiras precisam incluir.

### 4.2 Descritores DeCS/MeSH e strings em três línguas
- **DeCS:** o DeCS (BIREME) é trilíngue (português, espanhol e inglês). A IA monta a string com os descritores certos em cada língua, e o app guarda o descritor e o sinônimo usados.
- **Fora da saúde:** a IA sugere os equivalentes em inglês e espanhol, e o log mostra a string final de cada base.

### 4.3 Referências na ABNT
- **O que faz:** exporta as referências na NBR 6023:2018 (há estilo CSL para isso) e gera a lista de referências da revisão.
- **Por que sobe o patamar:** é a norma que a maioria dos programas de pós-graduação exige.

### 4.4 Qualis e indicadores do periódico na lista
- **O que mostra:** o estrato Qualis do periódico ao lado de cada artigo (dado público da CAPES), e o acesso aberto ou não.
- **A conferir:** como a CAPES publica o Qualis do quadriênio atual e se pode ser redistribuído **(de memória, a conferir)**.

### 4.5 Tipos de revisão comuns no Brasil, com roteiro próprio
- **O que é:** prompts MCP prontos para a revisão integrativa (muito usada na enfermagem), a revisão de escopo (JBI), a sistemática, a bibliométrica e a narrativa. Cada um traz as etapas, os relatos exigidos e o modelo de protocolo.
- **Por que sobe o patamar:** a IA passa a conduzir o método certo, em vez de uma "busca genérica".

---

## 5. A IA como parceira conferível

### 5.1 Verificador de referências contra alucinação
- **O que faz:** a pessoa cola um texto ou um `.bib`, ou a IA manda as referências que citou. O app confere cada uma no Crossref e no OpenAlex e marca o resultado:
  - **existe**;
  - **existe com dados diferentes** (o ano ou os autores não batem);
  - **não encontrada**.
- **Por que sobe o patamar:** referência inventada por IA é hoje o maior motivo de desconfiança na academia. Uma ferramenta que confere vale para alunos, orientadores, bancas e revistas, mesmo para quem não faz revisão sistemática. É a porta de entrada mais fácil para o RSL.app.

### 5.2 Retratações e expressões de preocupação
- **O que faz:** marca nas listas os artigos retratados, pela base do Retraction Watch, que hoje é aberta pela Crossref **(de memória, a conferir)**.
- **O aviso:** ele aparece também na exportação e na ficha.

### 5.3 Perguntar à própria biblioteca, com o trecho citado
- **O que faz:** busca semântica sobre os resumos, as fichas e os textos completos da revisão.
- **A regra da resposta:** toda resposta aponta o artigo e o trecho, nunca um texto sem fonte.
- **Onde roda:** o índice fica na máquina da pessoa ou no servidor da instituição.

### 5.4 Recursos MCP e telas dentro da IA
- **Recursos MCP:** as listas e as fichas viram resources, que a IA lê sem uma chamada de ferramenta.
- **Telas na conversa:** onde o cliente aceitar (MCP Apps, Apps SDK do ChatGPT), a tabela da lista e o fluxograma aparecem dentro da conversa.

### 5.5 IA local para quem não pode mandar dados à nuvem
- **O que é:** um guia, e depois um atalho, para usar um modelo aberto rodando na instituição (Ollama e Open WebUI) ligado ao RSL.app hospedado.
- **Para instituições:** responde à objeção da LGPD e do sigilo, porque nenhum texto sai do campus.

---

## 6. Para as instituições

### 6.1 Login pela CAFe (RNP)
- **O que é:** o pesquisador entra com o usuário da própria universidade pela federação CAFe (SAML), em vez de um código pessoal criado à mão **(de memória, a conferir: requisitos de adesão à CAFe)**.
- **Por que sobe o patamar:** é o que torna o RSL.app oferecível para milhares de pessoas sem uma pessoa de TI cadastrando uma a uma. É provavelmente o recurso que decide a adoção por uma universidade.

### 6.2 Equipes e revisão colaborativa
- **O que é:** grupos (orientador e orientandos, ou um laboratório) que compartilham protocolo, listas, triagem e fichas, com o registro de quem fez o quê.

### 6.3 Painel institucional, sem dados pessoais
- **O que mostra:** números agregados (revisões em curso, buscas por área, bases mais usadas) para a pró-reitoria e a biblioteca.
- **O que não mostra:** nada de nomes nem conteúdo.

### 6.4 Pacote LGPD para a instituição
- **O que leva:** depois da T-007, um modelo de registro das operações de tratamento e de aviso aos usuários, e o comando de exclusão que já existe (`user purge`).
- **Por que vem antes:** isso destrava divulgar o modo hospedado (D-018).

### 6.5 Material de formação para as bibliotecas
- **O que leva:** um roteiro de oficina, slides e exercícios ("revisão sistemática com IA rastreável"), para a biblioteca ensinar.
- **Por que sobe o patamar:** as bibliotecas universitárias já ensinam revisão sistemática. Tê-las como parceiras é o caminho mais curto até os pesquisadores e a forma mais direta de tirar o tabu.

---

## 7. Qualidade do app

- **Importar o que veio de fora:** exportações do Scopus, da Web of Science e do Portal CAPES feitas à mão (RIS, BibTeX, CSV) e bibliotecas do Zotero. Os registros entram na deduplicação e nos números do PRISMA. Muita gente só tem essas bases pela interface web.
- **Zotero direto:** mandar a lista para uma coleção do Zotero pela API dele, com as fichas como notas.
- **macOS:** executável para Mac.
- **Executável assinado:** acaba o aviso do SmartScreen, mas **custa dinheiro**, então a decisão é do Erick.
- **Atualização automática do app:** avisar quando há versão nova.
- **As dívidas registradas:**
  - o Histórico fica lento com centenas de buscas, e há dois caminhos em `settings.py` (11-03);
  - T-004, T-005 (medir com o teto de 1.000), T-006 e T-008 (mapa de citação) estão em aberto no plano de testes.

---

## Uma ordem possível

| Versão | Foco | O que entra |
|---|---|---|
| **2.2** | Ganhos rápidos com muito efeito | Verificador de referências (5.1), retratações (5.2), importar exportações de fora (7), ABNT (4.3) |
| **2.3** | Academia brasileira | SciELO, BDTD, LILACS/BVS e DeCS (4.1, 4.2), roteiros por tipo de revisão (4.5) |
| **3.0** | A revisão inteira, com IA rastreável | Protocolo (1.1), triagem com rastro (1.3), PRISMA (1.2), declaração de uso de IA (1.4), pacote de reprodutibilidade (1.5) |
| **3.x** | Leitura e síntese | Fichamento (2.1), listas de leitura (2.2), texto aberto (2.3), extração (2.4), risco de viés (2.5), redes e indicadores (3.1 a 3.3) |
| **4.0** | Escala institucional | CAFe (6.1), equipes (6.2), painel (6.3), IA local (5.5), pacote LGPD (6.4) |

A LGPD (T-007) e o pacote para as instituições (6.4) deveriam vir antes de qualquer divulgação do modo hospedado, seja qual for a ordem do resto.
