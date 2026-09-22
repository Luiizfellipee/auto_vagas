from src.remotive_collector import collect_remotive_jobs


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, payload):
        self._payload = payload

    def get(self, *args, **kwargs):
        return _FakeResponse(self._payload)


def test_normalizes_remotive_jobs():
    payload = {
        "jobs": [{
            "id": 123,
            "title": "Data Engineer",
            "company_name": "Acme",
            "url": "https://remotive.com/remote-jobs/data/123",
            "candidate_required_location": "Brazil",
            "job_type": "full_time",
            "publication_date": "2026-01-01T00:00:00",
            "description": "<p>Build pipelines</p>",
        }]
    }
    jobs = [job.to_dict() for job in collect_remotive_jobs(session=_FakeSession(payload))]
    assert jobs[0]["job_id"] == "remotive-123"
    assert jobs[0]["title"] == "Data Engineer"
    assert jobs[0]["company"] == "Acme"
    assert jobs[0]["workplace_type"] == "remote"
    assert "Build pipelines" in jobs[0]["description"]
