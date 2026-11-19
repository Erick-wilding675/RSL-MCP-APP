# RSL.app

[Português](README.md) | [English](README-en.md) | [Español](README-es.md) | [Français](README-fr.md)

**La plataforma completa, gratuita y autohospedada (self-hosted) para Revisiones Sistemáticas, Metaanálisis y Bibliometría con IA Rastreable.**

**RSL.app** acompaña al investigador en todas las fases de una revisión científica de la literatura: desde el diseño del protocolo previo a la búsqueda hasta la extracción matemática de datos para metaanálisis. Se ejecuta **localmente en tu máquina**, utiliza tus propias claves API gratuitas o institucionales, se conecta a tu IA favorita a través del protocolo MCP (*Model Context Protocol*) y ofrece una **aplicación de escritorio con interfaz gráfica moderna** para Windows y Linux.

> **Fundamento del Proyecto:** Elevar la revisión sistemática con la IA del propio investigador, con trazabilidad y reproducibilidad auditables, reemplazando la desconfianza por rigor metodológico en conformidad con las directrices internacionales (**PRISMA 2020**, **PRISMA-S**, **COPE**, **ICMJE** y **SciELO**).

---

## El Ciclo Completo de la Revisión (Del Protocolo al Metaanálisis)

RSL.app es mucho más que un buscador de artículos: es una estación metodológica integral con 37 herramientas MCP e interfaz gráfica dedicada:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 1. Planificación│ ──> │ 2. Recolección &│ ──> │ 3. Cribado con  │
│  & Protocolos   │     │ Desduplicación  │     │ Rastro & Kappa  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 6. Metaanálisis,│ <── │ 5. Textos OA &  │ <── │ 4. PRISMA 2020  │
│ Riesgo & Redes  │     │ Fichas de Lect. │     │ & Transparencia │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 1. Planificación Metodológica y Vocabulario Controlado
- **Protocolos previos a la búsqueda versionados:** Diseñe, versione y exporte protocolos en marcos metodológicos estructurados (**PICO**, **PCC**, **PICo**, **SPIDER** o Narrativo), listos para registrar en **PROSPERO** y **OSF**.
- **Descriptores DeCS/MeSH trilingües:** Catálogo integrado de descriptores autorizados en español, portugués e inglés con sinónimos oficiales y constructor automático de ecuaciones de búsqueda booleanas.
- **Guías especializadas:** Prompts y directrices metodológicas para Revisiones Sistemáticas (Cochrane), Revisiones de Alcance (JBI), Revisiones Integrativas (Whittemore) y Estudios Bibliométricos.

### 2. Búsqueda Exhaustiva, Literatura Gris y Desduplicación
- **8 bases de datos integradas:** Consulta unificada y simultánea en **OpenAlex**, **Crossref**, **Semantic Scholar**, **PubMed**, **Europe PMC**, **BDTD** (para literatura gris de tesis y disertaciones), además de **Scopus** y **Web of Science** (utilizando las credenciales de su institución).
- **Filtro de informes de revisión:** Exclusión automática de informes de revisión por pares (*peer-reviews*, cartas de decisión y correspondencia editorial) que ensucian los resultados.
- **Desduplicación inteligente:** Unificación de registros duplicados entre bases, preservando identificadores cruzados y fuentes de procedencia.
- **Importación de archivos externos:** Importe bibliografías externas directamente a sus listas desde archivos **RIS**, **BibTeX**, **Scopus CSV** y **Web of Science TSV**.
- **Revisiones Sistemáticas Vivas (Living Systematic Reviews):** Reejecute búsquedas pasadas y detecte automáticamente artículos nuevos frente a retenidos, generando informes metodológicos diferenciales para defensas de tesis o actualizaciones de artículos.

