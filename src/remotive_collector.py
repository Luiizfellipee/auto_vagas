import re

import requests

from .collector import CollectionError
from .normalizer import normalize_job

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
REMOTIVE_BASE_URL = "https://remotive.com/"


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", text).strip()


def collect_remotive_jobs(category: str = "data", session=None) -> list:
    """Coleta vagas da API pública gratuita da Remotive (sem necessidade de chave)."""
    session = session or requests.Session()
    try:
        response = session.get(
            REMOTIVE_API_URL,
            params={"category": category},
            timeout=30,
            headers={"User-Agent": "auto-vagas-monitor/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CollectionError(f"falha ao consultar Remotive: {exc}") from exc

    jobs = []
    for raw in payload.get("jobs", []):
        jobs.append(normalize_job({
            "id": f"remotive-{raw.get('id')}",
            "title": raw.get("title", ""),
            "company": raw.get("company_name", ""),
            "url": raw.get("url", ""),
            "location": raw.get("candidate_required_location", ""),
            "workplaceType": "remote",
            "type": raw.get("job_type", ""),
            "publishedAt": raw.get("publication_date", ""),
            "description": _strip_html(raw.get("description", "")),
        }, REMOTIVE_BASE_URL))
    return jobs
