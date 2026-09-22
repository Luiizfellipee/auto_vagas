import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # permite executar sem instalar dependências opcionais
    def load_dotenv(dotenv_path=".env", *args, **kwargs):
        path = Path(dotenv_path)
        if not path.exists():
            return False
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(name.strip(), value)
        return True

from src.collector import CollectionError, collect_jobs
from src.diff import compare
from src.filter_jobs import DEFAULT_TERMS, filter_jobs
from src.notifier import build_alert_embeds, build_existing_embeds, send_discord
from src.priority import is_brazil_relevant
from src.remoteok_collector import collect_remoteok_jobs
from src.remotive_collector import collect_remotive_jobs
from src.storage import append_history, load_snapshot, save_snapshot


ROOT = Path(__file__).parent


def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "sim"}


def collect_all_jobs() -> list:
    """Coleta vagas de todas as fontes habilitadas. A vaga de uma carreira própria
    (CAREER_URL) é opcional e fica fora do código público; as APIs gratuitas de
    vagas de dados (Remotive, RemoteOK) rodam por padrão."""
    jobs = []
    errors = []

    career_url = os.getenv("CAREER_URL")
    if career_url:
        location_prefixes = tuple(x.strip() for x in os.getenv("LOCATION_PREFIX_STRIP", "").split(",") if x.strip())
        try:
            jobs += collect_jobs(career_url, os.getenv("GUPY_API_URL") or None,
                                  os.getenv("GUPY_CAREER_PAGE_ID") or None, os.getenv("GUPY_API_TOKEN") or None,
                                  location_prefixes=location_prefixes)
        except CollectionError as exc:
            errors.append(str(exc))

    if _flag("ENABLE_REMOTIVE"):
        try:
            jobs += collect_remotive_jobs()
        except CollectionError as exc:
            errors.append(str(exc))

    if _flag("ENABLE_REMOTEOK"):
        try:
            jobs += collect_remoteok_jobs()
        except CollectionError as exc:
            errors.append(str(exc))

    if not jobs and errors:
        raise CollectionError("; ".join(errors))
    return jobs


def main() -> int:
    load_dotenv()
    data_dir = ROOT / os.getenv("DATA_DIR", "data")
    terms = [x.strip() for x in os.getenv("KEYWORDS", ",".join(DEFAULT_TERMS)).split(",") if x.strip()]
    try:
        raw_jobs = collect_all_jobs()
        normalized_jobs = [job.to_dict() for job in raw_jobs]
        current = filter_jobs(normalized_jobs, terms)
        current = [job for job in current if is_brazil_relevant(job)]
    except CollectionError as exc:
        print(f"Execução inconclusiva: {exc}", file=sys.stderr)
        return 2

    snapshot = data_dir / "vagas_snapshot.json"
    history = data_dir / "historico.jsonl"
    had_snapshot = snapshot.exists()
    previous = load_snapshot(snapshot)
    # Reaplica o filtro ao snapshot antigo para não tratar vagas que deixaram
    # de ser relevantes como se tivessem sido removidas da fonte.
    previous = filter_jobs(previous, terms)
    previous = [job for job in previous if is_brazil_relevant(job)]
    silent_bootstrap = _flag("BOOTSTRAP_SILENT")
    changes = compare(previous, current) if had_snapshot or not silent_bootstrap else compare(current, current)
    for job in changes.new:
        append_history(history, "NEW", job)
    for job in changes.missing:
        append_history(history, "MISSING", job)
    for job, fields in changes.changed:
        append_history(history, "CHANGED", job, fields)
    save_snapshot(snapshot, current)

    embeds = build_existing_embeds(current) if "--test-existing" in sys.argv else build_alert_embeds(changes)
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if embeds and webhook_url:
        send_discord(webhook_url, embeds)
    elif embeds:
        print(f"Discord não configurado; {len(embeds)} vaga(s) para avisar.")
    print(f"Coletadas {len(current)} vagas relevantes: {len(changes.new)} novas, {len(changes.changed)} alteradas, {len(changes.missing)} não encontradas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
