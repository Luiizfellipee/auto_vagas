from src.diff import compare


def job(job_id, title="Analista de Dados", description_hash="a"):
    return {"job_id": job_id, "title": title, "location": "Remoto", "status": "published", "description_hash": description_hash, "matched_terms": ["dados"]}


def test_new_missing_and_changed():
    result = compare([job("1"), job("2")], [job("1", description_hash="b"), job("3")])
    assert [x["job_id"] for x in result.new] == ["3"]
    assert [x["job_id"] for x in result.missing] == ["2"]
    assert result.changed[0][0]["job_id"] == "1"
    assert "description_hash" in result.changed[0][1]


def test_no_change():
    result = compare([job("1")], [job("1")])
    assert not result.new and not result.missing and not result.changed
