import json
from datetime import datetime, timezone
from pathlib import Path


def load_snapshot(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("jobs", data) if isinstance(data, (dict, list)) else []


def save_snapshot(path: Path, jobs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"collected_at": datetime.now(timezone.utc).isoformat(), "jobs": jobs}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_history(path: Path, event: str, job: dict, fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"event": event, "at": datetime.now(timezone.utc).isoformat(), "job": job}
    if fields:
        row["fields"] = fields
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
