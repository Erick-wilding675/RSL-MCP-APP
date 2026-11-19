# Avaliação de Risco de Viés e Qualidade Metodológica (22-03)

Permite a avaliação estruturada de qualidade e risco de viés de estudos incluídos com suporte aos instrumentos RoB 2 (ensaios clínicos), ROBINS-I (estudos não randomizados) e JBI Critical Appraisal, com geração de matriz de semáforo (FR-36, D-047).

## Contexto e Fundamento
- **Fundamento:** Em revisões sistemáticas, a avaliação de viés é mandatória pelo PRISMA e pelo manual Cochrane. Cada estudo deve ser avaliado domínio por domínio, justificando cada julgamento com base no texto do artigo.
- **Transparência metodológica:** A IA do pesquisador pode apontar trechos do método e sugerir um julgamento inicial, mas o pesquisador valida e a autoria fica gravada no log de reprodutibilidade.

## O que faz
1. **Módulo `rslapp.core.risk_of_bias`:**
   - Instrumentos suportados:
     - `rob2`: Cochrane Risk of Bias 2 (D1: Randomização, D2: Desvios da intervenção, D3: Dados faltantes, D4: Mensuração do desfecho, D5: Relato seletivo). Julgamentos: `low`, `some_concerns`, `high`.
     - `robins_i`: Cochrane ROBINS-I (D1: Confusão, D2: Seleção, D3: Classificação da intervenção, D4: Desvios da intervenção, D5: Dados faltantes, D6: Mensuração do desfecho, D7: Relato). Julgamentos: `low`, `moderate`, `serious`, `critical`, `no_info`.
     - `jbi`: Joanna Briggs Institute (questões do checklist JBI com respostas `yes`, `no`, `unclear`, `not_applicable`).
   - Modelo `DomainAssessment`:
     - `domain_id: str` (ex.: "D1", "D2")
     - `domain_name: str` (ex.: "Processo de randomização")
     - `judgment: str` ("low", "some_concerns", "high", "moderate", "serious", "critical", "yes", "no", "unclear", "not_applicable")
     - `rationale: str` (justificativa analítica)
     - `quote: str | None` (trecho direto do artigo)
   - Modelo `RiskOfBiasAssessment`:
     - `work_id: str`
     - `tool: str` ("rob2", "robins_i", "jbi")
     - `domains: list[DomainAssessment]`
     - `overall_judgment: str` ("low", "some_concerns", "high", "critical", etc. calculado automaticamente ou definido pelo revisor)
     - `overall_rationale: str | None`
     - `author_type: str` ("human" ou "ai")
     - `verified_by_human: bool`
     - `updated_at: str` (ISO 8601)

2. **Cálculo do julgamento global:**
   - Regra padrão Cochrane RoB 2: Se todos os domínios forem `low` -> Geral `low`. Se algum for `some_concerns` e nenhum `high` -> Geral `some_concerns`. Se pelo menos um domínio for `high` -> Geral `high`.

3. **Matriz e Visualização:**
   - Função `generate_traffic_light_summary(assessments: list[RiskOfBiasAssessment]) -> dict[str, Any]`:
     - Estrutura de dados pronta para renderização de tabela de semáforo com cores (verde, amarelo, vermelho).

4. **Persistência no Store:**
   - `data_dir / "quality" / {list_id} / {work_id}.json`.

## Pronto quando
- Testes unitários para RoB 2, ROBINS-I e JBI.
- Regra de cálculo de julgamento global testada.
- Persistência e leitura íntegra no `Store`.