### 3. Integridad Científica y Doble Cribado Rastreable
- **Verificador de alucinaciones de citas:** Compruebe listas de referencias contra Crossref y OpenAlex, identificando citas ficticias o discrepancias en metadados generadas por IA.
- **Detección de retractaciones:** Advertencias visuales y metadados para artículos retractados o con expresiones de preocupación provenientes de la base de datos **Retraction Watch**.
- **Cribado con rastro de autoría:** Registre decisiones de inclusión (`included`), exclusión (`excluded`) o duda (`maybe`) con motivos formales, distinguiendo expresamente quién decidió (`human` vs. `ai`).
- **Atajos rápidos de teclado en escritorio:** Navegue y cribe cientos de artículos con teclas ergonómicas (`I` para incluir, `E` para excluir, `M` para duda).
- **Concordancia entre evaluadores (Kappa de Cohen):** Cálculo automatizado del Kappa de Cohen con clasificación de Landis & Koch y lista detallada de discrepancias para resolución de consenso en doble cribado ciego.

### 4. Informe y Transparencia Metodológica
- **Diagrama de flujo oficial PRISMA 2020 vectorial (SVG):** Diagrama vectorial generado con las cifras empíricas reales de cada etapa (identificación, desduplicación, cribado por título/resumen, elegibilidad e inclusión final).
- **Lista de comprobación PRISMA-S:** Informe auditable con fechas exactas, ecuaciones de búsqueda por base, filtros aplicados y recuentos.
- **Declaración ética de uso de IA:** Generación automatizada de declaración de transparencia metodológica según los estándares **COPE / ICMJE / SciELO**, en español, inglés y portugués.

### 5. Textos Completos en Acceso Abierto y Fichas Analíticas
- **Descarga legal de PDFs en Acceso Abierto (OA):** Resolución automatizada y descarga en lote de textos completos legítimos a través de **Unpaywall**, **PubMed Central (PMC)** y **OpenAlex OA**, con validación binaria de cabecera `%PDF`.
- **Fichas de lectura crítica estructuradas:** Registro sistemático de objetivos, metodología, muestra, resultados, limitaciones y citas textuales con número de página, diferenciando borradores de IA de validaciones humanas.
- **Exportación para Obsidian:** Exporte todas las fichas de lectura en formato Markdown estructurado para Obsidian, Logseq o grafos de conocimiento personal.

