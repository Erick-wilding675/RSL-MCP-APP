# Visual novo: Configurações e Conectar IA (2.2)

**Fase:** 13 · 2.2: visual novo e ganhos rápidos · **Situação:** a fazer

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

- [ ] Configurações com os três cartões, olho nas chaves, barra de salvar, com teste de que nenhuma chave salva aparece na página
- [ ] Conectar IA em grade, com a confirmação do Claude Desktop em diálogo, com teste
- [ ] Os testes de `tests_desktop` que já existiam passam sem mudar o que conferem
- [ ] Os gates passam

## Vem de

D-026, D-028, D-031, FR-19.

## Antes de começar

- A 13-01 integrada.
- Um commit por tela.

## Resultado da entrega

(a preencher)

## Como testar

**Onde olhar primeiro:**

1. Configurações: salve uma chave, saia e volte. O campo volta vazio, o selo diz "configurada", e a chave não está no HTML da página.
2. Conectar IA: o diálogo de confirmação do Claude Desktop grava só depois de "Confirmar", e "Cancelar" não grava nada.

**Para conferir (Erick):**

- Conecte e desconecte o Claude Desktop pelo diálogo, e copie o comando do VS Code.
