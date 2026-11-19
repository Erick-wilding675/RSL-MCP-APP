# RSL.app

**A plataforma completa, gratuita e self-hosted de Revisão Sistemática, Metanálise e Bibliometria com IA Rastreável.**

O **RSL.app** acompanha o pesquisador em todas as etapas da revisão de literatura: do desenho do protocolo pré-busca à extração matemática de dados para metanálise. Ele roda **na sua máquina**, usa as suas próprias chaves gratuitas ou institucionais, conecta-se à sua IA favorita via protocolo MCP (*Model Context Protocol*) e oferece um **aplicativo desktop com interface gráfica moderna** para Windows e Linux.

> **O Fundamento do Projeto:** Elevar a revisão sistemática com a IA do próprio pesquisador, com rastreabilidade e reprodutibilidade auditáveis, substituindo a desconfiança pelo rigor metodológico e em conformidade com as diretrizes internacionais (**PRISMA 2020**, **PRISMA-S**, **COPE**, **ICMJE** e **SciELO**).

---

## O Ciclo Completo da Revisão (Do Protocolo à Metanálise)

O RSL.app não é apenas um buscador de artigos: é uma bancada metodológica completa com 37 ferramentas MCP e interface desktop dedicada:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 1. Planejamento │ ──> │   2. Coleta &   │ ──> │ 3. Triagem com  │
│  & Protocolos   │     │  Deduplicação   │     │ Rastro & Kappa  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 6. Metanálise,  │ <── │ 5. Textos OA &  │ <── │ 4. PRISMA 2020  │
│  Risco & Redes  │     │   Fichamento    │     │ & Transparência │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 1. Planejamento Metodológico e Vocabulário Controlado
- **Protocolos pré-busca versionados:** Crie, versione e exporte protocolos nos formatos **PICO**, **PCC**, **PICo**, **SPIDER** ou Narrativo, prontos para registro no **PROSPERO** e no **OSF**.
- **Descritores DeCS/MeSH trilíngues:** Catálogo integrado de descritores autorizados em Português, Inglês e Espanhol com sinônimos oficiais e construtor automático de strings booleanas.
- **Roteiros especializados:** Prompts e orientações metodológicas para Revisão Sistemática (Cochrane), Revisão de Escopo (JBI), Revisão Integrativa (Whittemore/Mendes) e Estudo Bibliométrico.

### 2. Busca Abrangente, Literatura Cinzenta e Deduplicação
- **8 bases integradas:** Consulta simultânea e unificada em **OpenAlex**, **Crossref**, **Semantic Scholar**, **PubMed**, **Europe PMC**, **BDTD** (Biblioteca Digital Brasileira de Teses e Dissertações para literatura cinzenta nacional), além de **Scopus** e **Web of Science** (usando credenciais e acessos da sua instituição).
- **Filtro de pareceres de revisão:** Exclusão automática de pareceres de revisão por pares (*peer-reviews* e cartas de decisão) que poluem as buscas.
- **Deduplicação inteligente:** Unificação de artigos duplicados entre bases, preservando IDs cruzados e fontes de origem.
- **Importação de arquivos externos:** Importe arquivos manuais em **RIS**, **BibTeX**, **CSV do Scopus** e **TSV do Web of Science** diretamente para as suas listas.
- **Revisão Viva (Living Systematic Review):** Reexecute buscas passadas e detecte automaticamente artigos novos versus artigos preservados, gerando relatórios metodológicos diferenciais.

### 3. Integridade Científica e Dupla Triagem Rastreável
- **Verificador de alucinações de referências:** Valide se referências coladas ou geradas por IA realmente existem na Crossref e no OpenAlex, identificando dados divergentes ou referências fictícias.
- **Detecção de retratações:** Alerta visual e metadados de artigos retratados ou com expressão de preocupação via base do **Retraction Watch**.
- **Triagem com rastro de autoria:** Registre decisões de inclusão (`included`), exclusão (`excluded`) ou dúvida (`maybe`) com justificativa formal, marcando expressamente quem decidiu (`human` vs. `ai`).
- **Atalhos rápidos no desktop:** Navegue e trie centenas de artigos por teclado (`I` para incluir, `E` para excluir, `M` para dúvida).
- **Concordância inter-avaliadores (Kappa de Cohen):** Suporte a dupla triagem independente com cálculo automatizado de concordância de Kappa, categorização de Landis & Koch e listagem de divergências para resolução de consenso.

