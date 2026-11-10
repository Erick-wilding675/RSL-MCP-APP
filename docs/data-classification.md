# Classificação de dados

**Projeto:** RSL.app · **Versão:** 0.1 · **Data:** 2026-11-02

> **Em resumo:** O sistema guarda dados públicos dos autores dos artigos: nome, ORCID, identificadores nas fontes e afiliações.
> Todos entram porque ligam os registros entre si e formam os nós das redes. Ficam só na máquina de quem usa. O projeto não tem servidor e não coleta nada direto das pessoas.
> A partir da v2 (fase 8), quem quiser pode hospedar um servidor para outras pessoas: aí os dados ficam no servidor de quem hospeda, e o servidor passa a guardar também quem usa (D-012, D-016).
> A lei de proteção de dados ainda não foi conferida para este caso.

## De quem são os dados

| De quem | O que é guardado | Por que é necessário | Por quanto tempo |
|---|---|---|---|
| Autores dos artigos | Nome, ORCID, identificadores do autor em cada fonte e afiliações | Ligar os registros entre fontes e formar os nós das redes (decisão do Erick, D-004) | Até o usuário apagar. O log e as listas não expiram sozinhos |
| O próprio pesquisador | O texto livre do pedido, resumido pela IA, dentro do log | Deixar o log interpretável (FR-13) | Igual ao log |
| Quem usa um servidor hospedado (v2) | O identificador escolhido por quem hospeda (pode ser o nome da pessoa), o hash do código pessoal, as datas de cadastro e revogação, os clientes OAuth registrados e os hashes dos tokens. O IP fica só na memória, para limitar tentativas de login | Fazer login e separar os dados de cada pessoa (D-012, D-015, D-016) | Até quem hospeda apagar a pessoa (`user purge`). Revogar não apaga |

## Quão sensível é cada um

| O que é guardado | Sensibilidade | O que isso significa aqui |
|---|---|---|
| Nome, ORCID, identificadores e afiliações dos autores | comum | São dados públicos de publicações, vindos das APIs abertas. Não há cuidado extra além de ficarem só na máquina do usuário |
| Texto do pedido do pesquisador | comum | Pode ter qualquer texto livre. Fica só na máquina do usuário, ou no servidor de quem hospeda, na v2 |
| Identificador e código de quem usa um servidor hospedado | comum, e o código é uma credencial | O código nunca é guardado em texto, só o hash, e nunca vai para log nem para resposta |

Nenhum campo é sensível no sentido de saúde, raça, religião, política, sindicato, vida sexual, biometria ou dado de criança.

## Quem pode ver

| Quem | O que vê | Como entra |
|---|---|---|
| O usuário e quem usa a máquina dele | Tudo | Pelo acesso que já tem à máquina e à pasta de dados |
| A IA conectada ao servidor | O que as respostas mostram. Por padrão, um resumo com os nomes dos autores | Pelo cliente MCP que o usuário escolheu. O provedor da IA trata isso como o resto da conversa |
| Quem hospeda um servidor (v2) | Tudo o que as pessoas do servidor buscam e guardam, e o cadastro delas | Pelo acesso à máquina e ao volume de dados |
| As outras pessoas do mesmo servidor (v2) | Nada das outras: cada uma vê só as próprias listas, log e exportações (D-012) | Pelo login com o próprio código |

## O que o projeto faz a respeito

- **Coleta:** só nas APIs abertas, quando o usuário faz uma busca. Não há coleta direta das pessoas, e nada é enviado para um servidor do projeto.
- **Apagar:** como tudo fica em arquivos numa pasta de dados (D-007), o usuário apaga os arquivos que quiser na própria máquina. O sistema não reescreve nem apaga entradas do log.
- **Pedido de uma pessoa:** quem pedir para ter os dados corrigidos ou apagados deve falar com a fonte (OpenAlex, Crossref, Semantic Scholar). O projeto não guarda dados fora da máquina de cada usuário.
- **Vazamento:** não há servidor do projeto que possa vazar. O risco é o da máquina do usuário, ou o do servidor de quem hospeda, na v2.
- **Servidor hospedado (v2):** quem hospeda passa a tratar os dados das pessoas do servidor. O guia de hospedagem avisa isso e mostra o `user purge`, que apaga os dados de uma pessoa (D-018). Códigos e tokens ficam só como hash. O link de download é assinado e vence em 1 hora (D-014).

## A lei

A LGPD é a lei do país do Erick. Não conferi o que ela exige de um software que cada pessoa roda na própria máquina e que guarda nomes e ORCID públicos de autores. Isso está no plano de testes (T-007).

## Pontos em aberto

- O que a LGPD exige neste caso (T-007). Depende do Erick.
- Se o usuário precisa de um meio fácil de apagar os dados guardados. No stdio, depende do Erick. No servidor hospedado, existe o `user purge` (D-016).
- O que a LGPD exige de quem hospeda um servidor para outras pessoas (T-007). Precisa ser conferido antes de anunciar o modo hospedado (D-018).
