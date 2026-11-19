# Dupla Triagem, Kappa de Cohen e Pacote de Reprodutibilidade Expandido (22-04)

Permite o cálculo do índice de concordância inter-avaliadores (Kappa de Cohen) entre dois revisores (ou entre humano e IA), identifica divergências para resolução de consenso e expande o Pacote de Reprodutibilidade Científica (.zip) com extração, risco de viés e manifesto de texto completo (FR-37, D-048).

## Contexto e Fundamento
- **Fundamento:** A triagem às cegas por dois pesquisadores independentes é o padrão ouro de revisões sistemáticas. O índice Kappa de Cohen ($\kappa$) mede a concordância real acima do acaso.
- Quando a IA sugere triagens, calcular o $\kappa$ entre a sugestão da IA e a decisão humana final é a métrica padrão que a pesquisa científica exige para validar o uso de IA.
- O Pacote de Reprodutibilidade (.zip com checksums SHA-256) deve conter todos os produtos do ciclo de vida da revisão para permitir auditoria total em repositórios abertos (Zenodo, OSF, DSpace).

## O que faz
1. **Módulo `rslapp.core.screening` (expansão):**
   - Função `calculate_cohen_kappa(decisions_a: dict[str, str], decisions_b: dict[str, str]) -> KappaResult`:
     - Determina artigos comuns avaliados por ambos.
     - Monta matriz de contingência $2 \times 2$ (incluídos vs. excluídos) ou $3 \times 3$ (incluído, excluído, talvez).
     - Calcula:
       - $P_o$: concordância observada ($P_o = \frac{\sum \text{concordâncias}}{N}$).
       - $P_e$: concordância esperada pelo acaso.
       - $\kappa = \frac{P_o - P_e}{1 - P_e}$ (com tratamento de divisão por zero se $P_e = 1$).
     - Classificação de Landis & Koch:
       - $< 0.00$: Sem concordância (Pobre)
       - $0.00 - 0.20$: Leve
       - $0.21 - 0.40$: Razoável
       - $0.41 - 0.60$: Moderada
       - $0.61 - 0.80$: Substancial
       - $0.81 - 1.00$: Quase perfeita
     - Lista de `divergent_work_ids` (onde avaliador A divergiu de avaliador B).

2. **Expansão do Pacote de Reprodutibilidade (`rslapp.core.reproducibility`):**
   - Inclui no arquivo `.zip`:
     - `extraction.csv` (quando houver dados de extração)
     - `extraction.json`
     - `risk_of_bias.json` (quando houver avaliações de risco de viés)
     - `fulltext_manifest.json` (quando houver downloads de texto completo)
     - `screening_concordance.json` (quando houver dados de dupla triagem)
   - Todos os novos arquivos são calculados no `checksums.sha256`.

## Pronto quando
- Testes matemáticos rigorosos para o cálculo do Kappa com matrizes conhecidas.
- Detecção precisa de artigos divergentes.
- Geração do Pacote de Reprodutibilidade contendo os novos arquivos e conferência SHA-256.
