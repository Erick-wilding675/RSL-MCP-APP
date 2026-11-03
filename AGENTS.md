<!-- blueprint:start -->
## Blueprint

RSL.app é um servidor MCP em Python, gratuito e self-hosted, que deixa a IA do pesquisador buscar artigos no OpenAlex, na Crossref e na Semantic Scholar e exportar listas com metadados, autores, referências e citações para ferramentas de revisão sistemática, a começar pelo VOSviewer.

| O quê | Onde |
|---|---|
| Os documentos | `docs/` |
| O plano, e uma spec por tarefa | `docs/plan.md`, `docs/specs/` |
| Onde o projeto está, para qualquer sessão | `.blueprint/state.md` |
| As decisões, cada uma com o motivo | `docs/decisions.md` |
| O que falta conferir | `docs/test-plan.md` |
| Por que uma linha de código é do jeito que é | Pergunte: a skill `blueprint-explain` responde a partir do código |
| O diário: um registro por sessão e os marcos | `.blueprint/journal/` |

### Como trabalhar aqui

1. **Leia `.blueprint/state.md` antes de responder.** Ele diz onde o projeto está. Nunca aja como se lembrasse de uma conversa: pode ter sido outra sessão, outro dia ou outro agente.
2. **Uma tarefa por vez, a do plano, na ordem.** A spec da tarefa diz o que ela faz, o que não faz e quando está pronta. **Diga em qual tarefa você está, pelo número e pelo nome, antes de começar**: a pessoa precisa saber qual você escolheu sem reler o plano.
3. **Toda entrega diz como testar e onde olhar primeiro:** o que rodar ou abrir, o que deve aparecer, e os dois ou três pontos mais arriscados do que mudou, o mais difícil primeiro. Isso vai nas seções "Resultado da entrega" e "Como testar" da spec e no que você conta à pessoa. Risco não é tamanho: o que mexe com chaves de API, dados pessoais de autores, gravação de arquivos e exportações vem antes do que é longo.
4. **O código leva o id do que ele serve.** Um requisito que virou código ganha o id (FR-04, NFR-03, D-007) num comentário onde aquele comportamento começa, e no nome do teste que o prova. Essa linha é o que deixa qualquer pessoa perguntar "por que é assim?" e ser respondida pelo código. Nem todo arquivo precisa de um. Um id que nenhum documento tem é um erro a relatar, não a manter.
5. **Entregue em partes que dê para revisar.** Um commit por requisito. Cerca de 400 linhas mudadas ou 10 arquivos é o que uma pessoa revisa de uma vez, arquivos novos incluídos; acima disso, divida a entrega e diga como dividiu.
6. **Registre o que aconteceu.** No fim de uma sessão, um registro em `.blueprint/journal/sessions/`. Uma decisão cara de desfazer vai para `docs/decisions.md`, com o motivo, quem decidiu e a data. Uma fase entregue vai para os marcos. A memória do projeto fica no Lore (`.ai-memory.toml`): grave nela seguindo as instruções da própria ferramenta.
7. **Uma mudança que o plano não cobre.** Se for pequena, faça e diga em uma linha o que fez. Pequena é: mexe numa parte do código, não traz decisão cara de desfazer, não traz fato novo sobre o projeto (a primeira tela, o primeiro dado guardado, o primeiro dado pessoal, o primeiro comando, a primeira chamada a um modelo) e cabe numa tarefa. Se não for pequena, escreva a spec com a pessoa antes de escrever código.
8. **Uma decisão cara de desfazer é da pessoa:** a pilha, a hospedagem, o tratamento de dados pessoais, qualquer coisa que gere custo. Traga opções e uma recomendação, e espere.
9. **Nunca escreva uma chave, um token ou uma senha** num arquivo deste projeto.

### Regras deste projeto

- **Quem faz o quê:** o Claude (desktop ou Claude Code, é o mesmo papel) planeja, escreve e revê documentos e specs, revisa o código e orquestra com o Playmaker. O Gemini, pelo Antigravity CLI (`agy`), escreve o código de cada tarefa, com o Gemini 4 Argon ou, se o limite dele acabar, o Gemini 3.8 Flash. O Erick testa e marca como pronta. Quem codifica não muda uma spec sozinho: se a spec está errada ou incompleta, registre e devolva ao Claude para atualizar.
- **Antes de usar uma API ou uma biblioteca nova:** leia a página oficial por inteiro (T-001, T-009). O que for dito de memória ou lido só num resultado de busca não vale como fato.
- **O servidor usa o SDK oficial `mcp>=2,<3`.** A maior parte dos exemplos que os modelos conhecem é da versão 1 (`from mcp.server.fastmcp import FastMCP`). Confira o nome da classe e o import na documentação da versão 2 antes de escrever (T-009).
- **Fora da primeira versão:** app desktop, juntar buscas, abrir o VOSviewer, Scopus, Web of Science e CAPES, texto completo. O Sci-Hub está fora do projeto.
- **Dados pessoais:** nomes, ORCID e afiliações de autores são guardados por decisão do Erick (D-004), só na máquina de quem usa. Nunca vão para o log de ferramentas de observabilidade nem para fora da pasta de dados.
- **Idioma:** documentos e mensagens em português do Brasil; nomes de código, ferramentas e campos em inglês, como no contrato (`docs/interface-contract.md`). Os nomes das ferramentas, das entradas, dos campos de resposta e dos códigos de erro não mudam sem aviso.

### O método

Os documentos e o plano deste projeto foram escritos com o Blueprint, e as regras acima vêm dele. Este arquivo, os documentos e o plano bastam para continuar.
<!-- blueprint:end -->
