from itertools import product
from typing import List, Dict, Set, Tuple


def get_metrics(courses: List[Dict], completed: Set[str]) -> Tuple[int, int, int, int]:
    """Calculate dashboard metrics.
    Returns:
        total_courses, completed_count, eligible_count, remaining_credits
    """
    total = len(courses)
    completed_cnt = len(completed)
    # Eligible courses are those not completed and whose prerequisites are all completed
    eligible = [c for c in courses if c['code'] not in completed and all(p in completed for p in c['prereqs'])]
    eligible_cnt = len(eligible)
    remaining_credits = sum(c['credits'] for c in courses if c['code'] not in completed)
    return total, completed_cnt, eligible_cnt, remaining_credits


def truth_table(variables: List[str]) -> List[Dict]:
    """Truth table of the conjunction of `variables` (1 = completed).
    With no variables the conjunction is vacuously true (a course with no prerequisites)."""
    rows = []
    for values in product((0, 1), repeat=len(variables)):
        row = dict(zip(variables, values))
        row["Eligible"] = int(all(values))
        rows.append(row)
    return rows