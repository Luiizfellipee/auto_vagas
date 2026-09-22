from .filter_jobs import normalize_text

# Ordem de prioridade (menor número = mais destaque):
# 0. Vaga da fonte de carreira configurada (CAREER_URL)
# 1. Vaga presencial/híbrida no Espírito Santo
# 2. Vaga remota aberta para o Brasil
# 3. Demais vagas
ES_TERMS = ("espirito santo", "vitoria", "vila velha")
BR_REMOTE_TERMS = ("brasil", "brazil", "worldwide", "anywhere", "global", "latam", "america latina", "latin america")
EXTERNAL_API_PREFIXES = ("remotive-", "remoteok-")

PRIORITY_BADGES = {
    0: "🌟",
    1: "📍",
    2: "🇧🇷",
}

PRIORITY_LABELS = {
    0: "🌟 Vaga acompanhada — Prioridade 1",
    1: "📍 Espírito Santo — Prioridade 2",
    2: "🇧🇷 Remoto Brasil — Prioridade 3",
}


def job_priority(job: dict) -> int:
    job_id = str(job.get("job_id", ""))
    if not job_id.startswith(EXTERNAL_API_PREFIXES):
        return 0

    location = normalize_text(job.get("location", ""))
    if any(term in location for term in ES_TERMS):
        return 1

    workplace = (job.get("workplace_type") or "").casefold()
    if workplace in {"remote", "remoto"} and any(term in location for term in BR_REMOTE_TERMS):
        return 2

    return 3


def sort_by_priority(jobs: list[dict]) -> list[dict]:
    return sorted(jobs, key=job_priority)


def is_brazil_relevant(job: dict) -> bool:
    """Vagas da fonte de carreira configurada sempre valem; vagas vindas das
    APIs públicas só valem se forem no Brasil (ES incluso) ou abertas a
    qualquer lugar/mundo (o que também cobre o Brasil)."""
    job_id = str(job.get("job_id", ""))
    if not job_id.startswith(EXTERNAL_API_PREFIXES):
        return True

    location = normalize_text(job.get("location", ""))
    if not location:
        return True

    return any(term in location for term in BR_REMOTE_TERMS) or any(term in location for term in ES_TERMS)
