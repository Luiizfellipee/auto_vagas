import time
from datetime import datetime, timezone

import requests

from .priority import PRIORITY_LABELS, job_priority, sort_by_priority

COLOR_NEW = 0x2ECC71
COLOR_CHANGED = 0xF1C40F
COLOR_MISSING = 0xE74C3C
COLOR_DEFAULT = 0x5865F2

EMBEDS_PER_MESSAGE = 10
# Envios muito rápidos e seguidos para o mesmo webhook fazem o Discord
# derrubar a conexão em vez de responder 429; um pequeno intervalo evita isso.
DELAY_BETWEEN_MESSAGES = 1.0


def _mode(location: str) -> str:
    text = (location or "").casefold()
    if "remot" in text:
        return "Remoto"
    if "híbr" in text or "hibr" in text:
        return "Híbrido"
    if "presencial" in text:
        return "Presencial"
    return "Não informado"


def _display_mode(job: dict) -> str:
    value = (job.get("workplace_type") or "").casefold()
    if value in {"remote", "remoto"}:
        return "Remoto"
    if value in {"hybrid", "híbrido", "hibrido"}:
        return "Híbrido"
    if value in {"on-site", "onsite", "presencial"}:
        return "Presencial"
    return _mode(job.get("location", ""))


def _display_employment(job: dict) -> str:
    value = (job.get("employment_type") or "").casefold()
    labels = {
        "vacancy_type_effective": "Efetivo",
        "vacancy_type_internship": "Estágio",
        "vacancy_legal_entity": "Pessoa jurídica (PJ)",
        "vacancy_type_temporary": "Temporário",
        "vacancy_type_trainee": "Trainee",
    }
    if value in labels:
        return labels[value]
    if value:
        return job["employment_type"]
    return "Não informado"


def _published_info(value: str) -> str:
    if not value:
        return "Data não informada"
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        days = max(0, (datetime.now(timezone.utc) - date).days)
        age = "hoje" if days == 0 else "ontem" if days == 1 else f"há {days} dias"
        return f"{date.astimezone().strftime('%d/%m/%Y')} ({age})"
    except ValueError:
        return value


def _field(name: str, value: str, inline: bool = True) -> dict:
    return {"name": name, "value": value[:1024], "inline": inline}


def build_job_embed(job: dict, heading: str = "VAGA ABERTA", color: int = COLOR_DEFAULT) -> dict:
    fields = [_field("🏢 Empresa", job.get("company") or "Não informado")]
    employment = _display_employment(job)
    if employment != "Não informado":
        fields.append(_field("📄 Tipo", employment))
    mode = _display_mode(job)
    if mode != "Não informado":
        fields.append(_field("🗺️ Modalidade", mode))
    if job.get("location") and job.get("location") != "Não informado":
        fields.append(_field("📍 Localidade", job["location"]))
    if job.get("published_at"):
        fields.append(_field("🗓️ Publicada", _published_info(job["published_at"])))

    embed = {
        "title": (job.get("title") or "Sem título")[:256],
        "color": color,
        "fields": fields,
        "footer": {"text": heading},
    }
    label = PRIORITY_LABELS.get(job_priority(job))
    if label:
        embed["author"] = {"name": label}
    if job.get("url"):
        embed["url"] = job["url"]
    return embed


def build_existing_embeds(jobs: list[dict]) -> list[dict]:
    return [build_job_embed(job) for job in sort_by_priority(jobs)]


def build_alert_embeds(changes) -> list[dict]:
    embeds = [build_job_embed(job, "NOVA VAGA", COLOR_NEW) for job in sort_by_priority(changes.new)]
    for job, changed_fields in sorted(changes.changed, key=lambda item: job_priority(item[0])):
        embed = build_job_embed(job, "VAGA ALTERADA", COLOR_CHANGED)
        embed["fields"].append(_field("✏️ Campos alterados", ", ".join(changed_fields), inline=False))
        embeds.append(embed)
    for job in sort_by_priority(changes.missing):
        embed = {
            "title": (job.get("title") or "Sem título")[:256],
            "color": COLOR_MISSING,
            "fields": [
                _field("🗓️ Última vez vista", _published_info(job.get("published_at", ""))),
                _field("ℹ️ Observação", "A fonte não informou encerramento; a vaga não apareceu na consulta atual.", inline=False),
            ],
            "footer": {"text": "VAGA NÃO ENCONTRADA"},
        }
        label = PRIORITY_LABELS.get(job_priority(job))
        if label:
            embed["author"] = {"name": label}
        embeds.append(embed)
    return embeds


def send_discord(webhook_url: str, embeds: list[dict], session=None) -> None:
    if not embeds:
        return
    session = session or requests.Session()
    chunks = [embeds[i:i + EMBEDS_PER_MESSAGE] for i in range(0, len(embeds), EMBEDS_PER_MESSAGE)]
    for index, chunk in enumerate(chunks):
        if index > 0:
            time.sleep(DELAY_BETWEEN_MESSAGES)
        for attempt in range(3):
            response = session.post(webhook_url, json={"embeds": chunk}, timeout=30)
            if response.status_code == 429:
                time.sleep(float(response.json().get("retry_after", 1)) + 0.5)
                continue
            response.raise_for_status()
            break
