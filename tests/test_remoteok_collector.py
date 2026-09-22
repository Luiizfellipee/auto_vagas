from src.remoteok_collector import collect_remoteok_jobs


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


def test_ignores_legal_notice_and_normalizes_jobs():
    payload = [
        {"legal": "https://remoteok.com/terms"},
        {
            "id": "456",
            "position": "Data Analyst",
            "company": "Acme",
            "url": "https://remoteok.com/remote-jobs/456",
            "location": "Worldwide",
            "date": "2026-01-01T00:00:00",
            "description": "<p>Analyze data</p>",
            "tags": ["data", "sql"],
        },
    ]
    jobs = [job.to_dict() for job in collect_remoteok_jobs(session=_FakeSession(payload))]
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "remoteok-456"
    assert jobs[0]["title"] == "Data Analyst"
    assert jobs[0]["workplace_type"] == "remote"
    assert jobs[0]["description"] == "Analyze data"
