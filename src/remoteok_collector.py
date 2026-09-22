import re

import requests

from .collector import CollectionError
from .normalizer import normalize_job

REMOTEOK_API_URL = "https://remoteok.com/api"
REMOTEOK_BASE_URL = "https://remoteok.com/"


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", text).strip()


def collect_remoteok_jobs(tag: str = "data", session=None) -> list:
    """Coleta vagas da API pública gratuita da RemoteOK (sem necessidade de chave)."""
    session = session or requests.Session()
    try:
        response = session.get(
            REMOTEOK_API_URL,
            params={"tags": tag},
            timeout=30,
            # a RemoteOK bloqueia requisições sem um User-Agent de navegador
            headers={"User-Agent": "Mozilla/5.0 (compatible; auto-vagas-monitor/1.0)"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CollectionError(f"falha ao consultar RemoteOK: {exc}") from exc

    jobs = []
    for raw in payload:
        if not isinstance(raw, dict) or "id" not in raw:
            continue  # o primeiro item da resposta é um aviso legal, não uma vaga
        # As tags da RemoteOK não são confiáveis para filtragem (a própria API
        # já retorna vagas fora do tema mesmo com ?tags=data), então usamos
        # apenas o texto real da descrição, sem misturar as tags nele.
        jobs.append(normalize_job({
            "id": f"remoteok-{raw.get('id')}",
            "title": raw.get("position", ""),
            "company": raw.get("company", ""),
            "url": raw.get("url", ""),
            "location": raw.get("location", ""),
            "workplaceType": "remote",
            "type": "",
            "publishedAt": raw.get("date", ""),
            "description": _strip_html(raw.get("description", "")),
        }, REMOTEOK_BASE_URL))
    return jobs
