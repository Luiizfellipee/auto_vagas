from src.filter_jobs import filter_jobs, normalize_text


def test_normalizes_accents_and_case():
    assert normalize_text("Inteligência Artificial") == "inteligencia artificial"


def test_matches_description_not_only_title():
    jobs = filter_jobs([{"job_id": "1", "title": "Especialista", "description": "Atuará com governança de dados"}])
    assert jobs[0]["matched_terms"] == ["governanca de dados"]


def test_same_title_different_ids_are_kept():
    jobs = filter_jobs([{"job_id": "1", "title": "Analista de Dados"}, {"job_id": "2", "title": "Analista de Dados"}])
    assert [job["job_id"] for job in jobs] == ["1", "2"]


def test_generic_data_word_does_not_match_unrelated_job():
    jobs = filter_jobs([{"job_id": "1", "title": "Analista de Sistemas", "description": "Cadastro de dados e sistemas internos"}])
    assert jobs == []
