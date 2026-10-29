from typing import List, Dict, Set, Tuple
import networkx as nx


def topological_sort(courses: List[Dict]) -> List[str]:
    """Return a list of course codes in topological order.
    Raises ValueError if a cycle is detected.
    """
    G = nx.DiGraph()
    for c in courses:
        G.add_node(c['code'])
    for c in courses:
        for pre in c['prereqs']:
            G.add_edge(pre, c['code'])
    try:
        order = list(nx.topological_sort(G))
        return order
    except nx.exception.NetworkXUnfeasible:
        raise ValueError('Circular prerequisite detected')


def plan_semesters_detailed(
    courses: List[Dict],
    completed: Set[str],
    max_credits: int,
    semesters: int,
    include_completed: bool = False,
) -> Dict:
    """Greedy semester planner returning full detail.

    Parameters:
      courses: list of course dicts (keys: code, name, credits, prereqs)
      completed: set of course codes already completed
      max_credits: maximum credits allowed in any single semester
      semesters: number of semesters available
      include_completed: if True, schedules all courses, ignoring completion status

    Returns a dict:
      status: 'complete' | 'partial' | 'infeasible'
      message: explanation for non-complete results ('' when complete)
      plan: list of semesters, each a list of course codes
      unscheduled: {code: reason} for courses that could not be placed

    Algorithm notes:
    The planner uses a greedy priority heuristic with topological ordering.
    Courses are placed semester by semester only after every prerequisite is
    completed or scheduled in a strictly EARLIER semester, and while remaining
    within the semester credit limit. While highly effective, this greedy approach
    is an approximation heuristic and does not guarantee a mathematically minimal
    number of semesters.
    """
    effective_completed = set() if include_completed else set(completed)
    remaining = courses if include_completed else [c for c in courses if c['code'] not in completed]

    try:
        topological_sort(courses)  # rejects circular prerequisites
    except ValueError as e:
        return {"status": "infeasible", "message": str(e), "plan": [], "unscheduled": {}}

    prereq_map = {c['code']: set(c['prereqs']) for c in courses}

    for c in remaining:
        if c['credits'] > max_credits:
            return {
                "status": "infeasible",
                "message": f"Course {c['code']} exceeds maximum credits per semester ({max_credits}). Planning impossible.",
                "plan": [], "unscheduled": {},
            }

    plan: List[List[str]] = [[] for _ in range(semesters)]
    used = [0] * semesters
    sem_of: Dict[str, int] = {}

    def ready(code: str, sem: int) -> bool:
        return all(p in effective_completed or (p in sem_of and sem_of[p] < sem) for p in prereq_map[code])

    for s in range(semesters):
        for c in remaining:
            code = c['code']
            if code in sem_of or not ready(code, s):
                continue
            if used[s] + c['credits'] <= max_credits:
                plan[s].append(code)
                used[s] += c['credits']
                sem_of[code] = s

    unscheduled: Dict[str, str] = {}
    for c in remaining:
        code = c['code']
        if code in sem_of:
            continue
        blocked = [p for p in c['prereqs'] if p not in effective_completed and p not in sem_of]
        if blocked:
            unscheduled[code] = "Waiting on prerequisite(s) that are not scheduled: " + ", ".join(blocked)
            continue
        scheduled_pre = [sem_of[p] for p in c['prereqs'] if p in sem_of]
        earliest = max(scheduled_pre) + 1 if scheduled_pre else 0
        if earliest >= semesters:
            if not scheduled_pre:
                unscheduled[code] = "No remaining credit capacity in any available semester."
            else:
                unscheduled[code] = f"Its prerequisites finish in semester {earliest}, so it needs semester {earliest + 1} or later."
        else:
            unscheduled[code] = "No remaining credit capacity in the semesters where it was eligible."

    if unscheduled:
        message = (f"Unable to schedule courses: {', '.join(unscheduled)} "
                   f"within {semesters} semesters respecting credit limit.")
        return {"status": "partial", "message": message, "plan": plan, "unscheduled": unscheduled}
    return {"status": "complete", "message": "", "plan": plan, "unscheduled": {}}


def plan_semesters(courses: List[Dict], completed: Set[str], max_credits: int, semesters: int, include_completed: bool = False):
    """Greedy semester planner.
    Returns a list of semesters, each a list of course codes, or an error string.
    """
    result = plan_semesters_detailed(courses, completed, max_credits, semesters, include_completed=include_completed)
    return result["plan"] if result["status"] == "complete" else result["message"]