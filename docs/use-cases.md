# Casos de uso

**Projeto:** RSL.app · **Versão:** 0.2 · **Data:** 2026-11-02

> **Em resumo:** O pesquisador usa o servidor por meio da IA dele. Quatro jornadas não podem dar errado: buscar por tema e exportar para o VOSviewer, achar um artigo específico e exportar, repetir uma busca a partir do log, e seguir as referências e as citações de um artigo.
> Cada pedido gera uma lista própria. Se uma fonte falha, as outras seguem e a lista sai marcada como incompleta.

## Quem usa

| Quem | O que vem fazer |
|---|---|
| Pesquisador (o Erick, o doutorando e quem mais quiser) | Pedir em linguagem natural, receber listas de artigos e exportá-las para a ferramenta de revisão |
| A IA do pesquisador (cliente MCP) | Planejar o pedido, chamar o servidor e entregar cada lista separada |

## As jornadas

| Nº | Jornada | Quem | Não pode dar errado |
|---|---|---|---|
| UC-01 | Buscar por tema e exportar para o VOSviewer | Pesquisador | sim |
| UC-02 | Achar um artigo específico e exportar | Pesquisador | sim |
| UC-03 | Repetir uma busca a partir do log | Pesquisador | sim |
| UC-04 | Seguir as referências e as citações de um artigo | Pesquisador | sim |

## UC-01 · Buscar por tema e exportar para o VOSviewer

**Começa quando:** o pesquisador pede, na IA conectada ao servidor, um tema ou assunto.
**Precisa de:** o servidor configurado e conectado à IA, com ao menos uma fonte disponível (FR-07).

1. O pesquisador descreve o que procura, em linguagem natural.
2. A IA planeja antes de buscar. Se o pedido tem assuntos que é melhor buscar e entregar separadamente, ela o divide em várias buscas. Cada busca terá a própria lista (FR-09, FR-10).
3. Para cada busca, a IA converte o pedido em termos técnicos e chama a ferramenta de busca do servidor (FR-01).
4. O servidor consulta OpenAlex, Crossref e Semantic Scholar, tira as duplicatas dentro daquela lista (FR-04) e registra a busca no log (FR-05).
5. A IA mostra cada lista separada, com os metadados (FR-03), e diz qual fonte falhou, se alguma (FR-08).
6. O pesquisador pede para exportar a lista que quiser, agora ou depois, porque as listas ficam salvas (FR-12). O servidor entrega RIS, CSV, lista de DOIs ou a URL da consulta do OpenAlex (FR-06).
7. O pesquisador abre o arquivo no VOSviewer, fora do servidor.

**Termina com:** uma lista sem duplicatas para cada busca, registrada no log, e um arquivo que o VOSviewer abre sem edição manual.

**Quando não dá certo**

| O que acontece | O que o sistema faz |
|---|---|
| Uma fonte falha ou atinge o limite | Segue com as outras. A lista sai marcada como incompleta, com a fonte e o motivo, e isso vai para o log (FR-08) |
| Nenhuma fonte está disponível, por exemplo sem chave configurada (deduzido) | Não devolve lista. Diz à IA o que falta configurar (FR-07) |
| A busca não acha nada (deduzido) | Devolve a lista vazia, registrada no log com 0 resultados (FR-05) |

## UC-02 · Achar um artigo específico e exportar

**Começa quando:** o pesquisador dá o título, ou o DOI, de um artigo.
**Precisa de:** o mesmo que UC-01.

1. O pesquisador informa o título ou o DOI.
2. A IA chama a ferramenta que busca um artigo específico (FR-02).
3. O servidor consulta as fontes, devolve o artigo com os metadados e registra a busca no log (FR-03, FR-05).
4. O pesquisador confere se é o artigo certo.
5. O pesquisador pede a exportação (FR-06).

**Termina com:** o artigo com seus metadados e um arquivo exportado.

**Quando não dá certo**

| O que acontece | O que o sistema faz |
|---|---|
| Não acha o artigo | Devolve a lista vazia, registrada no log (FR-05) |
| Acha vários artigos parecidos (deduzido) | Devolve os candidatos, e a IA pede ao pesquisador que escolha |
| Uma fonte falha | Segue com as outras e marca a falha (FR-08) |

## UC-03 · Repetir uma busca a partir do log

**Começa quando:** o pesquisador quer refazer uma busca já feita, por exemplo para atualizar a revisão meses depois.
**Precisa de:** a busca estar no log (FR-05).

1. O pesquisador diz qual busca quer repetir.
2. A IA localiza a busca no log.
3. O servidor repete a busca com as mesmas strings e as mesmas bases (FR-11).
4. O servidor registra uma nova entrada no log e não mexe na antiga (deduzido).
5. A IA mostra a nova lista, separada da anterior (FR-09).

**Termina com:** uma nova lista e uma nova entrada no log, com a busca original intacta.

**Quando não dá certo**

| O que acontece | O que o sistema faz |
|---|---|
| Os resultados diferem dos da busca original, porque as bases mudam (deduzido) | Mostra o número novo, e o original continua no log para comparação |
| Uma base usada antes está indisponível ou sem chave | Segue com as outras e marca a falha (FR-08) |

## UC-04 · Seguir as referências e as citações de um artigo

**Começa quando:** o pesquisador quer ver o que um artigo cita, ou quem o cita, por exemplo para ampliar a revisão ou montar um mapa de citações.
**Precisa de:** o artigo estar numa lista salva, ou o pesquisador dar o DOI (FR-15).

1. O pesquisador indica o artigo e se quer as referências (o que ele cita) ou as citações (quem o cita).
2. A IA chama a ferramenta de trabalhos relacionados do servidor (FR-15).
3. O servidor consulta as fontes que entregam esse dado, tira as duplicatas e registra a busca no log, com o artigo de origem e a direção (FR-04, FR-05).
4. A IA mostra a lista nova, separada das outras, e diz qual fonte não entrega esse dado ou falhou (FR-08, FR-09).
5. O pesquisador exporta a lista como qualquer outra (FR-06, FR-12).

**Termina com:** uma lista própria de referências ou de citações, ligada ao artigo de origem no log.

**Quando não dá certo**

| O que acontece | O que o sistema faz |
|---|---|
| O artigo tem mais citações do que a fonte deixa trazer (a Semantic Scholar corta em 10 mil) | Traz até o limite, marca a lista como incompleta e diz o motivo no log (FR-08) |
| Nenhuma fonte entrega o dado para esse artigo | Devolve a lista vazia, com `not_supported` no log (FR-14) |
| O artigo de origem não é achado | Diz que o artigo não foi achado e não cria lista |
| A cota de uma fonte acaba no meio | Segue com as outras e marca a falha (FR-08) |

## O que fica de fora

- Juntar várias buscas numa lista só. O Erick decidiu em 2026-11-02 que as listas ficam separadas por pedido.
- Abrir o VOSviewer na máquina do usuário. O servidor só entrega o arquivo ou a URL.
- Texto completo e a interface do app desktop. Esperam as próximas versões.
