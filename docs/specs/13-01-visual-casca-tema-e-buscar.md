# Visual novo: casca, tema e tela Buscar (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** a fazer

## O que faz

Dá ao app desktop um visual moderno e amigável (D-031). Esta tarefa monta três coisas que as outras telas vão usar: a casca, o tema e as peças comuns. Depois refaz a tela Buscar com elas. Nada muda no que as telas fazem.

### 1. Tema: cores, letra e modo escuro

- Num módulo novo, `src/rslapp/desktop/theme.py`, uma função `apply_theme()` que toda página chama no começo. Ela faz quatro coisas.
- **Cores** (`ui.colors`):

  | Papel | Claro | Escuro |
  |---|---|---|
  | `primary` (ações) | `#4F46E5` | `#818CF8` |
  | `secondary` | `#0F766E` | `#2DD4BF` |
  | `accent` | `#0D9488` | `#5EEAD4` |
  | `positive` | `#15803D` | `#4ADE80` |
  | `negative` | `#B91C1C` | `#F87171` |
  | `warning` | `#B45309` | `#FBBF24` |
  | `info` | `#1D4ED8` | `#60A5FA` |
  | `dark_page` | — | `#0B1020` |
  | `dark` | — | `#121933` |

  Fundo da página no claro: `#F6F7FB`. Os cartões ficam brancos no claro e `#121933` no escuro.
- **Letra:** pilha do sistema, sem baixar fonte:

  ```
  "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, "Ubuntu", "Cantarell", "Noto Sans", sans-serif
  ```

  Tamanho base de 15px. Títulos de página com 24px e peso 600.
- **Modo escuro:** `ui.dark_mode`.
  - O padrão é `None`, que segue o sistema.
  - A escolha da pessoa fica num campo novo, `theme`, do `desktop.json` (`"auto"`, `"light"` ou `"dark"`; o valor que falta vale `"auto"`), por `settings.py`, como os outros campos.
  - Nunca vai para a pasta de dados nem para o log.
- **CSS comum** por `ui.add_css`, num só lugar: cantos arredondados de 12px nos cartões, borda fina (`1px`, cinza claro no claro, `#1F2A4D` no escuro), sombra leve, foco visível (contorno de 2px na cor `primary`) em todo elemento que recebe teclado, e transições curtas (150 ms). Nada de animação longa.
- Leia antes a página oficial do NiceGUI sobre estilo (`ui.colors`, `ui.dark_mode`, `ui.add_css`, camadas de CSS) e a do `ui.left_drawer`, na versão 4 instalada (T-001, T-009).

### 2. Casca: navegação lateral e barra de cima

Troca o `render_header()` de `pages/__init__.py` por uma `render_shell(title, subtitle)`. Toda página passa a chamá-la.

- **Navegação lateral** (`ui.left_drawer`), sempre aberta em janela de 1000px de largura ou mais. Abaixo disso, ela recolhe para só os ícones.
  - **No topo:** o nome "RSL.app" e, embaixo, em letra menor, "Revisão sistemática com IA rastreável".
  - **Os itens, nesta ordem, com ícone Material e nome:** Buscar (`search`), Histórico (`history`), Conectar IA (`hub`), Configurações (`settings`).
  - **Item ativo:** fundo na cor `primary` com transparência, texto e ícone em `primary`.
  - **No pé:** a versão do app (`rslapp.__version__`) e o botão de tema, que alterna claro, escuro e automático. O botão tem ícone e dica (tooltip) dizendo o tema atual. A escolha grava no `desktop.json`.
- **Barra de cima** da área de conteúdo: o título da página (`title`) e, embaixo, o subtítulo (`subtitle`), em cinza. Os textos que hoje são subtítulos das telas passam para cá, **iguais**.
- **Área de conteúdo:** largura máxima de 1100px, centralizada, com margem de 24px.

### 3. Peças comuns

Em `src/rslapp/desktop/components.py`:

