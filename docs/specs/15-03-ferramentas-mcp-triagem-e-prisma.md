# Ferramentas MCP de Triagem e PRISMA

**Fase:** 15 · Versão 2.4 · **Situação:** pronta

## O que faz

Expõe as novas capacidades de triagem com rastro, fluxograma PRISMA 2020 e declaração metodológica de IA como ferramentas MCP registradas tanto no servidor de linha de comando (`stdio`) quanto no servidor Web multiusuário (`http`), atendendo aos requisitos FR-25, FR-26, FR-27 e às decisões D-036, D-037, D-038:

1. **Ferramenta `screen_work`:**
   - Registra ou atualiza a decisão de triagem de um trabalho pertencente a uma lista salva (`list_id`).
   - Argumentos:
     - `list_id` (str, obrigatório): identificador da lista (ex: `"l-0001"`).
     - `work_id` (str, obrigatório): ID do trabalho (DOI, ID sequencial ou ID da base).
     - `decision` (str, obrigatório): `"included"`, `"excluded"` ou `"maybe"`.
     - `reason` (str, opcional): motivo da exclusão ou nota de justificativa.
     - `decided_by` (str, padrão `"ai"` no MCP, ou identificador do modelo/usuário): autoria da decisão para rastro de auditoria.
     - `stage` (str, padrão `"title_abstract"`): estágio da triagem (`"title_abstract"` ou `"full_text"`).
     - `notes` (str, opcional): observações metodológicas adicionais.
   - Retorno: confirmação da decisão gravada e resumo atualizado do progresso da triagem da lista.

2. **Ferramenta `get_screening_status`:**
   - Retorna o resumo quantitativo e qualitativo das decisões de triagem da lista (`readOnlyHint=True`).
   - Argumentos:
     - `list_id` (str, obrigatório): identificador da lista.
   - Retorno: total de trabalhos, triados, pendentes, incluídos, excluídos, em dúvida (`maybe`), percentual de progresso, discriminação dos motivos de exclusão e divisão por autoria (`human` vs. `ai`).

3. **Ferramenta `get_prisma_flow`:**
   - Calcula e retorna a estrutura do fluxograma PRISMA 2020 e o checklist PRISMA-S (`readOnlyHint=True`).
   - Argumentos:
     - `list_id` (str, obrigatório): identificador da lista.
     - `include_svg` (bool, padrão `False`): se verdadeiro, inclui a string completa do SVG vetorial diagramado pronto para salvar em arquivo.
   - Retorno: dados de identificação, triagem, elegibilidade, inclusão, texto formatado em Markdown com o checklist PRISMA-S e opcionalmente o SVG.

4. **Ferramenta `get_ai_disclosure`:**
   - Gera a declaração formal de transparência no uso de inteligência artificial metodológica pronta para publicação (`readOnlyHint=True`).
   - Argumentos:
     - `list_id` (str, obrigatório): identificador da lista.
     - `language` (str, padrão `"pt"`): idioma da declaração (`"pt"` ou `"en"`).
   - Retorno: texto em Markdown no padrão internacional COPE/ICMJE/SciELO com os quantitativos consolidados e atestado de supervisão humana.

5. **Para instituições (D-029):**
   - Disponível sem custo adicional para qualquer IA conectada via stdio ou HTTP/SSE no servidor da instituição, viabilizando que grupos de pesquisa auditem revisões sistemáticas institucionais.

## O que não faz

- Não altera as listas de busca originais (`lists/l-NNNN.json`), preservando a imutabilidade do registro original.
- Não aceita decisões fora dos valores padronizados (`included`, `excluded`, `maybe`).

## Pronto quando

- [x] Ferramentas `@mcp.tool()` registradas em `src/rslapp/server.py` tanto na instância stdio quanto na lista de exportação HTTP (`_build_http_mcp_server`).
- [x] Documentação com docstrings detalhadas e orientações claras à IA no MCP.
- [x] Testes unitários de integração MCP em `tests/test_server_screening.py` cobrindo todas as 4 ferramentas.
- [x] Testes do servidor HTTP em `tests/test_server_http.py` verificando a exposição das 4 ferramentas.
- [x] Ruff check limpo.
