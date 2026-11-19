# RSL.app

[Português](README.md) | [English](README-en.md) | [Español](README-es.md) | [Français](README-fr.md)

**La plateforme complète, gratuite et auto-hébergée (self-hosted) pour les Revues Systématiques, la Méta-analyse et la Bibliométrie avec IA Traçable.**

**RSL.app** accompagne les chercheurs à chaque étape de leur revue systématique de la littérature : de l'élaboration du protocole initial jusqu'à l'extraction mathématique des données pour la méta-analyse. L'outil s'exécute **localement sur votre machine**, utilise vos propres clés API gratuites ou institutionnelles, se connecte à votre IA préférée via le protocole MCP (*Model Context Protocol*) et dispose d'une **application de bureau avec interface graphique moderne** pour Windows et Linux.

> **Fondement du Projet :** Donner toute sa puissance à la revue systématique grâce à l'IA propre au chercheur, avec une traçabilité et une reproductibilité auditables, en remplaçant la méfiance par une rigueur méthodologique conforme aux normes internationales (**PRISMA 2020**, **PRISMA-S**, **COPE**, **ICMJE** et **SciELO**).

---

## Le Cycle Complet de la Revue (Du Protocole à la Méta-Analyse)

RSL.app est bien plus qu'un simple moteur de recherche documentaire : c'est un atelier méthodologique complet comprenant 37 outils MCP et une interface graphique dédiée :

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 1. Planification│ ──> │ 2. Collecte &   │ ──> │ 3. Sélection &  │
│  & Protocoles   │     │ Dédoublonnage   │     │ Rastro & Kappa  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 6. Méta-analyse,│ <── │ 5. Textes OA &  │ <── │ 4. PRISMA 2020  │
│  Risque & Réseaux     │     Fiches      │     │ & Transparence  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 1. Planification Méthodologique et Vocabulaire Contrôlé
- **Protocoles pré-recherche versionnés :** Concevez, versionnez et exportez des protocoles structurés selon les cadres **PICO**, **PCC**, **PICo**, **SPIDER** ou Narratif, prêts pour l'enregistrement sur **PROSPERO** et l'**OSF**.
- **Descripteurs DeCS/MeSH trilingues :** Catalogue intégré de descripteurs contrôlés en français, anglais, portugais et espagnol avec synonymes officiels et générateur automatique d'équations de recherche booléennes.
- **Cadres méthodologiques spécialisés :** Directives et invites spécialisées pour les Revues Systématiques (Cochrane), les Revues de Portée / Scoping Reviews (JBI), les Revues Intégratives (Whittemore) et les Études Bibliométriques.

### 2. Recherche Exhaustive, Littérature Grise et Dédoublonnage
- **8 bases de données intégrées :** Interrogation simultanée et unifiée sur **OpenAlex**, **Crossref**, **Semantic Scholar**, **PubMed**, **Europe PMC**, **BDTD** (pour la littérature grise de thèses et mémoires), ainsi que **Scopus** et **Web of Science** (en utilisant les accès de votre établissement).
- **Filtre des rapports d'évaluation par les pairs :** Exclusion automatique des avis de relecture (*peer-reviews*, lettres de décision et correspondances éditoriales) qui polluent les résultats.
- **Dédoublonnage intelligent :** Fusion des doublons entre bases avec conservation des identifiants croisés et traçabilité des sources.
- **Importation de fichiers externes :** Importez des fichiers bibliographiques externes directement dans vos listes depuis des formats **RIS**, **BibTeX**, **CSV Scopus** et **TSV Web of Science**.
- **Revues Systématiques Vivantes (Living Systematic Reviews) :** Réexécutez vos recherches passées et identifiez automatiquement les nouvelles publications par rapport aux articles conservés, générant un rapport différentiel prêt pour publication.

### 3. Intégrité Scientifique et Double Sélection Traçable
- **Vérificateur d'hallucinations de références :** Validez vos listes de citations contre Crossref et OpenAlex pour détecter les références fictives ou les métadonnées divergentes générées par une IA.
- **Détection des rétractations :** Alertes visuelles et métadonnées pour les articles rétractés ou faisant l'objet d'un avis d'inquiétude (*expressions of concern*) via la base **Retraction Watch**.
- **Sélection documentaire avec traçabilité d'auteur :** Enregistrez les décisions d'inclusion (`included`), d'exclusion (`excluded`) ou d'indécision (`maybe`) avec justification formelle, en distinguant explicitement l'auteur de la décision (`human` vs. `ai`).
- **Raccourcis clavier ergonomiques :** Parcourez et sélectionnez des centaines d'articles au clavier (`I` pour inclure, `E` pour exclure, `M` pour indécis).
- **Accord inter-évaluateurs (Kappa de Cohen) :** Calcul automatisé du coefficient Kappa de Cohen avec échelle de Landis & Koch et identification des divergences pour résolution de consensus en double sélection à l'aveugle.

