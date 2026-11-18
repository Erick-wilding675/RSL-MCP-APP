# Módulo PRISMA 2020 e Declaração de Uso de IA

**Fase:** 15 · Versão 2.4 · **Situação:** pronta

## O que faz

Implementa no núcleo do RSL.app o cálculo matemático das caixas do fluxograma oficial PRISMA 2020, a geração de SVG vetorial diagramado e o gerador de declaração de transparência metodológica no uso de inteligência artificial (FR-26, FR-27, D-037, D-038):

1. **Módulo PRISMA (`src/rslapp/core/prisma.py`):**
   - Função `calculate_prisma_flow(list_data, screening_summary, search_record=None) -> dict[str, Any]`:
     - Calcula com exatidão matemática os números de cada estágio do PRISMA 2020:
       - *Identificação:* registros identificados por base acadêmica, registros importados externamente, total antes da deduplicação e duplicatas removidas;
       - *Triagem:* registros triados na primeira fase (título e resumo), excluídos com motivos discriminados e registros direcionados para busca do texto completo;
       - *Elegibilidade:* relatórios avaliados na íntegra, relatórios não recuperados e excluídos na fase de texto completo;
       - *Inclusão:* estudos e relatórios finalmente incluídos na revisão.
   - Função `render_prisma_svg(flow_data) -> str`:
     - Gera um SVG vetorial diagramado esteticamente agradável no padrão PRISMA 2020, com as 4 fases principais (Identificação, Triagem, Elegibilidade, Inclusão), caixas com bordas suaves, setas conectoras e números reais calculados.
   - Função `render_prisma_markdown(flow_data) -> str`:
     - Gera relatório textual estruturado em formato Markdown com checklist PRISMA-S.

2. **Módulo de Declaração de IA (`src/rslapp/core/ai_disclosure.py`):**
   - Função `render_ai_disclosure(...)`:
     - Gera texto padronizado para a seção de Metodologia em português e inglês;
     - Segue as diretrizes internacionais do COPE (Committee on Publication Ethics), ICMJE e SciELO Brasil sobre integridade e IA generativa;
     - Rastreia quais etapas contaram com auxílio de IA (planejamento da string, triagem de títulos/resumos, verificação de alucinações) e atesta explicitamente a supervisão e validação humana integral sobre as decisões finais.

## O que não faz

- Não depende de bibliotecas gráficas pesadas como Graphviz, Cairo ou Pillow (o SVG é gerado em código Python puro e limpo).
- Não inventa números (todos os valores partem estritamente das contagens do Store e do log).

## Decisões desta spec

1. **SVG Vetorial puro (D-037):** independente de dependências C ou executáveis externos, garantindo funcionamento idêntico no Windows, Linux e macOS, e permitindo exportação em alta resolução para editoração científica.
2. **Conformidade SciELO / COPE (D-038):** modelo de texto que atende às exigências de declaração de uso de IA exigidas pelos principais periódicos indexados nacionais e internacionais.

## Pronto quando

- [x] `src/rslapp/core/prisma.py` calcula fluxograma PRISMA 2020 e gera SVG e Markdown.
- [x] `src/rslapp/core/ai_disclosure.py` gera declarações em PT e EN com números reais e conformidade COPE/SciELO.
- [x] Testes unitários em `tests/core/test_prisma.py` validam consistência matemática dos estágios e geração de SVG válido.
- [x] Testes unitários em `tests/core/test_ai_disclosure.py` validam textos PT/EN e presença dos dados de auditoria.
- [x] Ruff check limpo.
