# Exportação em RIS

**Fase:** 2 · Fatia completa · **Situação:** não iniciada

## O que faz

A interface comum dos exportadores em `exporters/base.py`, o exportador `exporters/ris.py` e a ferramenta `export_list` (por ora só com `format="ris"`). O arquivo é gravado em `RSL_EXPORT_DIR` com o nome da lista e o caminho volta à IA. Os campos de RIS mapeados são tipo, título, autores, ano, periódico, resumo, palavras-chave e DOI.

## O que não faz

Não exporta CSV, JSON, lista de DOIs nem URL do OpenAlex (tarefa 05-03). Não troca ids de referências por DOI (04-01).

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Interface dos exportadores** em `exporters/base.py`: `Exporter` com `format: str`, `extension: str` e `def render(self, list_data: dict) -> str`, que recebe a lista salva (com `works` no formato `Work.to_dict()`) e devolve o texto. A gravação do arquivo fica fora do exportador, numa função comum, para os outros formatos (tarefa 05-03) reaproveitarem.
2. **Arquivo:** `<RSL_EXPORT_DIR>/<list_id>.ris` (por exemplo `l-0007.ris`), em UTF-8 e fim de linha `\r\n`, gravado de forma atômica (arquivo temporário e `os.replace`). Exportar de novo a mesma lista substitui o arquivo. A pasta é criada se não existir; se não aceita gravação, `export_folder_not_writable`.
3. **Erros:** como na 02-02, o miolo levanta `RSLError` e o servidor converte em `ToolError("<código>: <mensagem>")`. `list_not_found` vem de `Store.get_list` (que levanta `FileNotFoundError` ou `ValueError` para id malformado; os dois viram `list_not_found`).
4. **Mapeamento RIS:** `TY` (`JOUR` para `article`, `CONF` para trabalhos de evento quando o tipo indicar, `GEN` para o resto), `TI`, um `AU` por autor na ordem (`Sobrenome, Nome` só se a fonte já trouxer assim; senão o nome como veio), `PY`, `JO` (o periódico), `AB`, um `KW` por palavra-chave, `DO`, `ER` no fim. Campos vazios não são escritos. Nada é inventado.
5. **ORCID, afiliações e referências** não têm campo padrão no RIS. Nesta tarefa ficam de fora do RIS (estão no JSON da lista e no formato `json` da 05-03). Se o teste do Erick no VOSviewer pedir outra coisa, volta para a spec.

## Pronto quando

- [ ] Teste: uma lista de exemplo vira um arquivo RIS válido, com um registro por artigo e todos os autores
- [ ] Teste: uma lista inexistente devolve `list_not_found`; uma pasta sem permissão devolve `export_folder_not_writable`; um formato desconhecido devolve `invalid_input`
- [ ] Teste manual do Erick: uma busca real de tema pequeno, exportada em RIS, abre no VOSviewer 1.6.21 sem edição manual (primeiro critério de aceite do projeto); o resultado vai para a seção Resultado da entrega e para o T-008
- [ ] O RIS não tem campo padrão para ORCID nem referências; anotar na entrega o que foi para campos livres ou ficou de fora

## Vem de

FR-06, FR-12, UC-01, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Tarefa 02-02 integrada. O teste no VOSviewer é feito pelo Erick.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
