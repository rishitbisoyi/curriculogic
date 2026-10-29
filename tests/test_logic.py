import pytest

try:
    from logic import get_metrics
except ImportError:
    from curriculogic.logic import get_metrics

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
