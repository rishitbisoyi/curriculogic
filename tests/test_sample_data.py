import pytest
import os
import json
import tempfile
try:
    import sample_data
    from sample_data import load_sample_courses, save_courses, SAMPLE_COURSES
except ModuleNotFoundError:
    import curriculogic.sample_data as sample_data
    from curriculogic.sample_data import load_sample_courses, save_courses, SAMPLE_COURSES


def test_sample_courses_structure():
    assert len(SAMPLE_COURSES) >= 10
    for c in SAMPLE_COURSES:
        assert "code" in c
        assert "name" in c
        assert "credits" in c
        assert "prereqs" in c
        assert isinstance(c["credits"], int)
        assert isinstance(c["prereqs"], list)


def test_save_and_load_courses(tmp_path, monkeypatch):
    test_file = str(tmp_path / "courses_test.json")
    monkeypatch.setattr(sample_data, "DATA_FILE", test_file)

    test_data = [
        {"code": "TEST1", "name": "Test Course 1", "credits": 3, "prereqs": []},
        {"code": "TEST2", "name": "Test Course 2", "credits": 4, "prereqs": ["TEST1"]},
    ]

    save_courses(test_data)
    assert os.path.exists(test_file)

    loaded = load_sample_courses()
    assert loaded == test_data


def test_load_fallback_on_corrupt_file(tmp_path, monkeypatch):
    test_file = str(tmp_path / "corrupt.json")
    with open(test_file, "w") as f:
        f.write("{invalid json content")

    monkeypatch.setattr(sample_data, "DATA_FILE", test_file)

    loaded = load_sample_courses()
    assert loaded == SAMPLE_COURSES
