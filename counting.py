from math import comb, perm, ceil
from typing import List, Dict, Set


def pigeonhole_feasibility(remaining_courses: int, max_credits_per_semester: int, semesters: int, avg_course_credit: int = 3) -> bool:
    """Simple pigeonhole feasibility check.
    Estimate total credit capacity and compare with required credits.
    avg_course_credit can be overridden; default 3.
    """
    total_capacity = max_credits_per_semester * semesters
    required_credits = remaining_courses * avg_course_credit
    return required_credits <= total_capacity


def credit_capacity_check(required_credits: int, max_credits: int, semesters: int) -> Dict:
    """Pigeonhole check using actual credits.
    If R credits are spread over s semesters, some semester carries at least
    ceil(R / s) credits. If that exceeds the per-semester limit, no plan exists.
    (Necessary, not sufficient: prerequisite chains can still make a plan impossible.)
    """
    if semesters <= 0:
        raise ValueError('semesters must be positive')
    capacity = max_credits * semesters
    return {
        "required": required_credits,
        "capacity": capacity,
        "min_load": ceil(required_credits / semesters),
        "feasible": required_credits <= capacity,
    }


def combinations(n: int, k: int) -> int:
    """Return C(n, k) using math.comb, with validation."""
    if k < 0 or n < 0:
        raise ValueError('n and k must be non-negative')
    if k > n:
        return 0
    return comb(n, k)


def permutations(n: int, k: int) -> int:
    """Return P(n, k) = n! / (n-k)! using math.perm, with validation."""
    if k < 0 or n < 0:
        raise ValueError('n and k must be non-negative')
    if k > n:
        return 0
    return perm(n, k)
