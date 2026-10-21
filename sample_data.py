import json
from typing import List, Dict
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), 'courses.json')

SAMPLE_COURSES = [
    {"code": "PRG", "name": "Programming Fundamentals", "credits": 3, "prereqs": []},
    {"code": "MAT", "name": "Mathematics I", "credits": 3, "prereqs": []},
    {"code": "DST", "name": "Data Structures", "credits": 4, "prereqs": ["PRG"]},
    {"code": "DSM", "name": "Discrete Mathematics", "credits": 3, "prereqs": []},
    {"code": "ALG", "name": "Algorithms", "credits": 4, "prereqs": ["DST", "DSM"]},
    {"code": "DBM", "name": "Database Management Systems", "credits": 3, "prereqs": ["PRG"]},
    {"code": "OS", "name": "Operating Systems", "credits": 4, "prereqs": ["DST"]},
    {"code": "CN", "name": "Computer Networks", "credits": 3, "prereqs": ["OS"]},
    {"code": "AI", "name": "Introduction to AI", "credits": 3, "prereqs": ["ALG", "MAT"]},
    {"code": "ML", "name": "Machine Learning", "credits": 4, "prereqs": ["AI", "MAT"]},
]

def load_sample_courses() -> List[Dict]:
    """Load courses from persistent JSON file if exists, otherwise use sample data.
    Returns a list of course dictionaries.
    """
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            # If file is corrupted, fallback to sample
            pass
    # Write sample to file for future persistence
    save_courses(SAMPLE_COURSES)
    return SAMPLE_COURSES.copy()

def save_courses(courses: List[Dict]):
    """Save the given list of courses to the JSON file.
    """
    with open(DATA_FILE, 'w') as f:
        json.dump(courses, f, indent=2)
