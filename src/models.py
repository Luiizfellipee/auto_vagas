from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Job:
    job_id: str
    title: str
    company: str = "Não informado"
    location: str = "Não informado"
    url: str = ""
    status: str = "published"
    employment_type: str = ""
    workplace_type: str = ""
    published_at: str = ""
    description: str = ""
    matched_terms: list[str] = field(default_factory=list)
    description_hash: str = ""
    collected_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
