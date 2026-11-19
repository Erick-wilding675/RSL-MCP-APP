# Tabela de Extração de Dados para Metanálise (22-02)

Permite a extração estruturada de dados quantitativos e qualitativos de estudos incluídos, com suporte a cálculo de medidas de efeito e exportação direta para R (`metafor`) e RevMan (FR-35, D-046).

## Contexto e Fundamento
- **Fundamento:** A revisão sistemática com metanálise exige tabular numericamente os achados de cada estudo: tamanho amostral dos grupos intervenção e controle, desfechos dicotômicos (eventos/total) ou contínuos (médias e desvios padrão), e estimativas de efeito com intervalos de confiança.
- **Rastreabilidade:** Cada dado numérico extraído pode ter a indicação do trecho/página de onde foi retirado no artigo e indicação de autoria (`ai_extracted` vs `human_verified`), permitindo conferência e auditoria.

## O que faz
1. **Módulo `rslapp.core.extraction`:**
   - Modelo `StudyOutcome`:
     - `name: str` (nome do desfecho analisado, ex.: "Mortalidade em 30 dias", "Redução de pressão arterial sistólica")
     - `outcome_type: str` ("dichotomous" ou "continuous")
     - `unit: str | None` (unidade de medida, ex.: "mmHg", "dias", "%")
     - **Dados de intervenção/grupo 1:** `n_intervention: int | None`, `events_intervention: int | None`, `mean_intervention: float | None`, `sd_intervention: float | None`
     - **Dados de controle/grupo 2:** `n_control: int | None`, `events_control: int | None`, `mean_control: float | None`, `sd_control: float | None`
     - **Medida de efeito relatada:** `effect_measure: str | None` ("OR", "RR", "HR", "MD", "SMD")
     - `effect_estimate: float | None`
     - `ci_lower: float | None`
     - `ci_upper: float | None`
     - `p_value: float | None`
   - Modelo `ExtractionData`:
     - `work_id: str`
     - `study_design: str` (ex.: "RCT", "Cohort", "Case-Control", "Cross-Sectional")
     - `sample_size_total: int | None`
     - `country: str | None`
     - `intervention_description: str | None`
     - `control_description: str | None`
     - `outcomes: list[StudyOutcome]`
     - `evidence_quote: str | None`
     - `page_number: str | None`
     - `author_type: str` ("human" ou "ai")
     - `verified_by_human: bool`
     - `notes: str | None`
     - `updated_at: str` (ISO 8601)

2. **Cálculos e utilitários:**
   - Cálculo automático de Odds Ratio (OR) e Risco Relativo (RR) com intervalo de confiança de 95% para desfechos dicotômicos quando eventos e $N$ são fornecidos.
   - Cálculo de Diferença de Médias (MD) e Standardized Mean Difference (SMD - d de Cohen) para desfechos contínuos.

3. **Exportadores:**
   - `export_extraction_csv(extractions: list[ExtractionData], works: list[Work]) -> str`:
     - Gera CSV compatível com R `metafor` (colunas prontas: `study_id`, `author_year`, `ai`, `bi`, `ci`, `di`, `n1i`, `n2i`, `m1i`, `sd1i`, `m2i`, `sd2i`, `yi`, `vi`).
   - `export_revman_csv(extractions: list[ExtractionData], works: list[Work]) -> str`:
     - Gera formato padrão para importação direta no RevMan 5 / RevMan Web.

4. **Persistência no Store:**
   - `data_dir / "extraction" / {list_id} / {work_id}.json`.

## Pronto quando
- Testes unitários para cálculos de OR, RR, MD e SMD.
- Testes de exportação CSV para `metafor` e RevMan.
- Persistência e leitura íntegra no `Store`.