### 6. Síntesis, Metaanálisis, Redes y Reproducibilidad
- **Tabla de extracción para Metaanálisis:** Extracción de diseños de estudio (ensayos clínicos, cohortes, casos y controles), intervenciones, controles y desenlaces: dicotómicos (**Odds Ratio**, **Riesgo Relativo**) y continuos (**Diferencia de Medias**, **Diferencia de Medias Estandarizada / Hedges' g**) con intervalos de confianza del 95%.
- **Exportación nativa para R `metafor` y RevMan:** Exportación directa a CSV diseñada para modelado estadístico en R (columnas `yi`, `vi` o tablas 2x2) y RevMan 5/Web de Cochrane.
- **Evaluación de Riesgo de Sesgo y Calidad:** Instrumentos **Cochrane RoB 2** (ensayos aleatorizados), **Cochrane ROBINS-I** (estudios no aleatorizados) y **JBI Critical Appraisal**, con cálculo determinista del juicio global y **matriz visual de semáforo** (*traffic-light plot*).
- **Redes bibliométricas nativas:** Generación directa de grafos de coautoría, acoplamiento de revistas y coocurrencia de palabras clave listos para **VOSviewer** (`.map`, `.network`) y **Gephi** (`.gexf`).
- **Paquete de Reproducibilidad (.zip):** Archivo autocontenido con todos los artefactos de la revisión (metadados crudos, protocolos, búsquedas, cribados, fichas, metaanálisis y riesgo de sesgo) y manifiesto con sumas de comprobación criptográficas `checksums.sha256` para depósito en **Zenodo** o **OSF**.

---

## Cómo Utilizarlo

RSL.app puede utilizarse de dos formas complementarias:

### Opción 1: Aplicación de Escritorio (Interfaz Gráfica)
Para una experiencia visual directa y sin intermediarios:
1. Descargue el ejecutable desde la página de [Releases](https://github.com/Erick-wilding675/RSL-MCP-APP/releases):
   - **Windows (x64):** Descargue `RSL.app-<versión>-windows-x64.zip`, descomprima y abra `RSL.app.exe`.
   - **Linux (x86_64):** Descargue `RSL.app-<versión>-linux-x86_64.AppImage`, asigne permisos de ejecución (`chmod +x`) y ejecute.
2. O instálelo vía Python (3.10+):
   ```bash
   pip install "rslapp[desktop]"
   rslapp-desktop
   ```
3. La interfaz cuenta con pestañas dedicadas para: **Buscar**, **Lista de Artículos**, **Cribado**, **PRISMA 2020**, **Extracción Metaanálisis**, **Riesgo de Sesgo**, **Fichas de Lectura**, **Guías Metodológicas**, **Protocolos**, **Verificar Citas**, **Importar Archivos**, **Historial** y **Configuración**.

### Opción 2: Servidor MCP (Conectado a su IA)
Conecte RSL.app directamente a Claude Desktop, Claude Code, Cursor, VS Code o ChatGPT.

#### Configuración en Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "rslapp": {
      "command": "uvx",
      "args": ["rslapp"],
      "env": {
        "OPENALEX_API_KEY": "su-clave-de-openalex",
        "SEMANTIC_SCHOLAR_API_KEY": "su-clave-de-semantic-scholar",
        "SCOPUS_API_KEY": "su-clave-scopus-opcional"
      }
    }
  }
}
```

#### En Claude Code:
```bash
claude mcp add --env OPENALEX_API_KEY=su-clave --transport stdio rslapp -- uvx rslapp
```

#### Conexión en 1 Clic desde el Escritorio:
En la pantalla **Conectar IA** de la aplicación de escritorio, puede configurar Claude Desktop y Cursor de forma automática con un solo clic.

---

## Ejemplos de Interacción con la IA

Hable con su IA en lenguaje natural:

- **Planificación:** *"Diseña un protocolo PICO para evaluar el impacto de la retroalimentación formativa mediada por IA en la retención académica y genera la búsqueda con descriptores DeCS."*
- **Búsqueda amplia:** *"Busca artículos sobre 'living systematic reviews' y síntesis ágil de evidencia en OpenAlex, PubMed y BDTD. Exporta la lista desduplicada en formato RIS."*
- **Verificación:** *"Verifica este párrafo citado contra Crossref y avísame si alguna referencia parece inventada o si algún artículo ha sido retractado."*
- **Cribado:** *"Criba los artículos de la lista l-0005 según los criterios del protocolo y calcula la concordancia Kappa de Cohen entre decisiones humanas y sugerencias de la IA."*
- **Textos completos:** *"Descarga los PDFs en acceso abierto de todos los estudios incluidos en la lista l-0005 y muestra el estado del manifiesto."*
- **Metaanálisis:** *"Extrae los tamaños muestrales y desenlaces de mortalidad de los ensayos clínicos de la lista y exporta los datos para el paquete R metafor."*
- **Riesgo de sesgo:** *"Evalúa los estudios incluidos con la herramienta Cochrane RoB 2 y muestra la matriz de semáforo resultante."*
- **Reproducibilidad:** *"Exporta el paquete de reproducibilidad completo en formato .zip con hashes SHA-256 para depositarlo en OSF."*

---

## Las 37 Herramientas del Servidor MCP

El servidor MCP ofrece 37 herramientas auditables y estructuradas:

| Categoría | Herramienta | Descripción |
|---|---|---|
| **Búsqueda & Recolección** | `search_works` | Búsqueda unificada en 8 bases con desduplicación y filtro de revisiones |
| | `find_work` | Localiza un artículo específico por título exacto o DOI |
| | `get_related_works` | Obtiene referencias citadas o trabajos que citan un artículo |
| | `repeat_search` | Repite una búsqueda histórica registrada en el log |
| | `get_list` | Consulta artículos de una lista guardada con paginación |
| | `get_search_log` | Recupera el registro cronológico de auditoría y ruta de `log.md` |
| | `merge_lists` | Une varias listas del mismo tema sin duplicados |
| | `list_sources` | Informa del estado y conectividad de los conectores de bases |
| | `import_works` | Importa archivos externos (RIS, BibTeX, Scopus CSV, WoS TSV) |
| **Protocolo & Método**| `save_protocol` | Crea o actualiza protocolos metodológicos versionados (PICO, PCC, etc.) |
| | `get_protocol` | Recupera una versión específica o activa de un protocolo |
| | `list_protocols` | Lista todos los protocolos metodológicos registrados |
| | `export_protocol_markdown`| Exporta protocolo en Markdown estructurado para PROSPERO/OSF |
| | `lookup_descriptors` | Busca descriptores controlados trilingües DeCS/MeSH |
| | `build_multilingual_search_query` | Construye ecuaciones de búsqueda booleanas multilingües estructuradas |
| **Cribado & PRISMA** | `screen_work` | Registra decisión de cribado con motivo y autoría (`human`/`ai`) |
| | `get_screening_status` | Resumen cuantitativo del cribado y motivos de exclusión |
| | `get_screening_concordance` | Calcula concordancia Kappa de Cohen y lista discrepancias |
| | `get_prisma_flow` | Métricas y datos estructurados de las 4 fases de PRISMA 2020 |
| | `get_ai_disclosure` | Genera declaración de transparencia de uso de IA (COPE/ICMJE/SciELO) |
| **Integridad** | `verify_references` | Valida listas de citas contra alucinaciones vía Crossref y OpenAlex |
| **Textos & Fichas** | `fetch_fulltext` | Resuelve y descarga PDF en acceso abierto vía Unpaywall, PMC o OpenAlex |
| | `get_fulltext_status` | Consulta el manifiesto y estado de descarga de textos completos |
| | `save_work_note` | Guarda ficha analítica con trazabilidad de validación humana |
| | `get_work_note` | Recupera ficha de lectura de un estudio específico |
| | `list_work_notes` | Lista todas las fichas analíticas registradas para una revisión |
| | `export_notes_markdown` | Exporta compilación de fichas en Markdown para Obsidian |
| **Metaanálisis & Sesgo**| `save_extraction_data` | Registra diseño, muestra, intervenciones, controles y desenlaces |
| | `get_extraction_table` | Obtiene tabla consolidada de extracción para metaanálisis |
| | `export_extraction_csv` | Exporta matriz de datos para R `metafor` (`yi`, `vi`) o RevMan 5 |
| | `save_risk_of_bias` | Registra evaluación Cochrane RoB 2, ROBINS-I o JBI con juicio global |
| | `get_risk_of_bias_summary` | Resumen de riesgo de sesgo y datos para gráfico de semáforo |
| **Bibliometría & Redes**| `export_network` | Extrae y exporta redes de coautoría, revistas y términos (VOSviewer / Gephi) |
| **Revisión Viva** | `compare_search_versions` | Compara dos versiones de búsqueda identificando registros nuevos y retenidos |
| | `update_search_differential` | Actualiza búsqueda en modo LSR generando informe metodológico diferencial |
| **Exportación & Paquete**| `export_list` | Exporta lista a RIS, CSV, JSON, DOIs, BibTeX, ABNT o URL de OpenAlex |
| | `export_reproducibility_package` | Construye paquete `.zip` con manifiesto criptográfico SHA-256 |
| **Prompts MCP** | `plan_search` | Orienta a la IA en la planificación rigurosa de la búsqueda sistemática |

---

## Interoperabilidad con Herramientas Externas

RSL.app se integra perfectamente con las principales herramientas de investigación:

| Herramienta | Formato Generado por RSL.app | Aplicación |
|---|---|---|
| **VOSviewer** | `.ris`, `.csv` (Scopus), `.map`, `.network`, `.dois.txt` | Mapas de coautoría, cocitación y acoplamiento bibliográfico |
| **Gephi** | `.gexf` (Graph Exchange XML Format) | Análisis avanzado de redes complejas y métricas de centralidad |
| **R (`metafor` / `meta`)** | `.csv` (con `yi`, `vi`, `ai, bi, ci, di, n1i, n2i`) | Metaanálisis de efectos fijos y aleatorios, metarregresión y forest plots |
| **RevMan 5 / Web** | `.csv` | Elaboración de revisiones y metaanálisis de la Colaboración Cochrane |
| **Zotero / Mendeley** | `.bib`, `.ris` | Gestión de referencias y citación en procesadores de texto |
| **Obsidian / Logseq** | `.md` (Markdown con frontmatter y notas) | Gestión del conocimiento académico personal y síntesis temática |
| **Zenodo / OSF** | `.zip` (con `checksums.sha256`) | Depósito de datos de investigación y asignación de DOI |

---

## Almacenamiento y Estructura de Directorios

Por defecto, todos los datos se almacenan localmente en `~/RSL.app` (en Windows: `C:\Users\<usuario>\RSL.app`, configurable vía `RSL_DATA_DIR`):

```
RSL.app/
├── log.md                     # Registro cronológico auditable de búsquedas y operaciones
├── lists/                     # Metadados JSON completos de cada lista generada
├── searches/                  # Ecuaciones y parámetros enviados a cada base
├── screening/                 # Decisiones de cribado, motivos y autoría (humano vs. IA)
├── notes/                     # Fichas de lectura crítica estructuradas
├── protocols/                 # Protocolos metodológicos previos a la búsqueda versionados
├── differential/              # Registros de comparaciones diferenciales en revisiones vivas
├── fulltext/                  # Textos completos (PDFs) en Acceso Abierto descargados
├── exports/                   # Archivos exportados (RIS, CSV, BibTeX, ABNT, VOSviewer, ZIP)
└── cache/                     # Caché local de respuestas de APIs (caducidad de 7 días)
```

---

## Configuración y Variables de Entorno

Puede configurarse desde la pantalla **Configuración** de la aplicación de escritorio o mediante variables de entorno:

| Variable | Descripción | Valor Predeterminado |
|---|---|---|
| `OPENALEX_API_KEY` | Clave API gratuita de OpenAlex (10.000 créditos/día) | Opcional (Recomendada) |
| `SEMANTIC_SCHOLAR_API_KEY` | Clave API gratuita de Semantic Scholar | Opcional |
| `NCBI_API_KEY` | Clave API de NCBI para PubMed (límites de petición más altos) | Opcional |
| `SCOPUS_API_KEY` | Clave API de Elsevier para Scopus | Opcional (Institucional) |
| `SCOPUS_INSTTOKEN` | Token institucional de Scopus para consultas fuera del campus | Opcional |
| `WOS_STARTER_API_KEY` | Clave API de Web of Science Starter (Clarivate) | Opcional |
| `RSL_CONTACT_EMAIL` | Correo de contacto cortés (enviado a Crossref, NCBI, Europe PMC) | Opcional |
| `RSL_DATA_DIR` | Directorio de almacenamiento de datos | `~/RSL.app` |
| `RSL_EXPORT_DIR` | Directorio de destino para archivos exportados | `<RSL_DATA_DIR>/exports` |
| `RSL_CACHE_DAYS` | Días de vigencia de la caché local de APIs | `7` |

---

## Modo Alojado Multiusuario Institucional

Una universidad, centro de investigación o laboratorio puede ejecutar RSL.app en un servidor institucional compartido mediante **Docker** con HTTPS automático vía **Caddy**:
- Acceso seguro mediante códigos individuales generados por el administrador (`rslapp token add`).
- Listas y registros aislados por investigador, con una caché de APIs compartida para optimizar cuotas.
- Conexión directa por enlace HTTPS (`https://rsl.su-universidad.edu/mcp`) para Claude y ChatGPT sin instalaciones locales.
- Guía detallada y directrices de protección de datos en [`docs/hospedagem.md`](docs/hospedagem.md).

---

## Privacidad, Ética y Gobernanza de Datos

- RSL.app almacena nombres públicos de autores, afiliaciones e identificadores ORCID proporcionados por las bases de datos bibliográficas exclusivamente para construir redes de coautoría y análisis bibliométrico.
- Todos los datos permanecen **estrictamente en su ordenador local**. RSL.app no incluye telemetría, no realiza seguimiento y no envía información de sus investigaciones a terceros ajenos a las propias APIs académicas consultadas.

---

## Para Desarrolladores

```bash
git clone https://github.com/Erick-wilding675/RSL-MCP-APP.git
cd RSL-MCP-APP
uv run --extra dev ruff check .
uv run --extra dev python -m pytest tests/
uv run --extra desktop-dev --extra desktop pytest tests_desktop/
```

- Documentación de arquitectura, contratos y decisiones: [`docs/`](docs/).
- Estado del proyecto y diario Blueprint: [`.blueprint/`](.blueprint/).
- Stack: Python 3.10+, SDK oficial `mcp>=2,<3`, NiceGUI 2.x, HTTPX asíncrono.

---

## Licencia

[MIT](LICENSE). Software libre y gratuito. Respete los términos de servicio y licencias específicas de cada base de datos consultada.
