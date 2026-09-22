import re
import unicodedata
from collections.abc import Iterable

DEFAULT_TERMS = (
    "analista de dados", "cientista de dados", "engenheiro de dados",
    "engenharia de dados", "data analyst", "data scientist", "data engineer",
    "analytics", "business intelligence", "bi",
    "machine learning", "inteligencia artificial", "governanca de dados",
    "arquitetura de dados", "etl", "mlops", "data science",
)

GENERIC_TERMS = {"data", "dados"}
# Termos curtos/ambíguos demais para confiar em texto livre de descrições
# (aparecem em rodapés de SEO, listas de tags e textos de política de
# privacidade sem relação com a vaga em si); exigimos que apareçam no título.
TITLE_REQUIRED_TERMS = {
    "inteligencia artificial", "machine learning", "mlops",
    "data science", "analytics", "business intelligence", "bi", "etl",
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value).strip().casefold()


def matching_terms(job: dict, terms: Iterable[str] = DEFAULT_TERMS) -> list[str]:
    title_and_department = normalize_text(" ".join(str(job.get(k, "")) for k in ("title", "department", "departmentName")))
    haystack = normalize_text(" ".join(str(job.get(k, "")) for k in ("title", "description", "department", "departmentName")))
    matches = []
    for term in terms:
        normalized_term = normalize_text(term)
        if normalized_term in GENERIC_TERMS:
            continue
        if normalized_term in TITLE_REQUIRED_TERMS and not re.search(rf"(?<!\w){re.escape(normalized_term)}(?!\w)", title_and_department):
            continue
        if re.search(rf"(?<!\w){re.escape(normalized_term)}(?!\w)", haystack):
            matches.append(term)
    return matches


def filter_jobs(jobs: Iterable[dict], terms: Iterable[str] = DEFAULT_TERMS) -> list[dict]:
    result = []
    for job in jobs:
        matches = matching_terms(job, terms)
        if matches:
            copy = dict(job)
            copy["matched_terms"] = matches
            result.append(copy)
    return result