- `section_card(title, icon=None, description=None)`: um cartão com cabeçalho. É usado como `with`.
- `empty_state(icon, title, text, action_label=None, action_target=None)`: um ícone grande e suave, o título, uma frase de orientação e um botão para o próximo passo.
- `status_badge(text, kind)`: um selo pequeno, com `kind` em `ok`, `warning`, `error`, `info` ou `neutral`.
- `copy_block(text, mark=None)`: um bloco de código em monoespaçado com botão "Copiar". Substitui os blocos que a tela Conectar IA monta à mão; a troca nela é na 13-03.

### 4. Tela Buscar refeita

Mesmo comportamento e mesmos campos, nesta disposição:

- **Cartão "String de busca":** a caixa de texto grande (4 linhas, cresce até 10). Embaixo, a dica atual ("A string vai como está...") e a dica nova "Ctrl+Enter para buscar". **Ctrl+Enter** na caixa dispara a busca.
- **Cartão "Fontes":** cada fonte vira um cartão pequeno de escolha (chip grande) em grade de 2 ou 3 colunas, com o nome da fonte e uma linha de descrição:
  - OpenAlex: "ampla, todas as áreas";
  - Crossref: "metadados dos DOIs";
  - Semantic Scholar: "citações e áreas de computação e saúde";
  - Europe PMC e PubMed: "saúde e ciências da vida", a nota que já existe;
  - Scopus e Web of Science sem chave: "configure a chave em Configurações", com o link, e o cartão desabilitado como hoje.
- **Cartão "Opções":** "Quantidade" e "Incluir pareceres de revisão por pares", lado a lado.
- **Botão "Buscar":** grande, na cor `primary`, com ícone, alinhado à direita.
- **Durante a busca:** o cartão de progresso mostra o texto atual e uma barra de progresso indeterminada, no lugar do spinner sozinho.
- **Os `mark()`** (`query-input`, `source-*`, `max-results`, `include-peer-review`, `search-button`) continuam nos mesmos elementos.

## O que não faz

- Não muda o que nenhuma tela faz, nem os textos que os testes conferem.
- Não refaz Lista, Histórico, Configurações e Conectar IA (13-02 e 13-03). Elas só passam a usar `apply_theme()` e `render_shell()`, com o título e o subtítulo de hoje, para o app não ficar com dois visuais.
- Não baixa fonte nem nada da internet. O app continua funcionando sem rede para abrir.
- Não usa logotipo de terceiros (OpenAlex, Claude, Cursor etc.). Só ícones genéricos.

## Para instituições

Nada muda para quem hospeda: o visual é do app desktop. O guia (`docs/hospedagem.md`, "Distribuir o app aos pesquisadores") ganha uma linha: o app segue o tema claro ou escuro do sistema, e o pesquisador troca no pé da navegação.

## Pronto quando

- [ ] `apply_theme()` e `render_shell()` em todas as cinco telas, com a navegação lateral e o item ativo marcado
- [ ] O tema segue o sistema, e a troca grava `theme` no `desktop.json`, com teste
- [ ] As quatro peças comuns existem, com teste de que montam sem erro
- [ ] A tela Buscar no novo arranjo, com Ctrl+Enter, com teste
- [ ] Os testes de `tests_desktop` que já existiam passam sem mudar o que conferem
- [ ] Os gates passam: `tests_desktop`, a suíte principal em 3.10 e 3.14, e o ruff

## Vem de

D-024, D-025, D-031, FR-16; teste do Erick em 2026-11-16.

## Antes de começar

- Leia `src/rslapp/desktop/pages/`, `src/rslapp/desktop/settings.py` e `tests_desktop/`.
- Um commit por item.

## Resultado da entrega

(a preencher)

## Como testar

**Onde olhar primeiro:**

1. `settings.py`: o campo `theme` novo não pode apagar nem misturar as chaves já salvas no `desktop.json`.
2. A tela Buscar: o Ctrl+Enter não pode disparar duas buscas, e as fontes pagas sem chave continuam bloqueadas.

**Para conferir (Erick):**

- Abra o app com o Windows no tema claro e depois no escuro: ele acompanha. Troque pelo botão no pé da navegação, feche e abra de novo: a escolha ficou.
- Na tela Buscar, escreva uma string e aperte Ctrl+Enter: a busca roda e abre a lista.
