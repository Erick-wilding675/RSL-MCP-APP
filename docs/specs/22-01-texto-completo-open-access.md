# Texto Completo Legal em Acesso Aberto (22-01)

Permite que o pesquisador recupere automaticamente os artigos completos em PDF de acesso aberto (Open Access legal, sem Sci-Hub) a partir dos identificadores da lista (DOI, PMCID, OpenAlex ID) e salve-os organizados na pasta da revisão (FR-34, D-045).

## Contexto e Fundamento
- **Fundamento:** Na etapa de triagem por texto completo e fichamento analítico, o pesquisador precisa ler os artigos na íntegra. Baixar manualmente dezenas de PDFs toma horas e quebra o fluxo de trabalho.
- **Fontes legais abertas:**
  - OpenAlex: campos `open_access.oa_url` e `best_oa_location.pdf_url`.
  - Unpaywall API: `https://api.unpaywall.org/v2/{doi}?email={email}` para resolução de DOIs abertos em repositórios institucionais e periódicos híbridos/gold.
  - Europe PMC / PubMed Central: `https://www.ebi.ac.uk/europepmc/webservices/rest/{id}/fullTextXML` e link direto de PDF para artigos no PMC Open Access subset.
- **Rigor legal:** Nunca utiliza Sci-Hub ou métodos de evasão de paywall. Quando o artigo for fechado (paywall), marca explicitamente como `restricted_paywall` com link para a página oficial do editor.

## O que faz
1. **Módulo `rslapp.core.fulltext`:**
   - Função `resolve_open_access_pdf(work: Work, email: str | None = None, client: httpx.AsyncClient | None = None) -> FullTextInfo`:
     - Tenta resolver a URL direta do PDF a partir dos dados do Work (OpenAlex `source_ids`, URLs associadas).
     - Se houver DOI, consulta Unpaywall API com email de contato (usando `RSL_CONTACT_EMAIL` ou email padrão de cortesia acadêmica).
     - Se houver PubMed Central ID / Europe PMC ID, tenta a URL direta de PDF do PMC.
   - Função `download_fulltext_pdf(pdf_url: str, dest_path: Path, client: httpx.AsyncClient | None = None) -> bool`:
     - Baixa o PDF com validação do cabeçalho binário `%PDF` para garantir que a resposta não é uma página HTML de login/erro.
     - Grava atomicamente no destino `data_dir / "fulltext" / {list_id} / {work_id}.pdf`.
   - Modelo `FullTextRecord`:
     - `work_id: str`
     - `status: str` (`available`, `downloaded`, `restricted_paywall`, `not_found`)
     - `oa_url: str | None`
     - `pdf_path: str | None`
     - `license: str | None`
     - `repository: str | None`
     - `checked_at: str` (ISO 8601)

2. **Persistência no Store:**
   - Pasta `data_dir / "fulltext" / {list_id}`.
   - Arquivo de manifesto `manifest.json` com o estado de todos os artigos da lista.

## Para instituições (D-029)
Universidades que promovem a ciência aberta podem orientar seus pesquisadores a usar a ferramenta para auditoria de conformidade com mandatos de Open Access (como CAPES, FAPESP e cOAlition S / Plan S).

## Pronto quando
- Testes unitários cobrindo resolução OpenAlex, Unpaywall e PMC com MockTransport.
- Validação de integridade de cabeçalho `%PDF`.
- Registro atômico no manifesto e no disco.
