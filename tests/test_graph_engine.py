import pytest
try:
    from graph_engine import (
        build_graph,
        detect_cycle,
        find_cycle_path,
        get_eligible_courses,
        get_missing_prereqs,
        hasse_graph,
        redundant_edges,
        layered_positions
    )
except ModuleNotFoundError:
    from curriculogic.graph_engine import (
        build_graph,
        detect_cycle,
        find_cycle_path,
        get_eligible_courses,
        get_missing_prereqs,
        hasse_graph,
        redundant_edges,
        layered_positions
    )


@pytest.fixture
def courses():
    return [
        {"code": "A", "name": "A", "credits": 3, "prereqs": []},
        {"code": "B", "name": "B", "credits": 4, "prereqs": ["A"]},
        {"code": "C", "name": "C", "credits": 3, "prereqs": ["A", "B"]},
        {"code": "D", "name": "D", "credits": 2, "prereqs": []},
    ]


def test_build_graph_and_cycle_detection(courses):
    G = build_graph(courses)
    assert G.number_of_nodes() == 4
    assert G.number_of_edges() == 3  # A->B, A->C, B->C
    assert detect_cycle(G) is False
    assert find_cycle_path(G) is None


def test_cycle_detection_positive():
    cyclic_courses = [
        {"code": "X", "name": "X", "credits": 3, "prereqs": ["Y"]},
        {"code": "Y", "name": "Y", "credits": 3, "prereqs": ["X"]},
    ]
    G = build_graph(cyclic_courses)
    assert detect_cycle(G) is True
    path = find_cycle_path(G)
    assert path is not None
    assert path[0] == path[-1]  # cycle closes


def test_get_eligible_and_missing_prereqs(courses):
    # Empty completion: A and D have no prereqs -> eligible
    elig = get_eligible_courses(courses, set())
    assert {c["code"] for c in elig} == {"A", "D"}

    # Completed A: A is not eligible (done). B has prereq A -> eligible.
    elig_a = get_eligible_courses(courses, {"A"})
    assert {c["code"] for c in elig_a} == {"B", "D"}

    # Missing prereqs check
    c_course = next(c for c in courses if c["code"] == "C")
    assert get_missing_prereqs(c_course, set()) == ["A", "B"]
    assert get_missing_prereqs(c_course, {"A"}) == ["B"]
    assert get_missing_prereqs(c_course, {"A", "B"}) == []


def test_hasse_and_redundant_edges(courses):
    # A->B, B->C, A->C. In Hasse diagram, A->C is redundant because A->B->C exists.
    G = build_graph(courses)
    H = hasse_graph(G)
    assert H.number_of_edges() == 2
    redundant = redundant_edges(G, H)
    assert ("A", "C") in redundant


def test_layered_positions(courses):
    G = build_graph(courses)
    pos = layered_positions(G)
    assert len(pos) == 4
    # Layer of A (no predecessors) should be 0.0
    assert pos["A"][0] == 0.0
    # Layer of B (predecessor A) should be 1.0
    assert pos["B"][0] == 1.0
    # Layer of C (predecessors A and B) should be 2.0
    assert pos["C"][0] == 2.0