### 4. Relato e Transparência Metodológica
- **Fluxograma PRISMA 2020 oficial em SVG:** Diagrama vetorial desenhado com os números reais de cada etapa (identificação, duplicatas removidas, triagem por título/resumo, elegibilidade e inclusão final).
- **Checklist PRISMA-S:** Relatório auditável com datas, strings exatas por base, filtros aplicados e contagens.
- **Declaração ética de IA:** Geração automatizada de declaração de transparência metodológica no padrão internacional **COPE / ICMJE / SciELO**, em português e inglês.

### 5. Textos Completos Open Access e Fichamento Analítico
- **Download legal de PDFs em Acesso Aberto:** Resolução automatizada e download de textos completos legítimos via **Unpaywall**, **PubMed Central (PMC)** e **OpenAlex OA**, com validação de integridade do cabeçalho `%PDF`.
- **Fichamento científico estruturado:** Registro analítico de objetivo, método, amostra, resultados, limitações e citações diretas com página, com distinção clara entre rascunho de IA e validação humana.
- **Exportação para Obsidian:** Exporte fichamentos consolidados da revisão em Markdown com metadados estruturados.

### 6. Síntese, Metanálise, Redes e Reprodutibilidade
- **Tabela de extração para Metanálise:** Estruturação de dados amostrais e extração de desfechos dicotômicos (**OR**, **RR**) e contínuos (**MD**, **SMD / Hedges' g**) com cálculo de intervalos de confiança de 95%.
- **Exportação nativa para R `metafor` e RevMan:** Arquivos CSV prontos para modelagem estatística com colunas `yi` e `vi` ou tabelas de contingência 2x2.
- **Risco de Viés e Qualidade Metodológica:** Instrumentos **Cochrane RoB 2** (ensaios clínicos), **Cochrane ROBINS-I** (estudos não-randomizados) e **JBI Critical Appraisal**, com algoritmo determinístico de julgamento global e geração de **matriz de semáforo** (*traffic-light plot*).
- **Redes bibliométricas nativas:** Geração de grafos de coautoria, acoplamento de veículos e coocorrência de palavras-chave prontos para o **VOSviewer** (`.map` e `.network`) e **Gephi** (`.gexf`).
- **Pacote de Reprodutibilidade (.zip):** Pacote autocontido com todos os arquivos da revisão (dados brutos, protocolos, buscas, triagem, fichas, matrizes de metanálise e risco de viés) e manifesto de hashes criptográficos `checksums.sha256` pronto para depósito no **Zenodo** ou **OSF**.

---

## Como Usar

O RSL.app pode ser utilizado de duas formas complementares:

### Opção 1: Aplicativo Desktop (Interface Gráfica)
Se você prefere uma interface visual sem intermediários:
1. Baixe o executável pronto na página de [Releases](https://github.com/Erick-wilding675/RSL-MCP-APP/releases):
   - **Windows (x64):** Baixe `RSL.app-<versao>-windows-x64.zip`, extraia e abra `RSL.app.exe`.
   - **Linux (x86_64):** Baixe `RSL.app-<versao>-linux-x86_64.AppImage`, marque permissão de execução (`chmod +x`) e execute.
2. Ou instale via Python (3.10+):
   ```bash
   pip install "rslapp[desktop]"
   rslapp-desktop
   ```
3. O app inclui abas dedicadas para: **Buscar**, **Lista de Artigos**, **Triagem**, **PRISMA 2020**, **Extração Metanálise**, **Risco de Viés**, **Fichamento**, **Roteiros Metodológicos**, **Protocolos**, **Verificar Referências**, **Importar Arquivos**, **Histórico** e **Configurações**.

### Opção 2: Servidor MCP (Conectado à sua IA)
Conecte o RSL.app diretamente ao Claude Desktop, Claude Code, Cursor, VS Code ou ChatGPT.

#### Configuração no Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "rslapp": {
      "command": "uvx",
      "args": ["rslapp"],
      "env": {
        "OPENALEX_API_KEY": "sua-chave-do-openalex",
        "SEMANTIC_SCHOLAR_API_KEY": "sua-chave-da-semantic-scholar",
        "SCOPUS_API_KEY": "sua-chave-scopus-opcional"
      }
    }
  }
}
```

#### No Claude Code:
```bash
claude mcp add --env OPENALEX_API_KEY=sua-chave --transport stdio rslapp -- uvx rslapp
```

#### Conectar em 1 clique pelo Desktop:
Na tela **Conectar IA** do app desktop, você pode configurar o Claude Desktop e o Cursor automaticamente com um clique.

---

## Exemplos de Interação com a IA

Fale com sua IA em linguagem natural. Alguns fluxos recomendados:

- **Planejamento:** *"Monte um protocolo PICO para avaliar o impacto do feedback formativo mediado por IA na retenção escolar e gere a busca com descritores DeCS."*
- **Busca ampla:** *"Busque artigos sobre 'living systematic reviews' e metodologias ágeis de síntese de evidência no OpenAlex, PubMed e BDTD. Exporte a lista em RIS."*
- **Verificação:** *"Confira este parágrafo com citações contra a base da Crossref e me diga se alguma referência foi alucinada ou se algum estudo foi retratado."*
- **Triagem:** *"Trie os artigos da lista l-0005 com base nos critérios do protocolo e calcule a concordância Kappa de Cohen entre o revisor humano e as sugestões de IA."*
- **Textos completos:** *"Baixe os PDFs em acesso aberto de todos os estudos incluídos na lista l-0005 e liste o status do manifesto."*
- **Metanálise:** *"Extraia os dados amostrais e os desfechos de mortalidade dos ensaios clínicos da lista e gere a matriz de exportação para o pacote R metafor."*
- **Risco de Viés:** *"Aplique o instrumento Cochrane RoB 2 nos estudos incluídos e exiba o resumo com a matriz de semáforo."*
- **Reprodutibilidade:** *"Exporte o pacote completo de reprodutibilidade em .zip com hashes SHA-256 para depósito no OSF."*

---

## As 37 Ferramentas do Servidor MCP

O servidor MCP expõe 37 ferramentas auditáveis e estruturadas:

| Categoria | Ferramenta | O que faz |
|---|---|---|
| **Busca & Coleta** | `search_works` | Busca unificada em 8 bases com remoção de duplicatas e filtro de pareceres |
| | `find_work` | Localiza artigo por título exato ou DOI |
| | `get_related_works` | Recupera referências citadas ou trabalhos que citam um artigo |
| | `repeat_search` | Repete busca prévia a partir do log |
| | `get_list` | Consulta artigos de uma lista salva com paginação |
| | `get_search_log` | Recupera o histórico de buscas e caminho do `log.md` |
| | `merge_lists` | Junta múltiplas listas do mesmo tema sem duplicatas |
| | `list_sources` | Informa status e conectividade das bases de dados |
| | `import_works` | Importa arquivos externos (RIS, BibTeX, Scopus CSV, WoS TSV) |
| **Protocolo & Método**| `save_protocol` | Cria ou atualiza protocolo metodológico versionado (PICO, PCC, etc.) |
| | `get_protocol` | Recupera versão específica ou atual de um protocolo |
| | `list_protocols` | Lista todos os protocolos registrados |
| | `export_protocol_markdown`| Exporta protocolo em Markdown estruturado para PROSPERO/OSF |
| | `lookup_descriptors` | Busca descritores controlados DeCS/MeSH trilíngues |
| | `build_multilingual_search_query` | Monta strings de busca booleanas estruturadas |
| **Triagem & PRISMA** | `screen_work` | Registra decisão de triagem com motivo e rastro de autoria (`human`/`ai`) |
| | `get_screening_status` | Sumário quantitativo da triagem e motivos de exclusão |
| | `get_screening_concordance` | Calcula concordância Kappa de Cohen e lista divergências |
| | `get_prisma_flow` | Dados estruturados e métricas das 4 etapas do PRISMA 2020 |
| | `get_ai_disclosure` | Gera declaração metodológica de uso de IA (COPE/ICMJE/SciELO) |
| **Integridade** | `verify_references` | Valida listas de referências contra alucinações via Crossref e OpenAlex |
| **Textos & Fichas** | `fetch_fulltext` | Resolve e baixa PDF de acesso aberto via Unpaywall, PMC ou OpenAlex |
| | `get_fulltext_status` | Consulta manifesto de textos completos baixados |
| | `save_work_note` | Salva fichamento analítico com marcação de revisão humana |
| | `get_work_note` | Recupera ficha científica de um estudo |
| | `list_work_notes` | Lista fichamentos cadastrados para uma revisão |
| | `export_notes_markdown` | Exporta compilação de fichamentos em Markdown para Obsidian |
| **Metanálise & Viés** | `save_extraction_data` | Registra variáveis, intervenções e desfechos quantitativos |
| | `get_extraction_table` | Obtém tabela consolidada de extração de dados |
| | `export_extraction_csv` | Exporta matriz de dados para R `metafor` (`yi`, `vi`) ou RevMan 5 |
| | `save_risk_of_bias` | Registra avaliação Cochrane RoB 2, ROBINS-I ou JBI com julgamento global |
| | `get_risk_of_bias_summary` | Sumário de risco de viés e dados para matriz de semáforo |
| **Bibliometria & Redes**| `export_network` | Extrai e exporta redes de coautoria, periódicos e termos (VOSviewer / Gephi) |
| **Revisão Viva** | `compare_search_versions` | Compara duas versões de busca identificando artigos novos e retidos |
| | `update_search_differential` | Atualiza busca prévia em modo LSR gerando relatório diferencial |
| **Exportação & Pacote**| `export_list` | Exporta lista em RIS, CSV, JSON, DOIs, BibTeX, ABNT ou OpenAlex URL |
| | `export_reproducibility_package` | Gera pacote autocontido em `.zip` com manifesto de integridade SHA-256 |
| **Prompts MCP** | `plan_search` | Guia a IA no planejamento rigoroso da estratégia de busca |

---

## Compatibilidade com Ferramentas Externas

O RSL.app integra-se perfeitamente às ferramentas de pesquisa mais utilizadas:

| Ferramenta | Formato Gerado pelo RSL.app | Aplicação |
|---|---|---|
| **VOSviewer** | `.ris`, `.csv` (Scopus), `.map`, `.network`, `.dois.txt` | Mapas de coautoria, cocitação e acoplamento bibliográfico |
| **Gephi** | `.gexf` (Graph Exchange XML Format) | Análise avançada de redes complexas e métricas de centralidade |
| **R (`metafor` / `meta`)** | `.csv` (com colunas `yi`, `vi`, `ai, bi, ci, di, n1i, n2i`) | Metanálise de efeitos fixos e aleatórios, meta-regressão e forest plots |
| **RevMan 5 / Web** | `.csv` | Elaboração de revisões e metanálises da Colaboração Cochrane |
| **Zotero / Mendeley** | `.bib`, `.ris` | Gerenciamento de referências e citações no editor de texto |
| **Obsidian / Logseq** | `.md` (Markdown com frontmatter e fichas) | Gestão de conhecimento acadêmico e revisão temática |
| **Zenodo / OSF** | `.zip` (com `checksums.sha256`) | Depósito de dados de pesquisa e registro com DOI |

---

## Onde os Arquivos Ficam Armazenados

Por padrão, na pasta `~/RSL.app` (no Windows: `C:\Users\<seu-usuário>\RSL.app`, configurável via `RSL_DATA_DIR`):

```
RSL.app/
├── log.md                     # Registro cronológico auditável de buscas e operações
├── lists/                     # Metadados JSON completos de cada lista gerada
├── searches/                  # Parâmetros e strings originais enviadas a cada base
├── screening/                 # Decisões de triagem, motivos e autoria (humano vs. IA)
├── notes/                     # Fichamentos estruturados da leitura de artigos
├── protocols/                 # Protocolos metodológicos pré-busca e versionamento
├── differential/              # Comparações diferenciais de revisões vivas
├── fulltext/                  # Textos completos (PDFs) em Acesso Aberto baixados
├── exports/                   # Arquivos gerados (RIS, CSV, BibTeX, ABNT, VOSviewer, ZIP)
└── cache/                     # Cache local de respostas das APIs (expira em 7 dias)
```

---

## Configuração e Variáveis de Ambiente

Todas as configurações podem ser feitas pela tela **Configurações** do app desktop ou por variáveis de ambiente:

| Variável | Descrição | Padrão |
|---|---|---|
| `OPENALEX_API_KEY` | Chave gratuita do OpenAlex (10.000 créditos/dia) | Opcional (recomendada) |
| `SEMANTIC_SCHOLAR_API_KEY` | Chave gratuita da Semantic Scholar | Opcional |
| `NCBI_API_KEY` | Chave do NCBI para o PubMed (permite mais requisições/segundo) | Opcional |
| `SCOPUS_API_KEY` | Chave da Elsevier para o Scopus | Opcional (institucional) |
| `SCOPUS_INSTTOKEN` | Token institucional para Scopus fora da rede universitária | Opcional |
| `WOS_STARTER_API_KEY` | Chave da Web of Science Starter API (Clarivate) | Opcional |
| `RSL_CONTACT_EMAIL` | E-mail de contato cortês (Crossref, NCBI e Europe PMC) | Opcional |
| `RSL_DATA_DIR` | Diretório de armazenamento dos dados | `~/RSL.app` |
| `RSL_EXPORT_DIR` | Diretório destino dos arquivos exportados | `<RSL_DATA_DIR>/exports` |
| `RSL_CACHE_DAYS` | Validade do cache local das APIs (em dias) | `7` |

---

## Modo Hospedado (Multi-Usuário Institucional)

Uma universidade, laboratório ou grupo de pesquisa pode rodar o RSL.app em um servidor próprio compartilhado via **Docker** com HTTPS automático pelo **Caddy**:
- Login seguro por código pessoal gerado pelo administrador (`rslapp token add`).
- Dados e listas isolados por pesquisador, com cache compartilhado de APIs.
- Conexão direta por link HTTPS (`https://rsl.sua-universidade.br/mcp`) para Claude e ChatGPT.
- Veja o guia completo em [`docs/hospedagem.md`](docs/hospedagem.md).

---

## Dados Pessoais, Ética e LGPD

- O RSL.app armazena nomes públicos de autores, afiliações e identificadores ORCID fornecidos pelas próprias bases acadêmicas para viabilizar mapas de coautoria e análise bibliométrica.
- Os dados ficam **estritamente na sua máquina local**. O RSL.app não possui servidores centrais de coleta, não inclui telemetria oculta e não envia dados dos seus projetos a terceiros além das próprias bases consultadas.

---

## Para Desenvolvedores

```bash
git clone https://github.com/Erick-wilding675/RSL-MCP-APP.git
cd RSL-MCP-APP
uv run --extra dev ruff check .
uv run --extra dev python -m pytest tests/
uv run --extra desktop-dev --extra desktop pytest tests_desktop/
```

- Documentação de arquitetura, contratos e decisões: pasta [`docs/`](docs/).
- Estado do projeto e diário Blueprint: pasta [`.blueprint/`](.blueprint/).
- Stack: Python 3.10+, SDK oficial `mcp>=2,<3`, NiceGUI 2.x, HTTPX assíncrono.

---

## Licença

[MIT](LICENSE). Software livre e gratuito. Respeite os termos de uso e licenciamento de cada base de dados consultada.
