# RSL.app

[Português](README.md) | [English](README-en.md) | [Español](README-es.md) | [Français](README-fr.md)

**The complete, free, self-hosted platform for Systematic Literature Reviews, Meta-Analysis, and Bibliometrics with Traceable AI.**

**RSL.app** guides researchers through every stage of scientific literature reviews: from pre-search protocol design to mathematical data extraction for meta-analysis. It runs **locally on your machine**, uses your own free or institutional API keys, connects seamlessly to your preferred AI via the MCP (*Model Context Protocol*), and includes a **modern desktop GUI application** for Windows and Linux.

> **Project Foundation:** Elevate systematic reviews using the researcher's own AI with verifiable traceability and reproducibility, replacing skepticism with methodological rigor in compliance with international guidelines (**PRISMA 2020**, **PRISMA-S**, **COPE**, **ICMJE**, and **SciELO**).

---

## The Complete Review Lifecycle (From Protocol to Meta-Analysis)

RSL.app is far more than a simple paper search tool: it is a comprehensive methodological workstation featuring 37 MCP tools and a dedicated desktop application:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 1. Planning     │ ──> │ 2. Collection & │ ──> │ 3. Screening &  │
│  & Protocols    │     │ Deduplication   │     │ Cohen's Kappa   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 6. Meta-Analysis│ <── │ 5. Open Access  │ <── │ 4. PRISMA 2020  │
│  Risk & Networks│     │  PDFs & Notes   │     │ & Transparency  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 1. Methodological Planning & Controlled Vocabulary
- **Versioned Pre-Search Protocols:** Create, version, and export structured protocols in **PICO**, **PCC**, **PICo**, **SPIDER**, or Narrative frameworks, ready for registration on **PROSPERO** and **OSF**.
- **Trilingual DeCS/MeSH Descriptors:** Integrated catalog of authorized descriptors in Portuguese, English, and Spanish with official synonyms and automated Boolean query builder.
- **Specialized Guidelines:** Prompts and methodological frameworks for Systematic Reviews (Cochrane), Scoping Reviews (JBI), Integrative Reviews (Whittemore), and Bibliometric Studies.

