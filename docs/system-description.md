# Descrição do sistema

**Projeto:** RSL.app · **Versão:** 0.2 · **Data:** 2026-11-02

> **Em resumo:** Um servidor MCP em Python, self-hosted, que deixa a IA do pesquisador buscar artigos em bases acadêmicas abertas (OpenAlex, Crossref e Semantic Scholar) e devolver uma lista com metadados, pronta para exportar para ferramentas de revisão sistemática, a começar pelo VOSviewer.
> É gratuito e sem fins comerciais, para o Erick, um doutorando e quem mais quiser fazer uma revisão sistemática rigorosa com IA.
> A primeira versão é só o servidor MCP. O app desktop e as bases que dependem de licença ficam para depois.

## O que é

RSL.app (RSL de Revisão Sistemática da Literatura) não tem banco de artigos próprio. Ele consulta as APIs de bases acadêmicas e consolida o resultado.

A pessoa conecta o servidor MCP, que roda na máquina dela, à IA que já usa. Ela pede o que procura em linguagem natural. A IA traduz o pedido para termos técnicos de busca, chama o servidor e recebe uma lista de artigos com metadados (título, autores, coautores, tema e o que mais as bases oferecerem). Essa lista sai em formatos que as ferramentas de revisão e de bibliometria já aceitam, como o VOSviewer.

## Problema e valor

- **O problema:** fazer uma revisão sistemática robusta e completa exige buscar em várias bases e levar o resultado para as ferramentas de revisão. O Erick e o doutorando precisam de um acesso facilitado a isso.
- **Quem tem:** o Erick, um doutorando e qualquer pessoa que queira uma revisão sistemática gratuita e facilitada, com IA e MCP.
- **Como é hoje:** (deduzido da pesquisa, ver `research.md`) busca em cada base à mão e exportação de arquivos RIS ou CSV, um a um.
- **O que muda:** o pesquisador pede em linguagem natural, a IA monta as buscas técnicas e a lista chega consolidada e exportável, como uma ponte direta até a ferramenta de revisão.

## Quem usa

| Quem | O que precisa |
|---|---|
| Pesquisador (o Erick, o doutorando e quem mais quiser) | Descrever o que procura em linguagem natural, receber a lista de artigos com metadados e exportá-la |
| A IA do pesquisador (qualquer cliente que aceite MCP) | Traduzir o pedido para termos técnicos, chamar as ferramentas do servidor e entregar o resultado |
| Ferramentas de revisão e bibliometria (VOSviewer primeiro) | Receber a lista exportada em um formato que aceitam |

## Objetivos e sucesso

1. Pesquisar artigos por tema, palavra-chave, subtema ou título, e achar um artigo específico para exportar.
2. Devolver a lista com metadados: autores com todos os dados que a fonte oferecer (nome, ORCID, identificadores, afiliações), coautores, tema, título, referências, citações e o que mais as bases oferecerem.
3. Exportar a lista direto para ferramentas de revisão sistemática, começando pelo VOSviewer, sem passos manuais no meio.
4. Ser gratuito e rodar na máquina de quem usa.

**Como saber que funcionou:** nas palavras do Erick, uma revisão sistemática "robusta, completa e rigorosa" feita com IA e MCP, com uma ponte direta até o VOSviewer. Ainda não há número. Os critérios de aceite entram em Requisitos.

## Como chega às pessoas

Servidor MCP self-hosted em Python. A pessoa instala e configura na própria máquina, com as próprias chaves de API, e conecta nas IAs que aceitam MCP. Um app executável para Windows e Linux, com busca e lista para exportar, vem depois da primeira versão.

## Escopo

- **Na primeira versão:** servidor MCP; fontes OpenAlex, Crossref e Semantic Scholar; busca por tema, palavra-chave e título; lista com metadados, com os dados completos dos autores, as referências e as citações; busca das referências e das citações de um artigo, em lista própria; deduplicação entre as fontes; log de cada busca (a string enviada a cada base, a data e o número de resultados); uma lista separada para cada pedido, salva na máquina do usuário; log legível por pessoas; cache das respostas das APIs; exportação para o VOSviewer em arquivo ou URL prontos para ele abrir.
- **Fora da primeira versão:** app desktop; juntar buscas diferentes numa lista só; abrir o VOSviewer na máquina do usuário (o servidor só entrega o arquivo ou a URL prontos); Scopus, Web of Science e Periódicos CAPES (dependem de licença ou de acesso institucional); download de texto completo.
- **Fora do projeto:** Sci-Hub. Ele distribui artigos pagos sem autorização das editoras. Quando o texto completo entrar, virá de acesso aberto e, para quem tem acesso, do Periódicos CAPES via CAFe (plano aceito em 2026-11-02, ver `research.md`).
- **Depois:** app desktop para Windows e Linux; Scopus e Web of Science com a chave de cada usuário; PubMed e Europe PMC; exportação para outras ferramentas além do VOSviewer.

## Limites e contexto

- **Limites declarados pelo Erick:** sem fins comerciais e gratuito para quem usa; self-hosted; tudo em Python; um só desenvolvedor, trabalhando com agentes (o Claude desktop escreve docs e specs, o Gemini escreve o código, o Claude Code revisa, corrige e orquestra com o plugin Playmaker); memória do projeto no Lore; Langfuse para observabilidade, a configurar depois.
- **Sistemas a conectar:** APIs do OpenAlex (chave gratuita obrigatória), Crossref e Semantic Scholar; VOSviewer como primeiro destino. Nada a substituir.
- **Decidido pelo agente:** a primeira versão não tem telas, então o projeto não terá wireframes nem design por enquanto. Reabrimos quando o app entrar.
- **Dados pessoais:** os dados dos autores (nome, ORCID, identificadores, afiliações) são públicos, vêm das APIs abertas e ficam só na máquina de quem usa. Ver `data-classification.md`.

## Pontos em aberto

| Nº | Ponto | Depende de |
|---|---|---|
| 1 | Conferir no GitHub e no Glama se existe MCP comunitário do VOSviewer. A busca feita não foi exaustiva | Erick ou pesquisa na Arquitetura |
| 2 | Forkar ou contribuir com um MCP acadêmico que já existe, ou começar do zero | Decisão de Arquitetura |
| 3 | Configurar o Langfuse para os agentes do Gemini e do Claude Code | Erick |
| 4 | O que a LGPD exige para guardar nomes e ORCID de autores numa ferramenta local (T-007) | Erick |
| 5 | Quanto custa trazer referências e citações dentro das cotas das APIs (T-005) | Arquitetura |
