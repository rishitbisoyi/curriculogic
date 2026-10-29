import pytest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic import get_metrics, truth_table
from counting import combinations, permutations, credit_capacity_check
from graph_engine import (
    build_graph, detect_cycle, find_cycle_path, get_eligible_courses,
    get_missing_prereqs, hasse_graph, redundant_edges
)
from planner import plan_semesters_detailed, plan_semesters, topological_sort
from sample_data import SAMPLE_COURSES


@pytest.fixture
def basic_courses():
    return [
        {"code": "CS101", "name": "Intro to CS", "credits": 3, "prereqs": []},
        {"code": "CS102", "name": "Data Structures", "credits": 4, "prereqs": ["CS101"]},
        {"code": "MATH101", "name": "Calculus I", "credits": 4, "prereqs": []},
        {"code": "CS201", "name": "Algorithms", "credits": 4, "prereqs": ["CS102", "MATH101"]},
        {"code": "CS301", "name": "Senior Project", "credits": 3, "prereqs": ["CS201"]},
    ]


class TestCourseEligibility:
    """Test scenario 1-4: Adding courses, eligibility with and without prereqs, updates on completion."""

    def test_course_with_no_prereqs_is_immediately_eligible(self, basic_courses):
        completed = set()
        eligible = get_eligible_courses(basic_courses, completed)
        eligible_codes = [c["code"] for c in eligible]
        assert "CS101" in eligible_codes
        assert "MATH101" in eligible_codes
        assert "CS102" not in eligible_codes

    def test_dependent_course_blocked_when_prereqs_incomplete(self, basic_courses):
        completed = set()
        eligible = get_eligible_courses(basic_courses, completed)
        eligible_codes = [c["code"] for c in eligible]
        assert "CS102" not in eligible_codes
        assert "CS201" not in eligible_codes

        # Missing prereqs must report all missing, not just the first one
        cs201 = next(c for c in basic_courses if c["code"] == "CS201")
        missing = get_missing_prereqs(cs201, completed)
        assert set(missing) == {"CS102", "MATH101"}

    def test_marking_prereq_completed_updates_eligibility(self, basic_courses):
        completed = {"CS101"}
        eligible = get_eligible_courses(basic_courses, completed)
        eligible_codes = [c["code"] for c in eligible]
        assert "CS101" not in eligible_codes  # completed, so not in eligible
        assert "CS102" in eligible_codes      # now eligible
        assert "CS201" not in eligible_codes  # still blocked because MATH101 incomplete

        # Complete both CS102 and MATH101
        completed = {"CS101", "CS102", "MATH101"}
        eligible_now = get_eligible_courses(basic_courses, completed)
        eligible_now_codes = [c["code"] for c in eligible_now]
        assert "CS201" in eligible_now_codes

    def test_metrics_recalculation(self, basic_courses):
        completed = {"CS101", "MATH101"}
        total, comp_cnt, elig_cnt, rem_cr = get_metrics(basic_courses, completed)
        assert total == 5
        assert comp_cnt == 2
        assert elig_cnt == 1  # only CS102 is eligible
        assert rem_cr == 4 + 4 + 3  # CS102 (4) + CS201 (4) + CS301 (3) = 11


class TestCycleDetectionAndGraphs:
    """Test scenario 8: Circular dependencies detection and explanation."""

    def test_acyclic_graph_passes(self, basic_courses):
        G = build_graph(basic_courses)
        assert not detect_cycle(G)
        assert find_cycle_path(G) is None

        order = topological_sort(basic_courses)
        assert order.index("CS101") < order.index("CS102")
        assert order.index("CS102") < order.index("CS201")
        assert order.index("MATH101") < order.index("CS201")

    def test_circular_dependency_detected_and_path_returned(self):
        cyclic_courses = [
            {"code": "A", "name": "A", "credits": 3, "prereqs": ["B"]},
            {"code": "B", "name": "B", "credits": 3, "prereqs": ["C"]},
            {"code": "C", "name": "C", "credits": 3, "prereqs": ["A"]},
        ]
        G = build_graph(cyclic_courses)
        assert detect_cycle(G)
        path = find_cycle_path(G)
        assert path is not None
        assert len(path) >= 3
        # Path must start and end at the same node
        assert path[0] == path[-1]

        with pytest.raises(ValueError, match="Circular prerequisite"):
            topological_sort(cyclic_courses)

    def test_transitive_reduction_hasse(self):
        # A -> B -> C and direct edge A -> C
        courses = [
            {"code": "A", "name": "A", "credits": 3, "prereqs": []},
            {"code": "B", "name": "B", "credits": 3, "prereqs": ["A"]},
            {"code": "C", "name": "C", "credits": 3, "prereqs": ["A", "B"]},
        ]
        G = build_graph(courses)
        H = hasse_graph(G)
        assert G.has_edge("A", "C")
        assert not H.has_edge("A", "C")
        assert H.has_edge("A", "B")
        assert H.has_edge("B", "C")

        redundant = redundant_edges(G, H)
        assert ("A", "C") in redundant


