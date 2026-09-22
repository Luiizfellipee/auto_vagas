import json
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin
from html import unescape

import requests

from .normalizer import normalize_job


class CollectionError(RuntimeError):
    pass


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: set[str] = set()
        self.current = ""
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.current = attrs["href"]
            self.text = []

    def handle_data(self, data):
        if self.current:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            if re.search(r"/jobs?/|jobId", self.current, re.I):
                self.links.add(self.current)
            self.current = ""


def _request(session, url: str, **kwargs) -> str:
    try:
        response = session.get(url, timeout=kwargs.pop("timeout", 30), **kwargs)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise CollectionError(f"falha ao consultar {url}: {exc}") from exc


def _api_jobs(session, api_url: str, career_page_id: str | None, token: str | None) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    jobs = []
    page = 1
    while True:
        params = {"status": "published", "perPage": 100, "page": page, "fields": "all"}
        if career_page_id:
            params["careerPageId"] = career_page_id
        response = session.get(api_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        items = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not items:
            break
        jobs.extend(items)
        if len(items) < 100:
            break
        page += 1
    return jobs


def collect_jobs(career_url: str, api_url: str | None = None, career_page_id: str | None = None,
                 token: str | None = None, session=None, location_prefixes: tuple[str, ...] = ()) -> list:
    session = session or requests.Session()
    if api_url:
        try:
            raw = _api_jobs(session, api_url, career_page_id, token)
            normalized = [normalize_job(job, career_url) for job in raw]
            if normalized:
                return normalized
        except (requests.RequestException, ValueError):
            pass  # fallback público abaixo

    html = _request(session, career_url, headers={"User-Agent": "auto-vagas-monitor/1.0"})
    parser = _LinkParser()
    parser.feed(html)
    urls = {urljoin(career_url, link.split("?")[0]) for link in parser.links}
    if not urls:
        raise CollectionError("nenhuma vaga foi encontrada na página pública")
    jobs = []
    for url in sorted(urls):
        page = _request(session, url, headers={"User-Agent": "auto-vagas-monitor/1.0"})
        match = re.search(r"/jobs?/(\d+)", url)
        job_id = match.group(1) if match else re.search(r'jobId["=:]+(\d+)', page, re.I)
        job_id = job_id.group(1) if hasattr(job_id, "group") else None
        title = ""
        site_name = ""
        for pattern in (r'<h1[^>]*>\s*(.*?)\s*</h1>', r'<title[^>]*>\s*(.*?)\s*</title>'):
            found = re.search(pattern, page, re.I | re.S)
            if found:
                raw_title = unescape(re.sub(r"<[^>]+>", "", found.group(1)).strip())
                # a tag <title> costuma vir como "Cargo | Nome da empresa"; a <h1>
                # normalmente não tem esse sufixo de marca do site.
                if "|" in raw_title:
                    title, _, site_name = raw_title.partition("|")
                    title, site_name = title.strip(), site_name.strip()
                else:
                    title = raw_title
                break
        description = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.I | re.S)
        description = re.sub(r"<[^>]+>", " ", description)
        metadata = {}
        for block in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.I | re.S):
            try:
                candidate = json.loads(block.strip())
                if isinstance(candidate, dict) and (candidate.get("@type") == "JobPosting" or "jobLocation" in candidate):
                    metadata = candidate
                    break
            except json.JSONDecodeError:
                continue
        listing_text = _listing_text(html, url)
        listing_location, listing_mode, listing_type = _listing_fields(listing_text, location_prefixes)
        address = metadata.get("jobLocation", {}).get("address", {}) if isinstance(metadata.get("jobLocation"), dict) else {}
        location = ", ".join(str(address.get(key, "")).strip() for key in ("addressLocality", "addressRegion") if address.get(key))
        if metadata.get("jobLocationType") == "TELECOMMUTE":
            location = "Trabalho remoto"
        location = location or listing_location
        employment = metadata.get("employmentType", "")
        if employment:
            description += f" Tipo de contratação: {employment}."
        hiring_org = metadata.get("hiringOrganization")
        company = (hiring_org.get("name", "") if isinstance(hiring_org, dict) else "") or site_name
        raw_job = {"id": job_id or url, "title": metadata.get("title", title), "url": url,
                   "location": location, "workplaceType": metadata.get("workplaceType", metadata.get("jobLocationType", "")) or listing_mode,
                   "type": metadata.get("employmentType", "") or listing_type,
                   "publishedAt": metadata.get("datePosted", metadata.get("publishedAt", "")),
                   "description": metadata.get("description", description)}
        if company:
            raw_job["company"] = company
        jobs.append(normalize_job(raw_job, career_url))
    return jobs


def _listing_text(html: str, url: str) -> str:
    job_id = re.search(r"/jobs?/(\d+)", url)
    if not job_id:
        return ""
    pattern = rf".{{0,900}}{re.escape(job_id.group(1))}.{{0,900}}"
    found = re.search(pattern, html, re.I | re.S)
    if not found:
        return ""
    text = unescape(re.sub(r"<[^>]+>", " ", found.group(0)))
    return re.sub(r"\s+", " ", text).strip()


def _listing_fields(text: str, location_prefixes: tuple[str, ...] = ()) -> tuple[str, str, str]:
    if not text:
        return "", "", ""
    mode = ""
    if re.search(r"trabalho\s+remoto", text, re.I):
        return "Trabalho Remoto", "remote", _listing_type(text)
    if re.search(r"\b(híbrido|hibrido)\b", text, re.I):
        mode = "hybrid"
    elif re.search(r"\bpresencial\b", text, re.I):
        mode = "on-site"
    location_match = re.search(r"([A-ZÀ-Ý][\wÀ-ÿ .'-]{1,50}\s+-\s+[A-Z]{2})\s*(?:e\s*(?:híbrido|hibrido|presencial))?", text)
    location = location_match.group(1).strip() if location_match else ""
    if location_prefixes:
        prefix_pattern = "|".join(re.escape(prefix) for prefix in location_prefixes)
        location = re.sub(rf"^(?:{prefix_pattern})\s+", "", location, flags=re.I)
    return (location, mode, _listing_type(text))


def _listing_type(text: str) -> str:
    match = re.search(r"\b(Efetivo|Estágio|Temporário|Trainee|Freelancer|Autônomo)\b", text, re.I)
    return match.group(1) if match else ""
