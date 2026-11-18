"""Módulo de Descritores em Ciências da Saúde (DeCS/MeSH) Trilíngues (FR-33, D-044)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _normalize_text(text: str) -> str:
    """Normaliza texto para busca fonética e sem acentuação."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w\s]", " ", no_accents.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


# FR-33, D-044: Catálogo curado representativo do vocabulário controlado DeCS/MeSH
# Cobrindo conceitos centrais de saúde coletiva, computação biomédica, clínica e metodologia
DECS_CATALOG: list[dict[str, Any]] = [
    {
        "id": "D001185",
        "category": "L01.224.050",
        "terms": {
            "pt": "Inteligência Artificial",
            "en": "Artificial Intelligence",
            "es": "Inteligencia Artificial",
        },
        "synonyms": {
            "pt": ["IA", "Sistemas Inteligentes", "Inteligência de Máquina", "Raciocínio Computacional"],
            "en": ["AI", "Computational Intelligence", "Machine Intelligence", "Intelligent Systems"],
            "es": ["IA", "Inteligencia Computacional", "Sistemas Inteligentes"],
        },
    },
    {
        "id": "D000069550",
        "category": "L01.224.050.500",
        "terms": {
            "pt": "Aprendizado de Máquina",
            "en": "Machine Learning",
            "es": "Aprendizaje Automático",
        },
        "synonyms": {
            "pt": ["Aprendizagem Automática", "Machine Learning", "Aprendizado Estatístico", "Aprendizagem de Máquina"],
            "en": ["Pattern Recognition, Automated", "Statistical Learning", "Algorithmic Learning"],
            "es": ["Aprendizaje de Máquinas", "Aprendizaje Estadístico", "Reconocimiento de Patrones Automatizado"],
        },
    },
    {
        "id": "D000076242",
        "category": "L01.224.050.500.250",
        "terms": {
            "pt": "Aprendizado Profundo",
            "en": "Deep Learning",
            "es": "Aprendizaje Profundo",
        },
        "synonyms": {
            "pt": ["Aprendizagem Profunda", "Deep Learning", "Redes Neurais Profundas"],
            "en": ["Hierarchical Learning", "Deep Neural Networks"],
            "es": ["Redes Neuronales Profundas"],
        },
    },
    {
        "id": "D016428",
        "category": "V02.700.500",
        "terms": {
            "pt": "Revisão Sistemática",
            "en": "Systematic Review",
            "es": "Revisión Sistemática",
        },
        "synonyms": {
            "pt": ["Revisão Sistemática da Literatura", "Revisão de Escopo", "Síntese de Evidências"],
            "en": ["Systematic Literature Review", "Scoping Review", "Evidence Synthesis"],
            "es": ["Revisión Sistemática de la Literatura", "Síntesis de Evidencia"],
        },
    },
    {
        "id": "D015201",
        "category": "E05.318.740.500",
        "terms": {
            "pt": "Metanálise",
            "en": "Meta-Analysis",
            "es": "Metaanálisis",
        },
        "synonyms": {
            "pt": ["Meta-Análise", "Síntese Quantitativa", "Análise Combinada de Dados"],
            "en": ["Meta Analysis", "Quantitative Synthesis", "Data Pooling"],
            "es": ["Meta-Análisis", "Síntesis Cuantitativa"],
        },
    },
    {
        "id": "D019317",
        "category": "E05.318.308",
        "terms": {
            "pt": "Medicina Baseada em Evidências",
            "en": "Evidence-Based Medicine",
            "es": "Medicina Basada en la Evidencia",
        },
        "synonyms": {
            "pt": ["Prática Baseada em Evidências", "Cuidados de Saúde Baseados em Evidências"],
            "en": ["Evidence-Based Practice", "Evidence-Based Healthcare"],
            "es": ["Práctica Basada en Evidencias", "Atención Médica Basada en Evidencias"],
        },
    },
    {
        "id": "D011320",
        "category": "N02.421.726",
        "terms": {
            "pt": "Atenção Primária à Saúde",
            "en": "Primary Health Care",
            "es": "Atención Primaria de Salud",
        },
        "synonyms": {
            "pt": ["Atenção Básica à Saúde", "Cuidados Primários de Saúde", "Saúde da Família"],
            "en": ["Primary Care", "Primary Healthcare", "Family Health"],
            "es": ["Atención Primaria", "Cuidados Primarios de Salud", "Salud Familiar"],
        },
    },
    {
        "id": "D011634",
        "category": "N06.850.780",
        "terms": {
            "pt": "Saúde Pública",
            "en": "Public Health",
            "es": "Salud Pública",
        },
        "synonyms": {
            "pt": ["Saúde Coletiva", "Higiene Pública", "Saúde Comunitária"],
            "en": ["Community Health", "Collective Health"],
            "es": ["Salud Colectiva", "Salud Comunitaria"],
        },
    },
    {
        "id": "D004812",
        "category": "H02.403.429.515",
        "terms": {
            "pt": "Epidemiologia",
            "en": "Epidemiology",
            "es": "Epidemiología",
        },
        "synonyms": {
            "pt": ["Vigilância Epidemiológica", "Métodos Epidemiológicos"],
            "en": ["Epidemiologic Methods", "Epidemiological Studies"],
            "es": ["Métodos Epidemiológicos", "Estudios Epidemiológicos"],
        },
    },
    {
        "id": "D017216",
        "category": "L01.224.050.375",
        "terms": {
            "pt": "Telemedicina",
            "en": "Telemedicine",
            "es": "Telemedicina",
        },
        "synonyms": {
            "pt": ["Telessaúde", "Teleassistência Médica", "Teleconsulta", "Saúde Digital"],
            "en": ["Telehealth", "eHealth", "Digital Health", "Remote Consultation"],
            "es": ["Telesalud", "eSalud", "Salud Digital", "Teleconsulta"],
        },
    },
    {
        "id": "D003863",
        "category": "F03.600.300",
        "terms": {
            "pt": "Depressão",
            "en": "Depression",
            "es": "Depresión",
        },
        "synonyms": {
            "pt": ["Transtorno Depressivo", "Sintomas Depressivos", "Depressão Maior"],
            "en": ["Depressive Symptoms", "Depressive Disorder", "Major Depression"],
            "es": ["Trastorno Depresivo", "Síntomas Depresivos", "Depresión Mayor"],
        },
    },
    {
        "id": "D001007",
        "category": "F01.145.126.100",
        "terms": {
            "pt": "Ansiedade",
            "en": "Anxiety",
            "es": "Ansiedad",
        },
        "synonyms": {
            "pt": ["Transtornos de Ansiedade", "Angústia", "Estado Ansioso"],
            "en": ["Anxiety Disorders", "Nervousness", "Hypervigilance"],
            "es": ["Trastornos de Ansiedad", "Angustia", "Estado Ansioso"],
        },
    },
    {
        "id": "D003920",
        "category": "C19.246.300",
        "terms": {
            "pt": "Diabetes Mellitus",
            "en": "Diabetes Mellitus",
            "es": "Diabetes Mellitus",
        },
        "synonyms": {
            "pt": ["Diabetes", "Glicemia Elevada", "Hiperglicemia Crônica"],
            "en": ["Diabetes", "Hyperglycemia", "Diabetic Condition"],
            "es": ["Diabetes", "Hiperglucemia Crónica"],
        },
    },
    {
        "id": "D006973",
        "category": "C14.907.489",
        "terms": {
            "pt": "Hipertensão",
            "en": "Hypertension",
            "es": "Hipertensión",
        },
        "synonyms": {
            "pt": ["Pressão Alta", "Hipertensão Arterial", "Pressão Arterial Elevada"],
            "en": ["High Blood Pressure", "Arterial Hypertension"],
            "es": ["Presión Alta", "Hipertensión Arterial"],
        },
    },
    {
        "id": "D009765",
        "category": "C18.654.726.500",
        "terms": {
            "pt": "Obesidade",
            "en": "Obesity",
            "es": "Obesidad",
        },
        "synonyms": {
            "pt": ["Excesso de Peso", "Adiposidade", "Índice de Massa Corporal Elevado"],
            "en": ["Overweight", "Adiposity", "Body Mass Index"],
            "es": ["Sobrepeso", "Adiposidad"],
        },
    },
    {
        "id": "D000086382",
        "category": "C01.748.210",
        "terms": {
            "pt": "COVID-19",
            "en": "COVID-19",
            "es": "COVID-19",
        },
        "synonyms": {
            "pt": ["Infecções por Coronavírus", "SARS-CoV-2", "Doença por Coronavírus 2019"],
            "en": ["Coronavirus Disease 2019", "SARS-CoV-2 Infection", "2019-nCoV"],
            "es": ["Infección por SARS-CoV-2", "Enfermedad por Coronavirus 2019"],
        },
    },
    {
        "id": "D014611",
        "category": "D20.215.894",
        "terms": {
            "pt": "Vacinas",
            "en": "Vaccines",
            "es": "Vacunas",
        },
        "synonyms": {
            "pt": ["Imunização", "Vacinação", "Imunobiológicos"],
            "en": ["Vaccination", "Immunization", "Immunizing Agents"],
            "es": ["Inmunización", "Vacunación"],
        },
    },
    {
        "id": "D009732",
        "category": "H02.478",
        "terms": {
            "pt": "Cuidados de Enfermagem",
            "en": "Nursing Care",
            "es": "Atención de Enfermería",
        },
        "synonyms": {
            "pt": ["Assistência de Enfermagem", "Prática de Enfermagem", "Processo de Enfermagem"],
            "en": ["Nursing Services", "Nursing Practice", "Patient Care"],
            "es": ["Asistencia de Enfermería", "Cuidado del Paciente"],
        },
    },
    {
        "id": "D001675",
        "category": "K01.316.142",
        "terms": {
            "pt": "Bioética",
            "en": "Bioethics",
            "es": "Bioética",
        },
        "synonyms": {
            "pt": ["Ética Médica", "Ética em Pesquisa", "Deontologia Biomédica"],
            "en": ["Medical Ethics", "Ethics, Research", "Biomedical Ethics"],
            "es": ["Ética Médica", "Ética de la Investigación"],
        },
    },
    {
        "id": "D036301",
        "category": "E05.318.740.600",
        "terms": {
            "pt": "Pesquisa Qualitativa",
            "en": "Qualitative Research",
            "es": "Investigación Cualitativa",
        },
        "synonyms": {
            "pt": ["Estudo Qualitativo", "Análise de Conteúdo", "Pesquisa Fenomenológica"],
            "en": ["Qualitative Studies", "Content Analysis", "Ethnography"],
            "es": ["Estudios Cualitativos", "Análisis de Contenido"],
        },
    },
]