### 4. Rapport et Transparence Méthodologique
- **Diagramme de flux officiel PRISMA 2020 vectoriel (SVG) :** Diagramme vectoriel généré avec les chiffres réels de chaque étape (identification, dédoublonnage, sélection sur titre/résumé, éligibilité et inclusion finale).
- **Grille de contrôle PRISMA-S :** Rapport auditable consignant les dates, les équations exactes par base, les filtres et les volumes de notices.
- **Déclaration éthique d'usage de l'IA :** Génération automatique de déclaration de transparence méthodologique conforme aux recommandations internationales **COPE / ICMJE / SciELO**, en français, anglais et portugais.

### 5. Textes Intégraux Open Access et Fiches de Lecture
- **Téléchargement légal d'articles en Accès Ouvert (OA) :** Résolution et téléchargement par lots de PDFs en texte intégral légitime via **Unpaywall**, **PubMed Central (PMC)** et **OpenAlex OA**, validés par vérification binaire du format `%PDF`.
- **Fiches de lecture critique structurées :** Capture systématique des objectifs, méthodes, échantillons, résultats, limites et citations textuelles avec numéros de page, distinguant les suggestions d'IA des validations humaines.
- **Exportation pour Obsidian :** Exportez l'ensemble des fiches en Markdown structuré pour Obsidian, Logseq ou vos graphes de connaissances personnelles.

