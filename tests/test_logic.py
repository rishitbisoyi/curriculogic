import pytest
try:
    from logic import get_metrics, truth_table
except ModuleNotFoundError:
    from curriculogic.logic import get_metrics, truth_table


@pytest.fixture
def sample_courses():
    return [
        {"code": "A", "name": "Course A", "credits": 3, "prereqs": []},
        {"code": "B", "name": "Course B", "credits": 4, "prereqs": ["A"]},
        {"code": "C", "name": "Course C", "credits": 2, "prereqs": []},
    ]


def test_metrics_all(sample_courses):
    completed = set(["A"])
    total, completed_cnt, eligible_cnt, remaining = get_metrics(sample_courses, completed)
    assert total == 3
    assert completed_cnt == 1
    # B is eligible (prereq A completed), C is also eligible (no prereqs)
    assert eligible_cnt == 2
    assert remaining == 4 + 2  # B + C credits


def test_metrics_empty_completed(sample_courses):
    total, completed_cnt, eligible_cnt, remaining = get_metrics(sample_courses, set())
    assert total == 3
    assert completed_cnt == 0
    # Courses A and C have no prereqs, so both are eligible
    assert eligible_cnt == 2
    assert remaining == 9


def test_metrics_all_completed(sample_courses):
    completed = {"A", "B", "C"}
    total, completed_cnt, eligible_cnt, remaining = get_metrics(sample_courses, completed)
    assert total == 3
    assert completed_cnt == 3
    assert eligible_cnt == 0
    assert remaining == 0


def test_truth_table_vacuous():
    tt = truth_table([])
    assert len(tt) == 1
    assert tt[0]["Eligible"] == 1


def test_truth_table_single_var():
    tt = truth_table(["PRG"])
    assert len(tt) == 2
    assert tt[0] == {"PRG": 0, "Eligible": 0}
    assert tt[1] == {"PRG": 1, "Eligible": 1}


def test_truth_table_multiple_vars():
    tt = truth_table(["A", "B"])
    assert len(tt) == 4
    # Only last row where all are 1 is eligible
    assert tt[-1] == {"A": 1, "B": 1, "Eligible": 1}
    assert sum(r["Eligible"] for r in tt) == 1
