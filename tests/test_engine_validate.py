from engine.engine import REQUIRED_FIELDS, validate


def test_validate_all_missing():
    assert set(validate({})) == set(REQUIRED_FIELDS)


def test_validate_none_missing():
    complete = {
        "job_title": "Systemingenieur",
        "location": "München",
        "start_date": "sofort",
        "tasks": ["Aufgabe 1"],
        "profile": ["Profil 1"],
    }
    assert validate(complete) == []


def test_validate_one_missing():
    fields = {
        "job_title": "Systemingenieur",
        "location": "München",
        "start_date": None,
        "tasks": ["Aufgabe 1"],
        "profile": ["Profil 1"],
    }
    assert validate(fields) == ["start_date"]
