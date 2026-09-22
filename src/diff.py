from dataclasses import dataclass

FIELDS = ("title", "location", "status", "description_hash", "matched_terms")


@dataclass
class Changes:
    new: list[dict]
    missing: list[dict]
    changed: list[tuple[dict, list[str]]]


def compare(previous: list[dict], current: list[dict]) -> Changes:
    old = {str(j["job_id"]): j for j in previous}
    new = {str(j["job_id"]): j for j in current}
    added = [new[key] for key in sorted(new.keys() - old.keys())]
    missing = [old[key] for key in sorted(old.keys() - new.keys())]
    changed = []
    for key in sorted(old.keys() & new.keys()):
        fields = [field for field in FIELDS if old[key].get(field) != new[key].get(field)]
        if fields:
            changed.append((new[key], fields))
    return Changes(added, missing, changed)
