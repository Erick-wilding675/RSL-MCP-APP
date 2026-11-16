# Visual novo: Configurações e Conectar IA (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** integrada (2026-11-16)

## O que faz

Refaz as telas Configurações e Conectar IA com o tema, a casca e as peças da 13-01 (D-031). Nada muda no que cada tela faz. Esta tarefa toca as telas que mexem com **chaves de API** e com o **arquivo de configuração do Claude**.

### 1. Configurações

- **Três `section_card`:**
  - "Chaves de API" (ícone `key`);
  - "E-mail de contato" (ícone `mail`);
  - "Pastas" (ícone `folder`).
- **Cada chave:**
  - o nome da base;
  - um `status_badge`: `ok` "configurada", `neutral` "não configurada" ou `warning` quando é paga e falta;
  - o campo com o botão de olho para mostrar ou esconder (Quasar `password` com `toggle`). O campo começa **vazio** e escondido, como hoje: a tela nunca mostra a chave salva;
  - "Onde criar" como link com ícone `open_in_new`;
  - "Remover" como botão discreto.
- **Pastas:** cada campo com um botão de ícone que abre a pasta no gerenciador de arquivos, se ela existir. O aviso da pasta de dados (`DATA_DIR_WARNING`) vira um selo `warning` com o texto atual.
- **Salvar:** uma barra fixa no pé da tela, com o botão "Salvar" (`primary`) e o retorno de hoje (`save-feedback`). A barra aparece destacada quando há mudança não salva.
- **Mantém** todos os `mark()` de hoje (`input-*`, `status-*`, `remove-*`, `link-*`, `paid-note-*`).

### 2. Conectar IA

- **Grade de cartões**, dois por linha em janela larga, um em janela estreita. Cada cartão tem ícone genérico (sem logotipo de terceiros), nome e uma frase do que faz.
- **Claude Desktop:**
  - o estado como `status_badge`: `ok` "conectado", `warning` "conectado a outra instalação" ou `neutral` "não conectado";
  - o caminho do arquivo em letra pequena;
  - os botões "Conectar" e "Desconectar";
  - a confirmação (o trecho que vai ser gravado) num diálogo (`ui.dialog`), com o trecho em `copy_block`, o aviso de substituição e os botões "Confirmar" e "Cancelar". Os `mark()` passam para dentro do diálogo, com os mesmos nomes.
- **Cursor:** o botão "Instalar no Cursor".
- **VS Code, Claude Code e JSON genérico:** cada comando ou trecho em `copy_block`. Mantém o aviso do Prompt de Comando no Windows (12-05).
- **No topo:** o subtítulo de hoje (`connect-subtitle`) e uma faixa `info` curta: "As buscas que a IA fizer aparecem no Histórico deste app."

## O que não faz

- Não muda `connect.py` nem `settings.py`: o que se grava e onde fica igual.
- Não mostra nenhuma chave salva, nem parcialmente.
- Não muda os textos que os testes conferem nem os `mark()`.

## Para instituições

Nada muda para quem hospeda.

## Pronto quando

- [x] Configurações com os três cartões, olho nas chaves, barra de salvar, com teste de que nenhuma chave salva aparece na página
- [x] Conectar IA em grade, com a confirmação do Claude Desktop em diálogo, com teste
- [x] Os testes de `tests_desktop` que já existiam passam sem mudar o que conferem
- [x] Os gates passam

## Vem de

D-026, D-028, D-031, FR-19.

## Antes de começar

- A 13-01 integrada.
- Um commit por tela.
- **Modo escuro:** não use as variantes `dark:` do Tailwind. Elas não reagem ao modo escuro do NiceGUI, que só põe `body--dark` no `<body>`, e foi isso que quebrou a primeira entrega da 13-01. Use as classes do `theme.py` (`rsl-title`, `rsl-muted`, `rsl-surface-2`, `rsl-surface-disabled`, `rsl-code`) ou crie outras nele, com a cor do claro e a do escuro (`body.body--dark`).

## Resultado da entrega

Entregue em dois commits, um por tela, preservando todos os marcadores (`mark()`), textos esperados e comportamento de segurança dos segredos:
1. `d2b8985` (`feat(desktop): tela Configuracoes refeita com novo tema e componentes (D-031, FR-18)`):
   - Três `section_card` ("Chaves de API", "E-mail de contato", "Pastas") com ícones e descrições semânticas.
   - Cada chave com campo Quasar de senha e toggle de visualização, iniciando vazio e oculto; badges semânticos de situação (`status_badge` com `ok`, `warning` quando paga e não configurada, `info` quando definida no sistema, `neutral`), link com `open_in_new` e botão de remoção discreto.
   - Campos de pastas locais com botão de ícone `folder_open` para abrir a pasta no gerenciador de arquivos nativo (`open_folder` compatível com Windows e Linux) e caixa de aviso em `rsl-warning-box` (`DATA_DIR_WARNING`).
   - Barra fixa no rodapé (`save-bar`) destacada dinamicamente (`save-bar-dirty` com badge "Alterações não salvas") ao modificar campos, botão Salvar com feedback persistente (`save-feedback`).
   - Teste `test_d031_fr18_configuracoes_novos_componentes_e_abrir_pasta` em `tests_desktop/test_history_and_settings.py` conferindo o comportamento e a ausência total de segredos no HTML/props da página.
2. `1365a64` (`feat(desktop): tela Conectar IA refeita com grade, diálogo de confirmação e tema (D-031, FR-19)`):
   - Subtítulo com marker `connect-subtitle` e faixa de informação contextual em `rsl-info-box`.
   - Grade responsiva de 6 cartões (2 por linha em desktop largo, 1 em telas estreitas) com ícones genéricos e descrições padronizadas (`card-claude-desktop`, `card-cursor`, `card-vscode`, `card-claude-code`, `card-other-ais`, `card-chatgpt`).
   - Claude Desktop com `status_badge` semântico, caminho do arquivo de configuração e diálogo de confirmação modal (`ui.dialog`) contendo snippet monoespaçado, aviso de substituição de entradas anteriores e botões de ação ("Confirmar" e "Cancelar").
   - Comandos do VS Code, Claude Code e JSON genérico encapsulados em `copy_block` com botões de cópia e cópia rápida para clipboard.
   - Teste `test_d031_fr19_conectar_grade_e_cancelar_dialogo` em `tests_desktop/test_connect_page.py`.

## Como testar

**Onde olhar primeiro:**

1. Configurações: salve uma chave, saia e volte. O campo volta vazio, o selo diz "configurada", e a chave não está no HTML da página.
2. Conectar IA: o diálogo de confirmação do Claude Desktop grava só depois de "Confirmar", e "Cancelar" não grava nada.

**Para conferir (Erick):**

- Conecte e desconecte o Claude Desktop pelo diálogo, e copie o comando do VS Code.