### 2. Comprehensive Search, Grey Literature & Deduplication
- **8 Integrated Academic Databases:** Simultaneous, unified queries across **OpenAlex**, **Crossref**, **Semantic Scholar**, **PubMed**, **Europe PMC**, **BDTD** (Brazilian Digital Library of Theses and Dissertations for national grey literature), as well as **Scopus** and **Web of Science** (using your institution's credentials).
- **Peer-Review Filter:** Automated exclusion of peer-review reports, decision letters, and editorial correspondence that pollute search results.
- **Smart Deduplication:** Multi-source record linkage with cross-database ID mapping, preserving origin provenance.
- **External File Import:** Import external bibliographies directly into your lists from **RIS**, **BibTeX**, **Scopus CSV**, and **Web of Science TSV**.
- **Living Systematic Reviews (LSR):** Re-run past queries and automatically identify new versus retained publications, generating differential methodological reports for defense and publication updates.

### 3. Scientific Integrity & Traceable Dual Screening
- **Citation Hallucination Verifier:** Validate pasted or AI-generated reference lists against Crossref and OpenAlex, flagging fictional citations and discrepant metadata.
- **Retraction Detection:** Visual warnings and metadata badges for retracted articles or expressions of concern sourced from the **Retraction Watch** database.
- **Traceable Screening:** Record screening decisions (`included`, `excluded`, `maybe`) with formal exclusion rationales, clearly distinguishing human versus AI authorship (`human` vs. `ai`).
- **Rapid Desktop Shortcuts:** Navigate and screen hundreds of papers using ergonomic keyboard hotkeys (`I` for include, `E` for exclude, `M` for maybe).
- **Inter-Rater Agreement (Cohen's Kappa):** Automated calculation of Cohen's Kappa with Landis & Koch classification and divergent item listing for consensus resolution in blind dual screening.

### 4. Reporting & Methodological Transparency
- **Official Vectorial PRISMA 2020 Flowchart (SVG):** Precision SVG diagrams generated with exact empirical counts across all 4 stages (identification, deduplication, title/abstract screening, eligibility, and final inclusion).
- **PRISMA-S Checklist:** Audit-ready report tracking database queries, exact dates, search strings, filters, and record counts.
- **AI Ethics Disclosure:** Automated statement of AI methodological transparency compliant with **COPE / ICMJE / SciELO** standards, in Portuguese and English.

### 5. Open Access Full-Text Retrieval & Structured Notes
- **Legal Open Access PDF Downloader:** Automated resolution and batch downloading of legitimate full-text PDFs via **Unpaywall**, **PubMed Central (PMC)**, and **OpenAlex OA**, verified with binary `%PDF` header validation.
- **Structured Critical Appraisal Notes:** Systematic capture of study objectives, methods, sample size, findings, limitations, and verbatim quotes with page numbers, distinguishing AI drafts from human-verified notes.
- **Obsidian Markdown Export:** Compile all study notes into structured Markdown files ready for Obsidian, Logseq, or personal knowledge graphs.

### 6. Synthesis, Meta-Analysis, Networks & Reproducibility
- **Meta-Analysis Extraction Table:** Structured extraction of study designs (RCT, cohort, case-control, etc.), interventions, controls, and outcomes: dichotomous (**Odds Ratio**, **Risk Ratio**) and continuous (**Mean Difference**, **Standardized Mean Difference / Hedges' g**) with 95% confidence intervals.
- **Native R `metafor` & RevMan Export:** Direct CSV export tailored for R statistical modeling (with `yi`, `vi`, and 2x2 contingency cells) and Cochrane's RevMan 5/Web.
- **Risk of Bias & Methodological Quality:** Assessment instruments for **Cochrane RoB 2** (randomized trials), **Cochrane ROBINS-I** (non-randomized studies), and **JBI Critical Appraisal**, featuring deterministic overall risk calculation and visual **traffic-light matrix plots**.
- **Native Bibliometric Networks:** Direct graph generation for co-authorship, journal coupling, and term co-occurrence ready for **VOSviewer** (`.map`, `.network`) and **Gephi** (`.gexf`).
- **Reproducibility Package (.zip):** Self-contained archive packaging all review artifacts (raw metadata, protocols, queries, screening logs, appraisal notes, meta-analysis tables, and quality assessments) with a `checksums.sha256` cryptographic manifest for **Zenodo** or **OSF** deposition.

---

## How to Use

RSL.app can be used in two complementary ways:

### Option 1: Desktop Application (Graphical Interface)
For a visual, zero-configuration experience:
1. Download the pre-built standalone executable from the [Releases](https://github.com/Erick-wilding675/RSL-MCP-APP/releases) page:
   - **Windows (x64):** Download `RSL.app-<version>-windows-x64.zip`, extract, and launch `RSL.app.exe`.
   - **Linux (x86_64):** Download `RSL.app-<version>-linux-x86_64.AppImage`, make it executable (`chmod +x`), and run.
2. Or install via Python (3.10+):
   ```bash
   pip install "rslapp[desktop]"
   rslapp-desktop
   ```
3. The interface includes dedicated tabs for: **Search**, **List View**, **Screening**, **PRISMA 2020**, **Meta-Analysis Extraction**, **Risk of Bias**, **Critical Appraisal Notes**, **Methodological Guidelines**, **Protocols**, **Reference Verifier**, **Import Files**, **History**, and **Settings**.

### Option 2: MCP Server (Connected to Your AI)
Connect RSL.app directly to Claude Desktop, Claude Code, Cursor, VS Code, or ChatGPT.

#### Claude Desktop Configuration (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "rslapp": {
      "command": "uvx",
      "args": ["rslapp"],
      "env": {
        "OPENALEX_API_KEY": "your-openalex-key",
        "SEMANTIC_SCHOLAR_API_KEY": "your-semantic-scholar-key",
        "SCOPUS_API_KEY": "your-optional-scopus-key"
      }
    }
  }
}
```

#### Claude Code CLI:
```bash
claude mcp add --env OPENALEX_API_KEY=your-key --transport stdio rslapp -- uvx rslapp
```

#### One-Click AI Connection from Desktop:
Inside the desktop app's **Connect AI** page, you can configure Claude Desktop and Cursor with a single click.

---

## Example AI Prompts

Interact with your AI naturally:

- **Planning:** *"Draft a PICO protocol evaluating the impact of AI-mediated formative feedback on student retention and generate the query using DeCS descriptors."*
- **Broad Search:** *"Search for articles on 'living systematic reviews' and agile evidence synthesis in OpenAlex, PubMed, and BDTD. Export the deduplicated list to RIS."*
- **Integrity Check:** *"Verify this cited paragraph against Crossref and notify me if any citation appears hallucinated or if any paper was retracted."*
- **Screening:** *"Screen the articles in list l-0005 against our protocol criteria and calculate Cohen's Kappa agreement between human decisions and AI suggestions."*
- **Full Text:** *"Download open-access full-text PDFs for all included studies in list l-0005 and report download manifest status."*
- **Meta-Analysis:** *"Extract sample sizes and mortality outcomes for clinical trials in the list and export the dataset for the R metafor package."*
- **Risk of Bias:** *"Assess the included studies using the Cochrane RoB 2 tool and display the traffic-light summary plot."*
- **Reproducibility:** *"Export the complete reproducibility package in .zip format with SHA-256 hashes for deposition on OSF."*

---

## All 37 MCP Server Tools

The MCP server provides 37 auditable, structured tools:

| Category | Tool | Description |
|---|---|---|
| **Search & Harvest** | `search_works` | Multi-source search across 8 databases with deduplication and review filter |
| | `find_work` | Locate a specific paper by exact title or DOI |
| | `get_related_works` | Retrieve cited references or citing works for a given paper |
| | `repeat_search` | Re-execute a historical search from the log |
| | `get_list` | Inspect papers within a saved list with pagination |
| | `get_search_log` | Retrieve search log audit trail and path to `log.md` |
| | `merge_lists` | Merge multiple topic-related lists into one without duplicates |
| | `list_sources` | Report connectivity and status of all database connectors |
| | `import_works` | Import external files (RIS, BibTeX, Scopus CSV, WoS TSV) |
| **Protocols & Method**| `save_protocol` | Create or update versioned methodology protocols (PICO, PCC, etc.) |
| | `get_protocol` | Retrieve a specific or active protocol version |
| | `list_protocols` | List all registered methodology protocols |
| | `export_protocol_markdown`| Export structured protocol Markdown for PROSPERO/OSF |
| | `lookup_descriptors` | Search controlled trilingual DeCS/MeSH descriptors |
| | `build_multilingual_search_query` | Construct structured multi-language Boolean search queries |
| **Screening & PRISMA**| `screen_work` | Record screening decision with rationale and author attribution (`human`/`ai`) |
| | `get_screening_status` | Quantitative summary of screening progress and exclusion reasons |
| | `get_screening_concordance` | Calculate Cohen's Kappa inter-rater agreement and list divergences |
| | `get_prisma_flow` | Structured metrics across all 4 stages of PRISMA 2020 |
| | `get_ai_disclosure` | Generate AI methodology disclosure statement (COPE/ICMJE/SciELO) |
| **Integrity** | `verify_references` | Verify reference lists against hallucinations via Crossref and OpenAlex |
| **Full-Text & Notes** | `fetch_fulltext` | Resolve and download open-access PDF via Unpaywall, PMC, or OpenAlex |
| | `get_fulltext_status` | Inspect manifest and download status of full-text PDFs |
| | `save_work_note` | Save critical appraisal note with human validation tracking |
| | `get_work_note` | Retrieve appraisal note for a specific study |
| | `list_work_notes` | List all notes recorded for a review list |
| | `export_notes_markdown` | Export compiled review notes to Markdown for Obsidian |
| **Meta-Analysis & Bias**| `save_extraction_data` | Record study design, sample size, intervention, control, and outcomes |
| | `get_extraction_table` | Retrieve consolidated extraction table for meta-analysis |
| | `export_extraction_csv` | Export extraction matrix to R `metafor` (`yi`, `vi`) or RevMan 5 format |
| | `save_risk_of_bias` | Record Cochrane RoB 2, ROBINS-I, or JBI assessment with overall judgment |
| | `get_risk_of_bias_summary` | Risk of bias summary and traffic-light plot data |
| **Bibliometrics** | `export_network` | Extract and export co-authorship, journal, and keyword networks (VOSviewer / Gephi) |
| **Living Reviews** | `compare_search_versions` | Compare two search versions identifying added and retained records |
| | `update_search_differential` | Update past search in LSR mode generating differential report |
| **Export & Package** | `export_list` | Export list to RIS, CSV, JSON, DOIs, BibTeX, ABNT, or OpenAlex URL |
| | `export_reproducibility_package` | Build self-contained `.zip` package with SHA-256 cryptographic manifest |
| **MCP Prompts** | `plan_search` | Guide AI in rigorous systematic search planning |

---

## Interoperability with External Research Tools

RSL.app integrates seamlessly with established scientific software:

| Tool | Format Produced | Application |
|---|---|---|
| **VOSviewer** | `.ris`, `.csv` (Scopus), `.map`, `.network`, `.dois.txt` | Co-authorship, co-citation, and bibliographic coupling network visualization |
| **Gephi** | `.gexf` (Graph Exchange XML Format) | Complex network analysis and centrality metrics |
| **R (`metafor` / `meta`)** | `.csv` (with `yi`, `vi`, `ai, bi, ci, di, n1i, n2i`) | Fixed and random-effects meta-analysis, meta-regression, and forest plots |
| **RevMan 5 / Web** | `.csv` | Cochrane systematic review and meta-analysis authoring |
| **Zotero / Mendeley** | `.bib`, `.ris` | Reference management and in-text citation workflows |
| **Obsidian / Logseq** | `.md` (Markdown with frontmatter and notes) | Personal academic knowledge management and thematic synthesis |
| **Zenodo / OSF** | `.zip` (with `checksums.sha256`) | Research data deposit, open science compliance, and DOI assignment |

---

## Storage & Directory Layout

By default, all data is stored locally in `~/RSL.app` (on Windows: `C:\Users\<username>\RSL.app`, configurable via `RSL_DATA_DIR`):

```
RSL.app/
├── log.md                     # Human-readable, audit-ready chronological search log
├── lists/                     # Complete JSON metadata of all generated lists
├── searches/                  # Raw parameters and queries sent to each database
├── screening/                 # Screening decisions, exclusion reasons, and authorship
├── notes/                     # Structured critical appraisal notes
├── protocols/                 # Versioned pre-search methodology protocols
├── differential/              # Living review differential comparison logs
├── fulltext/                  # Downloaded Open Access full-text PDF files
├── exports/                   # Exported files (RIS, CSV, BibTeX, ABNT, VOSviewer, ZIP)
└── cache/                     # Local API response cache (7-day default expiration)
```

---

## Configuration & Environment Variables

Configure via the desktop app's **Settings** screen or standard environment variables:

| Variable | Description | Default |
|---|---|---|
| `OPENALEX_API_KEY` | Free OpenAlex API key (10,000 credits/day) | Optional (Recommended) |
| `SEMANTIC_SCHOLAR_API_KEY` | Free Semantic Scholar API key | Optional |
| `NCBI_API_KEY` | NCBI API key for PubMed (higher rate limits) | Optional |
| `SCOPUS_API_KEY` | Elsevier API key for Scopus | Optional (Institutional) |
| `SCOPUS_INSTTOKEN` | Scopus Institutional Token for off-campus queries | Optional |
| `WOS_STARTER_API_KEY` | Clarivate Web of Science Starter API key | Optional |
| `RSL_CONTACT_EMAIL` | Polite contact email (sent to Crossref, NCBI, Europe PMC) | Optional |
| `RSL_DATA_DIR` | Base directory for storing lists, logs, and cache | `~/RSL.app` |
| `RSL_EXPORT_DIR` | Output directory for exported files | `<RSL_DATA_DIR>/exports` |
| `RSL_CACHE_DAYS` | Cache retention lifetime in days | `7` |

---

## Multi-User Institutional Hosting

Universities, research groups, or laboratories can self-host RSL.app on an institutional server using **Docker** with automated HTTPS via **Caddy**:
- Secure login with personal access codes generated by the admin (`rslapp token add`).
- User-isolated lists and logs with a shared, quota-saving API cache.
- Direct HTTPS link (`https://rsl.your-institution.edu/mcp`) for connecting Claude and ChatGPT without local client installs.
- Detailed step-by-step instructions and data protection considerations in [`docs/hospedagem.md`](docs/hospedagem.md).

---

## Privacy, Ethics & Data Governance

- RSL.app stores public author names, affiliations, and ORCID identifiers retrieved from open bibliographic databases solely to enable co-authorship mapping and bibliometric analysis.
- All project data remains **strictly on your local machine**. RSL.app has no telemetry, tracking, or centralized cloud collection, and never transmits your data to third parties other than the queried academic APIs.

---

## For Developers

```bash
git clone https://github.com/Erick-wilding675/RSL-MCP-APP.git
cd RSL-MCP-APP
uv run --extra dev ruff check .
uv run --extra dev python -m pytest tests/
uv run --extra desktop-dev --extra desktop pytest tests_desktop/
```

- Architectural documentation, interface contracts, and decisions: [`docs/`](docs/).
- Project state and Blueprint journal: [`.blueprint/`](.blueprint/).
- Stack: Python 3.10+, official SDK `mcp>=2,<3`, NiceGUI 2.x, asynchronous HTTPX.

---

## License

[MIT](LICENSE). Free and open-source software. Please respect the individual terms of service and licensing of each consulted bibliographic database.
