# Extração de Grafos e Geradores de Redes Bibliométricas no Núcleo

**Fase:** 19 · Versão 2.8 · **Situação:** pronta

## O que faz

Implementa no núcleo do RSL.app o motor de **Extração de Grafos e Redes Bibliométricas Nativas** (FR-31, D-042, ideia 3.1):

1. **Motor de Extração de Redes (`src/rslapp/core/network.py`):**
   - Modalidades:
     - `coauthorship`: nós são autores, peso do nó é o número de artigos publicados na revisão; arestas são colaborações conjuntas no mesmo artigo, com peso igual ao número de publicações compartilhadas.
     - `source_coupling`: nós são veículos de publicação (periódicos/revistas - `venue`), peso do nó é o volume de artigos publicados; arestas representam coocorrência de autores ou acoplamento temático.
     - `keyword_cooccurrence`: nós são palavras-chave normalizadas, peso do nó é a frequência de aparição; arestas representam coocorrência de termos no mesmo artigo.
   - Filtros científicos configuráveis:
     - `min_node_weight: int` (filtro de corte para ruído/autores com poucas publicações, padrão 1).
     - `min_edge_weight: int` (filtro de corte para arestas esparsas, padrão 1).
     - `max_nodes: int` (teto configurável para preservar desempenho de renderização, padrão 500).

2. **Geradores de Formatos Nativos:**
   - **VOSviewer Map (`.map`):**
     Arquivo delimitado por tabulação (`\t`) com cabeçalho `id\tlabel\tweight<Occurrences>`, compatível com o manual 1.6.x do VOSviewer (Van Eck & Waltman).
   - **VOSviewer Network (`.network`):**
     Arquivo delimitado por tabulação com triplas `source_id\ttarget_id\tweight`.
   - **Gephi GEXF (`.gexf`):**
     Documento XML válido no padrão GEXF 1.2 (`http://www.gexf.net/1.2draft`) com grafo estático não-direcionado (`undirected`), nós e arestas com pesos estruturados para cálculo de modularidade e layout ForceAtlas2.

3. **Integração no Pacote de Reprodutibilidade:**
   - Adiciona os arquivos `network_coauthorship.map`, `network_coauthorship.network` e `network_coauthorship.gexf` ao pacote `.zip` de reprodutibilidade da revisão.

## O que não faz

- Não executa o software VOSviewer ou Gephi (o RSL.app entrega os arquivos nativos perfeitamente mastigados e compatíveis para abertura imediata).
- Não faz deduplicação heurística agressiva de nomes de autores (a normalização preserva a grafia oficial, usando ORCID quando disponível).

## Decisões desta spec

- **Formatos Nativos Sem Intermediários (D-042):** Elimina a necessidade de passar por RIS ou arquivos intermediários com assistentes manuais propensos a erros; os arquivos `.map` e `.network` abrem instantaneamente no VOSviewer via *Create -> Read VOSviewer map and network files*.
- **Estruturas Leves em Memória:** Os grafos são computados de forma eficiente utilizando contadores `collections.Counter` e combinações `itertools.combinations`.

## Para instituições (D-029)

Permite que laboratórios e programas de pós-graduação gerem mapas de colaboração científica e redes de coautoria prontos para relatórios institucionais e teses.

## Pronto quando

- [x] Módulo `src/rslapp/core/network.py` implementado com extração de coautoria, fontes e termos.
- [x] Geradores de VOSviewer `.map`, `.network` e Gephi `.gexf` implementados.
- [x] Testes unitários do motor de redes em `tests/core/test_network.py` passando 100%.
- [x] Linter ruff limpo sem nenhum aviso.
