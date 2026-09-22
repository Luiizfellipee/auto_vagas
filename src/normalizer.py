import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from .models import Job


def _text(value) -> str:
    if isinstance(value, list):
        return ", ".join(_text(x) for x in value)
    if isinstance(value, dict):
        return ", ".join(_text(x) for x in value.values())
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_job(raw: dict, base_url: str = "") -> Job:
    job_id = raw.get("job_id", raw.get("id", raw.get("code", "")))
    title = raw.get("title", raw.get("name", ""))
    url = raw.get("url", raw.get("jobUrl", ""))
    if url and not url.startswith("http"):
        url = urljoin(base_url, url)
    if not url and job_id:
        url = urljoin(base_url, f"jobs/{job_id}")
    description = _text(raw.get("description", raw.get("details", "")))
    location = _text(raw.get("location", ""))
    if not location:
        city = _text(raw.get("addressCity", raw.get("city", "")))
        state = _text(raw.get("addressStateShortName", raw.get("addressState", "")))
        location = " - ".join(x for x in (city, state) if x)
    if not location:
        location = _text(raw.get("address", "Não informado"))
    workplace_type = _text(raw.get("workplaceType", ""))
    if not workplace_type and raw.get("remoteWorking") is True:
        workplace_type = "remote"
    company_default = urlparse(base_url).netloc or "Não informado"
    return Job(
        job_id=str(job_id).strip(), title=_text(title), company=_text(raw.get("company", company_default)),
        location=location or "Não informado", url=url, status=_text(raw.get("status", "published")) or "published",
        employment_type=_text(raw.get("employment_type", raw.get("type", ""))), workplace_type=workplace_type,
        published_at=_text(raw.get("published_at", raw.get("publishedAt", raw.get("createdAt", "")))),
        description=description, matched_terms=list(raw.get("matched_terms", [])),
        description_hash=hashlib.sha256(description.encode("utf-8")).hexdigest(),
        collected_at=raw.get("collected_at") or datetime.now(timezone.utc).isoformat(),
    )
