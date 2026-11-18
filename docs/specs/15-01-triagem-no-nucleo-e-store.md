# Triagem no Núcleo e Store

**Fase:** 15 · Versão 2.4 · **Situação:** pronta

## O que faz

Implementa o modelo de dados e a persistência em arquivos para a etapa de triagem de artigos acadêmicos (seleção por título e resumo, e seleção por texto completo):
1. **Módulo do Núcleo (`src/rslapp/core/screening.py`):**
   - Define a estrutura de uma decisão de triagem:
     - `work_id`: identificador sequencial (ex: `"1"`, `"2"`) ou chave única do artigo na lista;
     - `doi`: DOI opcional para referência cruzada estável;
     - `decision`: `"included"`, `"excluded"` ou `"maybe"`;
     - `reason`: motivo padronizado ou personalizado de exclusão/inclusão (ex: `"População fora do escopo"`, `"Intervenção não elegível"`, `"Sem grupo de controle"`, `"Desenho de estudo não aceito"`, `"Idioma inacessível"`, `"Texto completo não recuperado"`);
     - `decided_by`: autoria da decisão (ex: `"human"`, `"ai"`, `"ai:claude-3-5-sonnet"`, `"ai:gpt-4o"`);
     - `stage`: estágio da triagem (`"title_abstract"` ou `"full_text"`);
     - `notes`: notas qualitativas adicionais;
     - `decided_at`: data e hora UTC ISO 8601 da decisão.
   - Fornece funções de validação e consolidação estatística:
     - `validate_decision(...)`: valida campos e restrições semânticas;
     - `calculate_screening_summary(...)`: calcula métricas de progresso (`total_works`, `screened`, `pending`, `included`, `excluded`, `maybe`, discriminação por motivos de exclusão, distribuição por autoria humano vs. IA e discriminação por estágio).
2. **Armazenamento no Store (`src/rslapp/store/__init__.py`):**
   - Cria o diretório `screening/` dentro de `data_dir` para manter a integridade imutável dos arquivos de busca em `lists/`;
   - Implementa:
     - `save_screening_decision(list_id, decision_data)`: grava ou atualiza de forma atômica uma decisão de artigo, preservando o histórico de decisões anteriores da lista;
     - `get_screening(list_id)`: recupera o dicionário com todas as decisões gravadas para a lista;
     - `get_screening_summary(list_id)`: calcula e retorna o resumo quantitativo consolidado da triagem da lista.
3. **Fachada do Serviço Desktop (`src/rslapp/desktop/service.py`):**
   - Expõe métodos:
     - `save_screening_decision(list_id, decision_data)`
     - `get_screening(list_id)`
     - `get_screening_summary(list_id)`

## O que não faz

- Não altera as buscas nem os arquivos originais em `lists/` e `searches/`.
- Não impõe quais motivos o pesquisador deve usar (oferece motivos recomendados pelo PRISMA/Cochrane, mas aceita texto livre).
- Não cria as interfaces visuais nem as ferramentas MCP (estas entram nas tarefas 15-03 e 15-04).

## Decisões desta spec

1. **Arquivo dedicado por lista em `screening/{list_id}.json` (D-007, D-036):** evita reescrever o arquivo JSON da lista de centenas de artigos a cada clique na triagem, protegendo contra corrupção acidental e respeitando o princípio de listas imutáveis do projeto.
2. **Rastro de autoria transparente (D-036):** todo registro contém `decided_by` (`human` ou `ai`), carimbo de data e estágio, permitindo auditoria metodológica perante bancas e pareceristas.

## Para instituições (D-029)

Permite que programas de pós-graduação e grupos de pesquisa auditem com exatidão a taxa de concordância e a participação de inteligência artificial na triagem de trabalhos, respondendo aos comitês de integridade científica.

## Pronto quando

- [x] `src/rslapp/core/screening.py` implementado com validação e cálculo de resumo.
- [x] `src/rslapp/store/__init__.py` suporta `save_screening_decision`, `get_screening` e `get_screening_summary` gravando em `screening/{list_id}.json` com gravação atômica.
- [x] `src/rslapp/desktop/service.py` expõe métodos correspondentes.
- [x] Testes unitários em `tests/core/test_screening.py` cobrem validação de decisões, cálculos de resumo, rastro humano vs. IA e tratamento de erros.
- [x] Testes de armazenamento em `tests/store/test_screening_store.py` cobrem gravação atômica, persistência de decisões sucessivas e isolamento por lista.
- [x] Ruff check limpo e suíte completa de testes passando.
