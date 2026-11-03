# Classificação de dados

**Projeto:** RSL.app · **Versão:** 0.1 · **Data:** 2026-11-02

> **Em resumo:** O sistema guarda dados públicos dos autores dos artigos: nome, ORCID, identificadores nas fontes e afiliações.
> Todos entram porque ligam os registros entre si e formam os nós das redes. Ficam só na máquina de quem usa. O projeto não tem servidor e não coleta nada direto das pessoas.
> A lei de proteção de dados ainda não foi conferida para este caso.

## De quem são os dados

| De quem | O que é guardado | Por que é necessário | Por quanto tempo |
|---|---|---|---|
| Autores dos artigos | Nome, ORCID, identificadores do autor em cada fonte e afiliações | Ligar os registros entre fontes e formar os nós das redes (decisão do Erick, D-004) | Até o usuário apagar. O log e as listas não expiram sozinhos |
| O próprio pesquisador | O texto livre do pedido, resumido pela IA, dentro do log | Deixar o log interpretável (FR-13) | Igual ao log |

## Quão sensível é cada um

| O que é guardado | Sensibilidade | O que isso significa aqui |
|---|---|---|
| Nome, ORCID, identificadores e afiliações dos autores | comum | São dados públicos de publicações, vindos das APIs abertas. Não há cuidado extra além de ficarem só na máquina do usuário |
| Texto do pedido do pesquisador | comum | Pode ter qualquer texto livre. Fica só na máquina do usuário |

Nenhum campo é sensível no sentido de saúde, raça, religião, política, sindicato, vida sexual, biometria ou dado de criança.

## Quem pode ver

| Quem | O que vê | Como entra |
|---|---|---|
| O usuário e quem usa a máquina dele | Tudo | Pelo acesso que já tem à máquina e à pasta de dados |
| A IA conectada ao servidor | O que as respostas mostram. Por padrão, um resumo com os nomes dos autores | Pelo cliente MCP que o usuário escolheu. O provedor da IA trata isso como o resto da conversa |

## O que o projeto faz a respeito

- **Coleta:** só nas APIs abertas, quando o usuário faz uma busca. Não há coleta direta das pessoas, e nada é enviado para um servidor do projeto.
- **Apagar:** como tudo fica em arquivos numa pasta de dados (D-007), o usuário apaga os arquivos que quiser na própria máquina. O sistema não reescreve nem apaga entradas do log.
- **Pedido de uma pessoa:** quem pedir para ter os dados corrigidos ou apagados deve falar com a fonte (OpenAlex, Crossref, Semantic Scholar). O projeto não guarda dados fora da máquina de cada usuário.
- **Vazamento:** não há servidor do projeto que possa vazar. O risco é o da máquina do usuário.

## A lei

A LGPD é a lei do país do Erick. Não conferi o que ela exige de um software que cada pessoa roda na própria máquina e que guarda nomes e ORCID públicos de autores. Isso está no plano de testes (T-007).

## Pontos em aberto

- O que a LGPD exige neste caso (T-007). Depende do Erick.
- Se o usuário precisa de um meio fácil de apagar os dados guardados. Depende do Erick.