class TestSemesterPlanner:
    """Test scenarios 9-11: Valid semester plan, credit limits, impossible plans, and cyclic graphs."""

    def test_valid_plan_ordering(self, basic_courses):
        completed = set()
        plan_res = plan_semesters_detailed(basic_courses, completed, max_credits=8, semesters=4)
        assert plan_res["status"] == "complete"
        plan = plan_res["plan"]

        # Find which semester each course is scheduled in
        sem_map = {}
        for s_idx, sem in enumerate(plan):
            for code in sem:
                sem_map[code] = s_idx

        # Verify prerequisite ordering: prerequisite in strictly earlier semester
        assert sem_map["CS101"] < sem_map["CS102"]
        assert sem_map["CS102"] < sem_map["CS201"]
        assert sem_map["MATH101"] < sem_map["CS201"]
        assert sem_map["CS201"] < sem_map["CS301"]

    def test_credit_limits_never_exceeded(self, basic_courses):
        max_cr = 5
        plan_res = plan_semesters_detailed(basic_courses, set(), max_credits=max_cr, semesters=6)
        by_code = {c["code"]: c for c in basic_courses}
        for sem in plan_res["plan"]:
            sem_credits = sum(by_code[c]["credits"] for c in sem)
            assert sem_credits <= max_cr

    def test_single_course_exceeds_credit_limit_is_infeasible(self, basic_courses):
        # CS102 is 4 credits, set max_credits to 3
        plan_res = plan_semesters_detailed(basic_courses, set(), max_credits=3, semesters=4)
        assert plan_res["status"] == "infeasible"
        assert "exceeds maximum credits" in plan_res["message"]

    def test_cyclic_courses_rejected_by_planner(self):
        cyclic_courses = [
            {"code": "A", "name": "A", "credits": 3, "prereqs": ["B"]},
            {"code": "B", "name": "B", "credits": 3, "prereqs": ["A"]},
        ]
        plan_res = plan_semesters_detailed(cyclic_courses, set(), max_credits=10, semesters=4)
        assert plan_res["status"] == "infeasible"
        assert "Circular" in plan_res["message"]

    def test_insufficient_semesters_reports_partial_plan_with_reasons(self, basic_courses):
        # Chain of 4 layers needs at least 4 semesters
        plan_res = plan_semesters_detailed(basic_courses, set(), max_credits=10, semesters=2)
        assert plan_res["status"] == "partial"
        assert len(plan_res["unscheduled"]) > 0

    def test_include_completed_parameter(self, basic_courses):
        completed = {"CS101", "MATH101"}
        # Without include_completed, only remaining 3 courses are planned
        res_default = plan_semesters_detailed(basic_courses, completed, max_credits=10, semesters=4)
        total_default = sum(len(s) for s in res_default["plan"])
        assert total_default == 3

        # With include_completed, all 5 courses are planned
        res_full = plan_semesters_detailed(basic_courses, completed, max_credits=10, semesters=4, include_completed=True)
        total_full = sum(len(s) for s in res_full["plan"])
        assert total_full == 5


class TestMathematicsLab:
    """Test scenario 12 & mathematical counting tools."""

    def test_combinations_3_from_5_is_10(self):
        # Explicit user requirement: choosing 3 electives from 5 must produce 10
        assert combinations(5, 3) == 10

    def test_combinations_boundary_conditions(self):
        assert combinations(5, 0) == 1
        assert combinations(5, 5) == 1
        assert combinations(5, 6) == 0
        with pytest.raises(ValueError):
            combinations(-1, 3)

    def test_permutations(self):
        assert permutations(5, 2) == 20
        assert permutations(5, 0) == 1
        assert permutations(5, 5) == 120
        assert permutations(4, 5) == 0
        with pytest.raises(ValueError):
            permutations(3, -1)

    def test_pigeonhole_credit_capacity(self):
        # 40 credits over 3 semesters at 12 credits limit: ceil(40/3) = 14 > 12 -> infeasible
        chk = credit_capacity_check(40, 12, 3)
        assert chk["min_load"] == 14
        assert not chk["feasible"]

        # 36 credits over 3 semesters at 12 credits limit: feasible
        chk2 = credit_capacity_check(36, 12, 3)
        assert chk2["min_load"] == 12
        assert chk2["feasible"]

        with pytest.raises(ValueError):
            credit_capacity_check(20, 10, 0)

    def test_truth_table_generator(self):
        table = truth_table(["A", "B"])
        assert len(table) == 4
        # Conjunction of A and B is only true when both are 1
        for row in table:
            if row["A"] == 1 and row["B"] == 1:
                assert row["Eligible"] == 1
            else:
                assert row["Eligible"] == 0

        # Vacuous truth with no prereqs
        table_empty = truth_table([])
        assert len(table_empty) == 1
        assert table_empty[0]["Eligible"] == 1


class TestSampleDataIntegrity:
    """Verify built-in sample curriculum dataset integrity."""

    def test_sample_courses_acyclic(self):
        G = build_graph(SAMPLE_COURSES)
        assert not detect_cycle(G)

    def test_sample_courses_valid_prereqs(self):
        codes = {c["code"] for c in SAMPLE_COURSES}
        for c in SAMPLE_COURSES:
            for p in c["prereqs"]:
                assert p in codes, f"Course {c['code']} has missing prerequisite {p}"