# FR-33, D-044: Consulta descritores com pontuação por exatidão, prefixo ou correspondência de sinônimos
def lookup_descriptors(
    query: str,
    lang: str = "pt",
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Busca descritores controlados DeCS/MeSH no catálogo local por aproximação fonética e sinônimos."""
    if not query or not query.strip():
        return []

    norm_query = _normalize_text(query)
    clean_lang = lang.lower().strip() if lang else "pt"
    if clean_lang not in ("pt", "en", "es"):
        clean_lang = "pt"

    scored_results: list[tuple[int, dict[str, Any]]] = []

    for entry in DECS_CATALOG:
        score = 0
        term_target = _normalize_text(entry["terms"].get(clean_lang, ""))
        syns_target = [_normalize_text(s) for s in entry["synonyms"].get(clean_lang, [])]

        # Verifica correspondência exata ou de prefixo no termo principal do idioma alvo
        if norm_query == term_target:
            score = 100
        elif term_target.startswith(norm_query) or norm_query.startswith(term_target):
            score = 80
        elif norm_query in term_target or term_target in norm_query:
            score = 60
        else:
            # Verifica sinônimos no idioma alvo
            for syn in syns_target:
                if norm_query == syn:
                    score = max(score, 90)
                elif syn.startswith(norm_query):
                    score = max(score, 70)
                elif norm_query in syn:
                    score = max(score, 50)

        # Se não casou no idioma alvo, testa correspondência em outros idiomas
        if score == 0:
            for other_lang in ("pt", "en", "es"):
                if other_lang == clean_lang:
                    continue
                o_term = _normalize_text(entry["terms"].get(other_lang, ""))
                if norm_query == o_term:
                    score = max(score, 75)
                elif norm_query in o_term:
                    score = max(score, 45)
                for o_syn in [_normalize_text(s) for s in entry["synonyms"].get(other_lang, [])]:
                    if norm_query == o_syn:
                        score = max(score, 65)
                    elif norm_query in o_syn:
                        score = max(score, 40)

        if score > 0:
            scored_results.append((score, entry))

    # Ordena por pontuação decrescente
    scored_results.sort(key=lambda x: x[0], reverse=True)
    limit = max(1, min(max_results, 50))
    return [item[1] for item in scored_results[:limit]]


# FR-33, D-044: Gera blocos booleanos multilíngues formatados para bases de pesquisa
def build_multilingual_query(
    descriptors: list[str | dict[str, Any]],
    operator: str = "OR",
) -> dict[str, str]:
    """Gera expressões booleanas de busca em Português, Inglês e Espanhol combinando termos e sinônimos."""
    op = " OR " if operator.upper() == "OR" else " AND "

    pt_terms: list[str] = []
    en_terms: list[str] = []
    es_terms: list[str] = []

    for item in descriptors:
        matched: dict[str, Any] | None = None
        if isinstance(item, dict) and "terms" in item:
            matched = item
        elif isinstance(item, str):
            clean_str = item.strip()
            # Tenta encontrar por ID primeiro
            for entry in DECS_CATALOG:
                if entry["id"].lower() == clean_str.lower():
                    matched = entry
                    break
            # Depois por correspondência de texto
            if not matched:
                results = lookup_descriptors(clean_str, max_results=1)
                if results:
                    matched = results[0]

        if matched:
            # Termo principal + sinônimos em PT
            main_pt = matched["terms"].get("pt")
            if main_pt and f'"{main_pt}"' not in pt_terms:
                pt_terms.append(f'"{main_pt}"')
            for s in matched["synonyms"].get("pt", []):
                quote_s = f'"{s}"'
                if quote_s not in pt_terms:
                    pt_terms.append(quote_s)

            # Termo principal + sinônimos em EN
            main_en = matched["terms"].get("en")
            if main_en and f'"{main_en}"' not in en_terms:
                en_terms.append(f'"{main_en}"')
            for s in matched["synonyms"].get("en", []):
                quote_s = f'"{s}"'
                if quote_s not in en_terms:
                    en_terms.append(quote_s)

            # Termo principal + sinônimos em ES
            main_es = matched["terms"].get("es")
            if main_es and f'"{main_es}"' not in es_terms:
                es_terms.append(f'"{main_es}"')
            for s in matched["synonyms"].get("es", []):
                quote_s = f'"{s}"'
                if quote_s not in es_terms:
                    es_terms.append(quote_s)
        elif isinstance(item, str) and item.strip():
            # Termo livre de fallback
            quoted = f'"{item.strip()}"'
            pt_terms.append(quoted)
            en_terms.append(quoted)
            es_terms.append(quoted)

    query_pt = f"({op.join(pt_terms)})" if pt_terms else ""
    query_en = f"({op.join(en_terms)})" if en_terms else ""
    query_es = f"({op.join(es_terms)})" if es_terms else ""

    combined_blocks = [q for q in (query_en, query_pt) if q]
    query_combined = f"({' OR '.join(combined_blocks)})" if combined_blocks else ""

    return {
        "pt": query_pt,
        "en": query_en,
        "es": query_es,
        "combined": query_combined,
    }
