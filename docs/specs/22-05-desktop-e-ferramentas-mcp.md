# Novas Ferramentas MCP e Interface Desktop para a Revisão Completa (22-05)

Expõe as novas capacidades no servidor MCP (stdio e HTTP) e integra na interface desktop (NiceGUI) com telas e formulários interativos (FR-38, D-049).

## O que faz
1. **Novas ferramentas MCP:**
   - `fetch_fulltext(list_id: str, work_id: str, email: str | None = None) -> dict`: Tenta resolver e baixar o PDF em acesso aberto para o artigo.
   - `get_fulltext_status(list_id: str) -> dict`: Devolve o resumo dos textos completos baixados e disponíveis na lista.
   - `save_extraction_data(list_id: str, work_id: str, study_design: str, outcomes: list[dict], ...) -> dict`: Salva ou atualiza a extração de dados para metanálise.
   - `get_extraction_table(list_id: str) -> dict`: Devolve a tabela de extração consolidada de todos os artigos da lista.
   - `export_extraction_csv(list_id: str, format: str = "metafor") -> dict`: Exporta os dados para R `metafor` ou RevMan.
   - `save_risk_of_bias(list_id: str, work_id: str, tool: str, domains: list[dict], ...) -> dict`: Salva avaliação de risco de viés (RoB 2, ROBINS-I, JBI).
   - `get_risk_of_bias_summary(list_id: str) -> dict`: Devolve a matriz de risco de viés e julgamento global da lista.
   - `get_screening_concordance(list_id: str) -> dict`: Devolve o cálculo do Kappa de Cohen e lista de divergências.

2. **Interface Desktop:**
   - **Tela Lista (`/lista/{list_id}`):**
     - Botão "Baixar Textos Abertos (PDF)" com notificação de progresso.
     - Botões de atalho: "Extração de Dados" (`/extracao/{list_id}`) e "Risco de Viés" (`/qualidade/{list_id}`).
     - Coluna de status na tabela indicando badge `PDF OA` quando disponível com botão para abrir o arquivo.
   - **Nova Tela Extração de Dados (`/extracao/{list_id}`):**
     - Lista os artigos incluídos na triagem.
     - Formulário para registrar desenho do estudo, amostras e adicionar múltiplos desfechos com seus valores (médias, desvios ou eventos).
     - Botão para exportar CSV formatado para R `metafor` ou RevMan.
   - **Nova Tela Risco de Viés (`/qualidade/{list_id}`):**
     - Seleção do instrumento (RoB 2 para ensaios clínicos, ROBINS-I para observacionais, JBI).
     - Formulário com os domínios do instrumento, julgamentos com cores e trechos de evidência.
     - Gráfico / tabela resumo estilo semáforo (Traffic-light plot).
   - **Tela Triagem (`/triagem/{list_id}`):**
     - Indicador visual do Kappa de Cohen quando houver decisão humana vs sugestão de IA.
     - Botão de filtro "Apenas divergências".

## Pronto quando
- Registro e resposta das 8 novas ferramentas MCP no servidor stdio e HTTP.
- Rotas `/extracao/{list_id}` e `/qualidade/{list_id}` registradas e testadas na suíte do desktop.
- 100% dos testes passando.
