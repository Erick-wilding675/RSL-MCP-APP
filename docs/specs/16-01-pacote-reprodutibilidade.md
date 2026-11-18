# Pacote de Reprodutibilidade Científica com Manifesto SHA-256

**Fase:** 16 · Versão 2.5 · **Situação:** pronta

## O que faz

Implementa no núcleo do RSL.app, no servidor MCP e no app desktop o gerador do **Pacote de Reprodutibilidade Científica** da revisão em formato `.zip` com garantia criptográfica de integridade (FR-28, D-039):

1. **Módulo no Núcleo (`src/rslapp/core/reproducibility.py`):**
   - Função `build_reproducibility_package(list_id: str, store: Store, export_dir: Path) -> dict[str, Any]`:
     - Compila em memória e empacota num arquivo `.zip` padronizado (`reproducibility_{list_id}.zip`):
       - `metadata.json`: metadados da busca, lista, query, total de artigos e versão do RSL.app;
       - `search_log.md`: extrato do log metodológico registrado no Store;
       - `works.csv`: exportação tabular completa de todos os artigos deduplicados;
       - `works.ris`: arquivo RIS para importação no VOSviewer, Zotero e Mendeley;
       - `works.bib`: arquivo BibTeX para LaTeX e gerenciadores bibliográficos;
       - `references_abnt.txt`: lista de referências formatada na ABNT NBR 6023:2018;
       - `screening.json`: decisões de triagem (inclusões, exclusões, motivos e autoria humano vs IA);
       - `prisma_2020.svg`: fluxograma vetorial PRISMA 2020 oficial com contagens reais;
       - `prisma_s_checklist.md`: checklist PRISMA-S de relato de buscas;
       - `ai_disclosure_pt.md`: declaração metodológica de uso de IA em português (COPE/ICMJE/SciELO);
       - `ai_disclosure_en.md`: declaração metodológica de uso de IA em inglês;
       - `checksums.sha256`: hashes SHA-256 de todos os arquivos internos no padrão Unix checksum (`<hash>  <filename>`).
     - Calcula o SHA-256 global do `.zip` gerado.

2. **Ferramenta MCP (`export_reproducibility_package`):**
   - Nome: `export_reproducibility_package`
   - Parâmetro: `list_id: str`
   - Resposta: dicionário com `path` (ou `download_url` no modo HTTP), `list_id`, `filename`, `file_count`, `size_bytes` e `sha256`.

3. **Interface Desktop (`rslapp.desktop`):**
   - Adiciona botão "Baixar Pacote de Reprodutibilidade (.zip)" na tela de Lista (`/lista/{list_id}`) e na tela PRISMA (`/prisma/{list_id}`).

## O que não faz

- Não envia dados para repositórios externos (o `.zip` é gerado localmente na máquina do pesquisador, pronto para upload no Zenodo, OSF ou DSpace institucional).
- Não requer dependências externas além da biblioteca padrão Python (`zipfile`, `hashlib`).

## Decisões desta spec

1. **Manifesto SHA-256 interno (D-039):** garante auditoria científica irrefutável e transparência em bancas de pós-graduação e periódicos científicos internacionais.
2. **Bundle autocontido:** todos os artefatos da revisão (metadados brutos, exportações, decisões de triagem, diagrama e declaração de IA) em um único download de 1 clique.

## Para instituições (D-029)

A biblioteca universitária ou repositório institucional (DSpace) pode receber o `.zip` diretamente como material suplementar da dissertação ou tese, com o hash SHA-256 garantindo a reprodutibilidade dos dados.

## Pronto quando

- [x] `src/rslapp/core/reproducibility.py` cria o pacote `.zip` completo com os 11 arquivos e `checksums.sha256`.
- [x] Ferramenta MCP `export_reproducibility_package` exposta no stdio e no servidor HTTP.
- [x] Botão de download integrado na interface desktop.
- [x] Testes unitários do núcleo e integração desktop passando.
- [x] Ruff check limpo.