### 6. Synthèse, Méta-Analyse, Réseaux et Reproductibilité
- **Tableau d'extraction pour la Méta-Analyse :** Extraction structurée des types d'études (essais randomisés, cohortes, etc.), interventions, témoins et critères de jugement : dichotomiques (**Odds Ratio**, **Risque Relatif**) et continus (**Différence de Moyennes**, **Différence Moyenne Standardisée / Hedges' g**) avec intervalles de confiance à 95%.
- **Exportation native pour R `metafor` et RevMan :** Fichiers CSV prêts pour la modélisation statistique dans R (colonnes `yi`, `vi` et cellules de contingence 2x2) et le logiciel RevMan 5/Web de la Collaboration Cochrane.
- **Évaluation du Risque de Biais et de la Qualité :** Grilles d'évaluation **Cochrane RoB 2** (essais randomisés), **Cochrane ROBINS-I** (études non randomisées) et **JBI Critical Appraisal**, avec algorithme de jugement global et **matrice visuelle en feux tricolores** (*traffic-light plot*).
- **Réseaux bibliométriques natifs :** Génération directe de graphes de co-auteurs, de couplage bibliographique et de co-occurrence de mots-clés prêts pour **VOSviewer** (`.map`, `.network`) et **Gephi** (`.gexf`).
- **Paquet de Reproductibilité (.zip) :** Archive autonome regroupant l'ensemble des fichiers de la revue (métadonnées brutes, protocoles, recherches, décisions de sélection, fiches, extractions et évaluations du risque de biais) avec manifeste de hachages cryptographiques `checksums.sha256` pour dépôt sur **Zenodo** ou l'**OSF**.

---

## Guide d'Utilisation

RSL.app s'utilise de deux manières complémentaires :

### Option 1 : Application de Bureau (Interface Graphique)
Pour une utilisation visuelle et autonome :
1. Téléchargez l'exécutable autonome depuis la page des [Releases](https://github.com/Erick-wilding675/RSL-MCP-APP/releases) :
   - **Windows (x64) :** Téléchargez `RSL.app-<version>-windows-x64.zip`, décompressez et lancez `RSL.app.exe`.
   - **Linux (x86_64) :** Téléchargez `RSL.app-<version>-linux-x86_64.AppImage`, rendez-le exécutable (`chmod +x`) et lancez-le.
2. Ou installez-le via Python (3.10+) :
   ```bash
   pip install "rslapp[desktop]"
   rslapp-desktop
   ```
3. L'application propose des onglets dédiés pour : **Recherche**, **Liste d'articles**, **Sélection**, **PRISMA 2020**, **Extraction Méta-analyse**, **Risque de Biais**, **Fiches de Lecture**, **Directives Méthodologiques**, **Protocoles**, **Vérification de Références**, **Importer des Fichiers**, **Historique** et **Paramètres**.

### Option 2 : Serveur MCP (Connecté à votre IA)
Connectez directement RSL.app à Claude Desktop, Claude Code, Cursor, VS Code ou ChatGPT.

#### Configuration dans Claude Desktop (`claude_desktop_config.json`) :
```json
{
  "mcpServers": {
    "rslapp": {
      "command": "uvx",
      "args": ["rslapp"],
      "env": {
        "OPENALEX_API_KEY": "votre-cle-openalex",
        "SEMANTIC_SCHOLAR_API_KEY": "votre-cle-semantic-scholar",
        "SCOPUS_API_KEY": "votre-cle-scopus-optionnelle"
      }
    }
  }
}
```

#### En ligne de commande avec Claude Code :
```bash
claude mcp add --env OPENALEX_API_KEY=votre-cle --transport stdio rslapp -- uvx rslapp
```

#### Connexion en 1 Clic depuis le Bureau :
Dans l'onglet **Connecter l'IA** de l'application de bureau, configurez Claude Desktop et Cursor en un seul clic.

---

## Exemples d'Invites pour l'IA

Communiquez naturellement avec votre IA :

- **Planification :** *"Rédige un protocole PICO évaluant l'impact des retours formatifs médiatisés par l'IA sur la rétention scolaire et génère l'équation de recherche avec les descripteurs DeCS."*
- **Recherche globale :** *"Recherche des articles sur les revues systématiques vivantes (living systematic reviews) et la synthèse agile de données probantes dans OpenAlex, PubMed et BDTD. Exporte la liste dédoublonnée au format RIS."*
- **Contrôle d'intégrité :** *"Vérifie ce paragraphe contenant des citations contre la base Crossref et indique-moi si des références semblent inventées ou si des études ont été rétractées."*
- **Sélection :** *"Effectue la sélection des articles de la liste l-0005 selon nos critères d'éligibilité et calcule le coefficient Kappa de Cohen entre les choix humains et les suggestions d'IA."*
- **Texte intégral :** *"Télécharge les PDFs en accès ouvert de toutes les études incluses dans la liste l-0005 et affiche le statut du manifeste."*
- **Méta-analyse :** *"Extrais les effectifs d'échantillons et les données de mortalité des essais cliniques de la liste et prépare la matrice pour le package R metafor."*
- **Risque de biais :** *"Évalue les études incluses avec l'outil Cochrane RoB 2 et présente la matrice visuelle en feux tricolores."*
- **Reproductibilité :** *"Exporte le paquet complet de reproductibilité au format .zip avec les empreintes SHA-256 pour dépôt sur l'OSF."*

---

## Les 37 Outils du Serveur MCP

Le serveur MCP met à disposition 37 outils structurés et auditables :

| Catégorie | Outil | Description |
|---|---|---|
| **Recherche & Collecte** | `search_works` | Recherche unifiée sur 8 bases avec dédoublonnage et filtre d'évaluation |
| | `find_work` | Recherche un article spécifique par titre exact ou identifiant DOI |
| | `get_related_works` | Récupère les références citées ou les travaux citant une publication |
| | `repeat_search` | Réexécute une recherche passée enregistrée dans le journal |
| | `get_list` | Consulte les notices d'une liste enregistrée avec pagination |
| | `get_search_log` | Consulte l'historique d'audit des recherches et le fichier `log.md` |
| | `merge_lists` | Fusionne plusieurs listes sur un même sujet sans doublons |
| | `list_sources` | Indique l'état de fonctionnement et la connectivité des bases |
| | `import_works` | Importe des fichiers externes (RIS, BibTeX, CSV Scopus, TSV WoS) |
| **Protocole & Méthode**| `save_protocol` | Crée ou met à jour un protocole méthodologique versionné (PICO, PCC, etc.) |
| | `get_protocol` | Récupère une version active ou archivée d'un protocole |
| | `list_protocols` | Liste l'ensemble des protocoles méthodologiques enregistrés |
| | `export_protocol_markdown`| Exporte un protocole en Markdown structuré pour PROSPERO/OSF |
| | `lookup_descriptors` | Recherche des descripteurs contrôlés trilingues DeCS/MeSH |
| | `build_multilingual_search_query` | Construit des équations de recherche booléennes multilingues |
| **Sélection & PRISMA** | `screen_work` | Enregistre une décision de sélection avec justification et auteur (`human`/`ai`) |
| | `get_screening_status` | Synthèse quantitative de l'avancement et motifs d'exclusion |
| | `get_screening_concordance` | Calcule l'accord Kappa de Cohen et récapitule les divergences |
| | `get_prisma_flow` | Métriques structurées des 4 étapes du diagramme PRISMA 2020 |
| | `get_ai_disclosure` | Génère la déclaration méthodologique d'usage de l'IA (COPE/ICMJE/SciELO) |
| **Intégrité** | `verify_references` | Vérifie l'authenticité de listes de références via Crossref et OpenAlex |
| **Textes & Fiches** | `fetch_fulltext` | Résout et télécharge le PDF en accès ouvert via Unpaywall, PMC ou OpenAlex |
| | `get_fulltext_status` | Consulte le manifeste et l'état des téléchargements d'articles |
| | `save_work_note` | Enregistre une fiche d'analyse critique avec traçabilité de révision humaine |
| | `get_work_note` | Récupère la fiche de lecture d'une étude spécifique |
| | `list_work_notes` | Liste les fiches de lecture enregistrées pour une revue |
| | `export_notes_markdown` | Exporte l'ensemble des fiches en Markdown pour Obsidian |
| **Méta-Analyse & Biais**| `save_extraction_data` | Enregistre le protocole, l'échantillon, les interventions et critères de jugement |
| | `get_extraction_table` | Récupère le tableau consolidé d'extraction pour la méta-analyse |
| | `export_extraction_csv` | Exporte la matrice de données pour R `metafor` (`yi`, `vi`) ou RevMan 5 |
| | `save_risk_of_bias` | Enregistre l'évaluation Cochrane RoB 2, ROBINS-I ou JBI avec jugement global |
| | `get_risk_of_bias_summary` | Synthèse du risque de biais et données pour le graphique en feux tricolores |
| **Bibliométrie & Réseaux**| `export_network` | Génère des réseaux de co-auteurs, revues et termes (VOSviewer / Gephi) |
| **Revues Vivantes** | `compare_search_versions` | Compare deux recherches en identifiant les notices ajoutées et retenues |
| | `update_search_differential` | Met à jour une recherche en mode LSR avec rapport différentiel |
| **Exportation & Paquet**| `export_list` | Exporte une liste en RIS, CSV, JSON, DOIs, BibTeX, ABNT ou URL OpenAlex |
| | `export_reproducibility_package` | Génère l'archive `.zip` avec le manifeste cryptographique SHA-256 |
| **Invites MCP** | `plan_search` | Guide l'IA dans l'élaboration rigoureuse de la stratégie documentaire |

---

## Interopérabilité avec les Logiciels de Recherche

RSL.app communique naturellement avec les outils phares du milieu académique :

| Logiciel | Format Généré par RSL.app | Utilisation |
|---|---|---|
| **VOSviewer** | `.ris`, `.csv` (Scopus), `.map`, `.network`, `.dois.txt` | Cartographie de co-auteurs, co-citations et couplage bibliographique |
| **Gephi** | `.gexf` (Graph Exchange XML Format) | Analyse approfondie de réseaux complexes et métriques de centralité |
| **R (`metafor` / `meta`)** | `.csv` (avec `yi`, `vi`, `ai, bi, ci, di, n1i, n2i`) | Méta-analyse à effets fixes et aléatoires, méta-régression et forest plots |
| **RevMan 5 / Web** | `.csv` | Rédaction de revues systématiques et méta-analyses Cochrane |
| **Zotero / Mendeley** | `.bib`, `.ris` | Gestion documentaire et insertion de citations dans le traitement de texte |
| **Obsidian / Logseq** | `.md` (Markdown avec métadonnées et fiches) | Gestion des connaissances scientifiques et synthèse thématique |
| **Zenodo / OSF** | `.zip` (avec `checksums.sha256`) | Dépôt de données de recherche, science ouverte et attribution de DOI |

---

## Stockage et Organisation des Dossiers

Par défaut, l'ensemble des données est conservé localement dans `~/RSL.app` (sous Windows : `C:\Users\<utilisateur>\RSL.app`, paramétrable via `RSL_DATA_DIR`) :

```
RSL.app/
├── log.md                     # Journal chronologique auditable de l'ensemble des opérations
├── lists/                     # Données JSON exhaustives de chaque liste constituée
├── searches/                  # Paramètres et équations envoyés à chaque base
├── screening/                 # Décisions de sélection, motifs et attribution (`human`/`ai`)
├── notes/                     # Fiches de lecture critique structurées
├── protocols/                 # Protocoles méthodologiques préalables et versionnés
├── differential/              # Journaux de comparaison différentielle (revues vivantes)
├── fulltext/                  # Articles téléchargés en texte intégral Open Access (PDF)
├── exports/                   # Fichiers exportés (RIS, CSV, BibTeX, ABNT, VOSviewer, ZIP)
└── cache/                     # Cache local des réponses API (validité par défaut de 7 jours)
```

---

## Configuration et Variables d'Environnement

Le paramétrage s'effectue via l'onglet **Paramètres** de l'application de bureau ou par des variables d'environnement :

| Variable | Description | Valeur par défaut |
|---|---|---|
| `OPENALEX_API_KEY` | Clé API gratuite OpenAlex (10 000 requêtes/jour) | Optionnelle (Recommandée) |
| `SEMANTIC_SCHOLAR_API_KEY` | Clé API gratuite Semantic Scholar | Optionnelle |
| `NCBI_API_KEY` | Clé API NCBI pour PubMed (meilleur débit de requêtes) | Optionnelle |
| `SCOPUS_API_KEY` | Clé API Elsevier pour Scopus | Optionnelle (Institutionnelle) |
| `SCOPUS_INSTTOKEN` | Jeton institutionnel Scopus pour accès hors campus | Optionnelle |
| `WOS_STARTER_API_KEY` | Clave API Web of Science Starter (Clarivate) | Optionnelle |
| `RSL_CONTACT_EMAIL` | Adresse de contact courtois (Crossref, NCBI, Europe PMC) | Optionnelle |
| `RSL_DATA_DIR` | Répertoire de stockage des données | `~/RSL.app` |
| `RSL_EXPORT_DIR` | Répertoire de destination des exports | `<RSL_DATA_DIR>/exports` |
| `RSL_CACHE_DAYS` | Durée de conservation du cache local (en jours) | `7` |

---

## Hébergement Institutionnel Multi-Utilisateurs

Une université, un laboratoire ou un groupe de recherche peut déployer RSL.app sur un serveur institutionnel partagé sous **Docker** avec gestion automatique du HTTPS via **Caddy** :
- Authentification sécurisée par codes d'accès individuels créés par l'administrateur (`rslapp token add`).
- Données et listes isolées par chercheur, avec cache API mutualisé pour économiser les quotas.
- Accès direct via lien HTTPS (`https://rsl.votre-universite.fr/mcp`) pour Claude et ChatGPT sans installation locale.
- Consultez le guide complet et les mentions relatives à la protection des données dans [`docs/hospedagem.md`](docs/hospedagem.md).

---

## Protection des Données Personnelles et Éthique

- RSL.app enregistre les noms publics des auteurs, leurs affiliations et identifiants ORCID fournis par les bases bibliographiques exclusivement pour construire les réseaux de co-auteurs et les analyses bibliométriques.
- Vos données demeurent **strictement sur votre machine locale**. RSL.app ne comporte aucune télémétrie masquée, aucun traqueur central et ne transmet jamais vos données à des tiers autres que les APIs académiques interrogées.

---

## Pour les Développeurs

```bash
git clone https://github.com/Erick-wilding675/RSL-MCP-APP.git
cd RSL-MCP-APP
uv run --extra dev ruff check .
uv run --extra dev python -m pytest tests/
uv run --extra desktop-dev --extra desktop pytest tests_desktop/
```

- Documentation d'architecture, contrats d'interface et décisions : dossier [`docs/`](docs/).
- État du projet et journal Blueprint : dossier [`.blueprint/`](.blueprint/).
- Socle technique : Python 3.10+, SDK officiel `mcp>=2,<3`, NiceGUI 2.x, HTTPX asynchrone.

---

## Licence

[MIT](LICENSE). Logiciel libre et gratuit. Veillez à respecter les conditions d'utilisation et les licences propres à chaque base de données bibliographique consultée.
