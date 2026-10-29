import pytest
try:
    from counting import combinations, permutations, credit_capacity_check, pigeonhole_feasibility
except ModuleNotFoundError:
    from curriculogic.counting import combinations, permutations, credit_capacity_check, pigeonhole_feasibility


def test_combinations_standard():
    assert combinations(10, 3) == 120
    assert combinations(5, 5) == 1
    assert combinations(5, 0) == 1


def test_combinations_edge_cases():
    assert combinations(0, 0) == 1
    assert combinations(5, 6) == 0


def test_combinations_negative_raises():
    with pytest.raises(ValueError, match="non-negative"):
        combinations(-1, 2)
    with pytest.raises(ValueError, match="non-negative"):
        combinations(2, -1)


def test_permutations_standard():
    assert permutations(5, 2) == 20
    assert permutations(4, 4) == 24
    assert permutations(4, 0) == 1


def test_permutations_edge_cases():
    assert permutations(0, 0) == 1
    assert permutations(3, 4) == 0


def test_permutations_negative_raises():
    with pytest.raises(ValueError, match="non-negative"):
        permutations(-1, 2)
    with pytest.raises(ValueError, match="non-negative"):
        permutations(2, -1)


def test_credit_capacity_check():
    # Feasible: 30 required, 3 sems * 12 max = 36 capacity, min_load = ceil(30/3) = 10 <= 12
    res = credit_capacity_check(30, 12, 3)
    assert res["feasible"] is True
    assert res["min_load"] == 10
    assert res["capacity"] == 36

    # Infeasible: 40 required, 3 sems * 12 max = 36 capacity, min_load = ceil(40/3) = 14 > 12
    res_inf = credit_capacity_check(40, 12, 3)
    assert res_inf["feasible"] is False
    assert res_inf["min_load"] == 14

    # Non-positive semesters raises ValueError
    with pytest.raises(ValueError, match="semesters must be positive"):
        credit_capacity_check(20, 10, 0)
    with pytest.raises(ValueError, match="semesters must be positive"):
        credit_capacity_check(20, 10, -1)


def test_pigeonhole_feasibility():
    assert pigeonhole_feasibility(6, 12, 3, avg_course_credit=3) is True
    assert pigeonhole_feasibility(20, 12, 3, avg_course_credit=3) is False
