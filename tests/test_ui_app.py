import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parent.parent / "app.py"


def test_app_dashboard_loads():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception
    # Check metric widgets
    assert len(at.metric) >= 4
    # Dashboard metrics
    labels = [m.label for m in at.metric]
    assert "Total courses" in labels
    assert "Completed" in labels
    assert "Eligible now" in labels
    assert "Remaining credits" in labels


def test_app_navigation_eligibility():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Select Eligibility Checker
    at.radio[0].set_value("Eligibility Checker").run()
    assert not at.exception
    # Verify completed multiselect exists
    assert len(at.multiselect) >= 1


def test_app_navigation_course_management():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Select Course Management
    at.radio[0].set_value("Course Management").run()
    assert not at.exception
    # Verify add course button and dataframe exist
    assert len(at.dataframe) >= 1


def test_app_navigation_graph():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Select Dependency Graph
    at.radio[0].set_value("Dependency Graph").run()
    assert not at.exception
    # Verify radio view for graph/hasse
    assert len(at.radio) >= 2


def test_app_navigation_planner():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Select Semester Planner
    at.radio[0].set_value("Semester Planner").run()
    assert not at.exception
    # Click generate plan button
    generate_btn = next((b for b in at.button if b.label == "Generate plan"), None)
    assert generate_btn is not None
    generate_btn.click().run()
    assert not at.exception


def test_app_navigation_math_lab():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Select Mathematics Lab
    at.radio[0].set_value("Mathematics Lab").run()
    assert not at.exception


def test_app_navigation_about():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Select About the Project
    at.radio[0].set_value("About the Project").run()
    assert not at.exception
