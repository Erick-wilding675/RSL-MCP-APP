# Exportação em RIS

**Fase:** 2 · Fatia completa · **Situação:** não iniciada

## O que faz

A interface comum dos exportadores em `exporters/base.py`, o exportador `exporters/ris.py` e a ferramenta `export_list` (por ora só com `format="ris"`). O arquivo é gravado em `RSL_EXPORT_DIR` com o nome da lista e o caminho volta à IA. Os campos de RIS mapeados são tipo, título, autores, ano, periódico, resumo, palavras-chave e DOI.

## O que não faz

Não exporta CSV, JSON, lista de DOIs nem URL do OpenAlex (tarefa 05-03). Não troca ids de referências por DOI (04-01).

## Pronto quando

- [ ] Teste: uma lista de exemplo vira um arquivo RIS válido, com um registro por artigo e todos os autores
- [ ] Teste: uma lista inexistente devolve `list_not_found`; uma pasta sem permissão devolve `export_folder_not_writable`; um formato desconhecido devolve `invalid_input`
- [ ] Teste manual do Erick: uma busca real de tema pequeno, exportada em RIS, abre no VOSviewer 1.6.21 sem edição manual (primeiro critério de aceite do projeto); o resultado vai para a seção Resultado da entrega e para o T-008
- [ ] O RIS não tem campo padrão para ORCID nem referências; anotar na entrega o que foi para campos livres ou ficou de fora

## Vem de

FR-06, FR-12, UC-01, D-002. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Nenhuma. O teste no VOSviewer é feito pelo Erick.

## Resultado da entrega

A escrever na entrega.

## Como testar

A escrever na entrega.
