# Protocolo Metodológico Pré-Busca Versionado (PROSPERO, OSF, Cochrane, JBI)

**Fase:** 18 · Versão 2.7 · **Situação:** pronta

## O que faz

Implementa no núcleo do RSL.app e no armazenamento o sistema de **Protocolo Metodológico Pré-Busca Versionado** (FR-30, D-041, ideia 1.1):

1. **Modelo de Protocolo de Pesquisa (`src/rslapp/core/protocols.py`):**
   - Suporte aos frameworks metodológicos mais utilizados internacionalmente:
     - `pico`: População, Intervenção, Comparação, Desfecho (Outcomes), Desenho de estudo (Study design - opcional).
     - `pcc`: População, Conceito, Contexto (padrão JBI para revisões de escopo / scoping reviews).
     - `pico_qualitative`: População, Interesse (Interest), Contexto (revisões qualitativas).
     - `spider`: Sample (Amostra), Phenomenon of Interest (Fenômeno de Interesse), Design (Desenho), Evaluation (Avaliação), Research type (Tipo de Pesquisa).
     - `narrative`: Pergunta de pesquisa central, Escopo temático, Contexto teórico e Objetivos.
   - Estrutura completa de dados (`Protocol`):
     - `id: str`: identificador único (ex.: `prot_a1b2c3d4` ou sequencial `prot_0001`).
     - `title: str`: título do protocolo / revisão sistemática.
     - `framework: Literal["pico", "pcc", "pico_qualitative", "spider", "narrative"]`.
     - `question: str`: pergunta de pesquisa principal formulada a partir do framework.
     - `subquestions: list[str]`: perguntas de pesquisa secundárias ou específicas.
     - `components: dict[str, str]`: componentes do framework selecionado devidamente discriminados.
     - `inclusion_criteria: list[str]`: critérios formais de inclusão.
     - `exclusion_criteria: list[str]`: critérios formais de exclusão com justificativas metodológicas.
     - `planned_sources: list[str]`: bases acadêmicas planejadas (`openalex`, `crossref`, `semanticscholar`, `pubmed`, `europepmc`, `bdtd`, `scopus`, `wos`).
     - `search_strategy: str`: estratégia de busca textual com termos, sinônimos e operadores booleanos.
     - `languages: list[str]`: idiomas considerados (ex.: `["pt", "en", "es"]`).
     - `date_range: dict[str, int | None]`: recorte temporal planejado (`start_year`, `end_year`).
     - `authors: list[str]`: autores e pesquisadores responsáveis.
     - `status: Literal["draft", "registered", "completed"]`: status do protocolo.
     - `registration_platform: str | None`: plataforma de registro prévio (`"PROSPERO"`, `"OSF"`, `"JBI"`, `"Outro"`).
     - `registration_number: str | None`: identificador ou DOI do registro (ex.: `"CRD42026123456"` ou link do OSF).
     - `version: int`: versão inteira incremental (inicia em 1).
     - `created_at: str`: carimbo ISO 8601 de criação.
     - `updated_at: str`: carimbo ISO 8601 da última alteração.
     - `history: list[dict[str, Any]]`: histórico resumido de alterações entre versões.
     - `ai_assisted: bool`: indicação se a formulação contou com auxílio de IA.
     - `ai_model: str | None`: modelo de IA que auxiliou no desenho do protocolo.

2. **Validação e Normalização (`validate_protocol_data`):**
   - Valida que o framework é reconhecido.
   - Valida que título e pergunta de pesquisa não estão vazios.
   - Garante que critérios de inclusão e exclusão sejam listas de strings.
   - Normaliza datas e versões.

3. **Armazenamento no Store (`src/rslapp/store/`):**
   - Diretório estruturado: `protocols/{protocol_id}.json`.
   - Histórico de versões mantido em `protocols/history/{protocol_id}_v{version}.json`.
   - Operações atômicas com `atomic_write_replace`:
     - `save_protocol(data: dict[str, Any]) -> dict[str, Any]`: se o protocolo já existe, incrementa `version`, arquiva a versão anterior no histórico e salva o novo estado atual.
     - `get_protocol(protocol_id: str, version: int | None = None) -> dict[str, Any] | None`: permite resgatar a versão atual ou uma versão histórica pontual.
     - `list_protocols() -> list[dict[str, Any]]`: lista todos os protocolos cadastrados ordenados por data de atualização.
     - `delete_protocol(protocol_id: str) -> bool`: remove protocolo e seu histórico.

4. **Exportador Markdown para PROSPERO, OSF e Apêndice Metodológico (`format_protocol_markdown`):**
   - Formata o protocolo em documento Markdown acadêmico rigoroso com:
     - Cabeçalho com título, metadados, status, autores e rastro de versionamento.
     - Seção de Enquadramento Teórico com os elementos do framework discriminados (ex.: P, I, C, O).
     - Pergunta norteadora e subperguntas numeradas.
     - Tabela comparativa ou listas estruturadas de Critérios de Elegibilidade (Inclusão vs. Exclusão).
     - Estratégia de Busca Detalhada: bases planejadas, filtros temporais e linguísticos, sintaxe booleana.
     - Declaração Metodológica de Transparência sobre o uso de IA na formulação do protocolo.

5. **Integração com Pacote de Reprodutibilidade (`rslapp.core.reproducibility`):**
   - Permite que a busca ou a lista referencie um `protocol_id`.
   - Caso um protocolo seja referenciado ou exista um protocolo com mesmo id/título, inclui `protocol.md` e `protocol.json` no pacote `.zip` e no manifesto `checksums.sha256`.

## O que não faz

- Não submete diretamente via API ao PROSPERO ou OSF (essas plataformas exigem login pessoal do pesquisador com formulários manuais ou credenciais individuais; o RSL.app entrega o texto exatamente estruturado nos moldes requeridos).
- Não substitui o julgamento metodológico do pesquisador ou do comitê de ética.

## Decisões desta spec

1. **Versionamento Imutável de Histórico (D-041):** Cada atualização de um protocolo não apaga o passado; a versão antiga é automaticamente arquivada em `history/`, permitindo auditoria metodológica caso haja alteração de critérios no decorrer da pesquisa (exigência central do PRISMA 2020 para justificar desvios do protocolo original).
2. **Frameworks Especializados:** Apoio aos 5 frameworks principais da literatura científica de saúde, ciências sociais aplicadas e engenharias.

## Para instituições (D-029)

Permite que universidades, comitês de ética em pesquisa (CEP) e programas de pós-graduação estabeleçam um rastro auditável dos projetos de mestrado e doutorado antes da execução das buscas, mitigando o risco de vieses de seleção.

## Pronto quando

- [x] Módulo `src/rslapp/core/protocols.py` implementado com validação, normalização e formatação Markdown completa.
- [x] Métodos de armazenamento atômico implementados em `src/rslapp/store/__init__.py` com suporte a versionamento e histórico.
- [x] Integração com `build_reproducibility_package` para empacotar o protocolo caso disponível.
- [x] Testes unitários do núcleo em `tests/core/test_protocols.py` passando 100%.
- [x] Linter ruff limpo sem nenhum aviso.
