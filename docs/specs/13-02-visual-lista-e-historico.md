# Visual novo: Lista e Histórico (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** a fazer

## O que faz

Refaz as telas Lista e Histórico com o tema, a casca e as peças da 13-01 (D-031). Nada muda no que cada tela faz.

### 1. Tela Lista

- **Faixa de resumo** no topo, com quatro números grandes em cartões pequenos:
  - total de artigos;
  - fontes consultadas;
  - quantos repetidos foram removidos, se o núcleo já devolve esse número (se não devolve, este cartão não aparece; não calcule na tela);
  - data da busca.
- **Cartão "Busca":** a string em monoespaçado, com botão "Copiar" (`copy_block`), o identificador da lista e uma linha por fonte com `status_badge`:
  - `ok` com o número de resultados;
  - `warning` quando a fonte saiu incompleta, com o motivo.
- **Aviso de lista incompleta:** fica no topo, com a cor `warning`, ícone e o texto de hoje. Mantém o `mark("incomplete-warning")`.
- **Cartão "Exportar":** os botões de formato lado a lado, cada um com ícone. "Abrir pasta" fica como botão secundário. Depois de exportar, o aviso mostra o caminho e um botão "Abrir pasta".
- **Tabela:**
  - cabeçalho fixo;
  - linhas alternadas suaves;
  - o título em negrito e, embaixo, os autores em cinza;
  - o DOI como link;
  - a fonte como `status_badge` `neutral`;
  - paginação de 25 por página;
  - o filtro (`table-filter`) acima, com ícone de lupa e o texto de dica "Filtrar por título, autor ou DOI".
- **Lista não encontrada:** `empty_state` com o texto de hoje e o botão "Voltar para Buscar" (`back-to-search`).

### 2. Tela Histórico

- O botão "Abrir log" (`open-log-button` ou o `mark` atual) fica à direita da barra de cima.
- **Tabela:**
  - a data em formato curto ("16/11/2026 14:25");
  - a string cortada como hoje, com a string inteira numa dica (tooltip);
  - as fontes como selos;
  - o total;
  - as ações "Ver lista" e "Repetir" como botões com ícone (`visibility` e `replay`) e dica. Mantém os `mark()` de hoje.
- **Repetir:** enquanto repete, a linha mostra uma barra de progresso indeterminada, no lugar do texto solto.
- **Histórico vazio:** `empty_state` com ícone `history`, o texto de hoje ("Histórico vazio: nenhuma busca ainda.", `empty-history`) e o botão "Ir para Buscar" (`go-to-search`).
- A lentidão com centenas de buscas (dívida da 11-03) **não** é desta tarefa. A paginação de 25 por página entra aqui só como visual.

## O que não faz

- Não muda o núcleo, a exportação, o log nem a repetição.
- Não muda os textos que os testes conferem nem os `mark()`.
- Não acrescenta colunas novas de dados.

## Para instituições

Nada muda para quem hospeda.

## Pronto quando

- [ ] Lista com resumo, cartões, tabela paginada e estados de erro e vazio, com teste
- [ ] Histórico com tabela nova, ações com ícone e estado vazio, com teste
- [ ] Os testes de `tests_desktop` que já existiam passam sem mudar o que conferem
- [ ] Os gates passam

## Vem de

D-025, D-031, FR-16, FR-17, FR-18.

## Antes de começar

- A 13-01 integrada.
- Um commit por tela.
- **Modo escuro:** não use as variantes `dark:` do Tailwind. Elas não reagem ao modo escuro do NiceGUI, que só põe `body--dark` no `<body>`, e foi isso que quebrou a primeira entrega da 13-01. Use as classes do `theme.py` (`rsl-title`, `rsl-muted`, `rsl-surface-2`, `rsl-surface-disabled`, `rsl-code`) ou crie outras nele, com a cor do claro e a do escuro (`body.body--dark`).

## Resultado da entrega

(a preencher)

## Como testar

**Onde olhar primeiro:**

1. A exportação na Lista: o botão e o aviso mudaram de lugar, mas o arquivo gerado é o mesmo.
2. O "Repetir" no Histórico: abre a lista nova, como antes.

**Para conferir (Erick):**

- Abra uma lista grande, filtre por um autor, mude de página e exporte para o VOSviewer.
