# Catálogo e Motor de Descritores DeCS/MeSH Trilíngues no Núcleo

**Fase:** 21 · Versão 2.10 · **Situação:** pronta

## O que faz

Implementa no núcleo do RSL.app o catálogo e motor de **Descritores em Ciências da Saúde (DeCS/MeSH)** em 3 idiomas (Português, Inglês, Espanhol) (FR-33, D-044, ideia 4.2):

1. **Catálogo Integrado de Vocabulário Controlado (`src/rslapp/core/decs.py`):**
   - Base de descritores representativos e fundamentais cobrindo:
     - Saúde Coletiva, Epidemiologia e Atenção Primária;
     - Inteligência Artificial, Informática em Saúde e Telemedicina;
     - Enfermagem, Medicina Baseada em Evidências e Revisões Sistemáticas;
     - Neurociências, Saúde Mental, Doenças Crônicas e Infecciosas.
   - Cada descritor possui:
     - `decs_id`: identificador oficial (ex.: `D000069550` ou similar);
     - `terms`: dicionário trilíngue com descritores principais autorizados em `pt`, `en` e `es`;
     - `synonyms`: dicionário trilíngue com listas de sinônimos/termos alternativos autorizados em `pt`, `en` e `es`.

2. **Funções do Motor:**
   - `lookup_descriptors(query: str, lang: str = "pt", max_results: int = 10) -> list[dict]`:
     - Realiza busca tolerante normalizada por substring e correspondência de palavras no idioma indicado ou em qualquer um dos três idiomas.
     - Retorna lista de descritores com termos principais e sinônimos nos 3 idiomas.
   - `build_multilingual_query(descriptor_ids_or_terms: list[str], operator: str = "OR") -> dict[str, str]`:
     - Monta blocos booleanos de pesquisa limpos e estruturados para cada língua:
       - `pt`: `("Termo Principal" OR "Sinônimo 1" OR ...)`
       - `en`: `("Main Term" OR "Synonym 1" OR ...)`
       - `es`: `("Término Principal" OR "Sinónimo 1" OR ...)`

## O que não faz

- Não depende de conexão de rede externa para funcionar (o catálogo é local, rápido e 100% autocontido no pacote Python, funcionando offline).
- Não substitui o julgamento metodológico do pesquisador, servindo como acelerador de precisão científica.

## Decisões desta spec

- **Autonomia Offline e Resiliência (D-009, D-044):** Para garantir funcionamento ininterrupto mesmo quando a API externa da BIREME estiver instável ou fora do ar, o RSL.app traz o catálogo curado localmente.

## Para instituições (D-029)

Permite que estudantes de graduação e pós-graduação aprendam a estruturar estratégias de busca multilíngues no padrão formal de indexação científica internacional.

## Pronto quando

- [x] Módulo `src/rslapp/core/decs.py` implementado com catálogo e funções de consulta e geração booleana.
- [x] Testes unitários em `tests/core/test_decs.py` passando 100%.
- [x] Linter ruff limpo sem avisos.
