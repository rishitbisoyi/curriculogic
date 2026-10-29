import pytest
try:
    from planner import topological_sort, plan_semesters_detailed, plan_semesters
except ModuleNotFoundError:
    from curriculogic.planner import topological_sort, plan_semesters_detailed, plan_semesters


@pytest.fixture
def curriculum():
    return [
        {"code": "PRG", "name": "Programming Fundamentals", "credits": 3, "prereqs": []},
        {"code": "MAT", "name": "Mathematics I", "credits": 3, "prereqs": []},
        {"code": "DST", "name": "Data Structures", "credits": 4, "prereqs": ["PRG"]},
        {"code": "DSM", "name": "Discrete Mathematics", "credits": 3, "prereqs": []},
        {"code": "ALG", "name": "Algorithms", "credits": 4, "prereqs": ["DST", "DSM"]},
    ]


def test_topological_sort_valid(curriculum):
    order = topological_sort(curriculum)
    assert len(order) == len(curriculum)
    assert order.index("PRG") < order.index("DST")
    assert order.index("DST") < order.index("ALG")
    assert order.index("DSM") < order.index("ALG")


def test_topological_sort_cycle():
    cyclic = [
        {"code": "A", "name": "A", "credits": 3, "prereqs": ["B"]},
        {"code": "B", "name": "B", "credits": 3, "prereqs": ["A"]},
    ]
    with pytest.raises(ValueError, match="Circular prerequisite detected"):
        topological_sort(cyclic)


def test_plan_semesters_detailed_complete(curriculum):
    # Total credits: 3+3+4+3+4 = 17. With 10 max credits and 3 semesters (cap 30), should complete.
    res = plan_semesters_detailed(curriculum, set(), max_credits=10, semesters=3)
    assert res["status"] == "complete"
    assert res["unscheduled"] == {}
    assert len(res["plan"]) == 3
    scheduled = [c for sem in res["plan"] for c in sem]
    assert len(scheduled) == len(curriculum)

    # Legacy wrapper test
    plan_out = plan_semesters(curriculum, set(), max_credits=10, semesters=3)
    assert isinstance(plan_out, list)
    assert len(plan_out) == 3


def test_plan_semesters_detailed_course_exceeds_max(curriculum):
    # DST has 4 credits, max_credits=3
    res = plan_semesters_detailed(curriculum, set(), max_credits=3, semesters=4)
    assert res["status"] == "infeasible"
    assert "exceeds maximum credits" in res["message"]


def test_plan_semesters_detailed_cycle():
    cyclic = [
        {"code": "A", "name": "A", "credits": 3, "prereqs": ["B"]},
        {"code": "B", "name": "B", "credits": 3, "prereqs": ["A"]},
    ]
    res = plan_semesters_detailed(cyclic, set(), max_credits=10, semesters=2)
    assert res["status"] == "infeasible"
    assert "Circular prerequisite" in res["message"]


def test_plan_semesters_detailed_partial(curriculum):
    # 1 semester with 5 max credits: only PRG (3) can fit (or PRG/MAT/DSM one of them).
    res = plan_semesters_detailed(curriculum, set(), max_credits=5, semesters=1)
    assert res["status"] == "partial"
    assert len(res["unscheduled"]) > 0


def test_plan_semesters_unscheduled_no_prereqs_message():
    # Test our edge case fix where course has no prerequisites but cannot be placed
    courses = [{"code": "A", "name": "A", "credits": 3, "prereqs": []}]
    res = plan_semesters_detailed(courses, set(), max_credits=10, semesters=0)
    assert res["status"] == "partial"
    assert res["unscheduled"]["A"] == "No remaining credit capacity in any available semester."
