import copy
import json
import re

import streamlit as st

st.set_page_config(
    page_title="CurricuLogic — Plan smarter. Understand the mathematics.",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui import (esc, inject_css, page_header, section_title, badge, course_card, empty_state,
                util_bar, legend, html_table, set_flash, show_flash)
from logic import get_metrics, truth_table
from graph_engine import (build_graph, draw_graph, detect_cycle, find_cycle_path, get_eligible_courses,
                          get_missing_prereqs, hasse_graph, redundant_edges,
                          COLOR_COMPLETED, COLOR_ELIGIBLE, COLOR_BLOCKED)
from planner import plan_semesters_detailed, topological_sort
from counting import combinations, permutations, credit_capacity_check
from sample_data import SAMPLE_COURSES, load_sample_courses, save_courses

inject_css()

NEW = "__new__"
PAGES = [
    "Dashboard",
    "Course Management",
    "Eligibility Checker",
    "Dependency Graph",
    "Semester Planner",
    "Mathematics Lab",
    "About the Project",
]
GRAPH_LEGEND = [("Completed", COLOR_COMPLETED), ("Eligible now", COLOR_ELIGIBLE), ("Blocked", COLOR_BLOCKED)]

# ── Session state ───────────────────────────────────────────
if "courses" not in st.session_state:
    st.session_state["courses"] = load_sample_courses()
if "completed" not in st.session_state:
    st.session_state["completed"] = set()
st.session_state.setdefault("nav", PAGES[0])
st.session_state.setdefault("cm_form", None)
st.session_state.setdefault("pending", None)


def get_courses():
    return st.session_state["courses"]


def get_completed():
    codes = {c["code"] for c in get_courses()}
    st.session_state["completed"] = set(st.session_state["completed"]) & codes
    return st.session_state["completed"]


def go_to(page: str):
    st.session_state["nav"] = page


def store_courses(courses):
    st.session_state["courses"] = courses
    save_courses(courses)


# ── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="cl-brand"><div class="cl-wordmark">Curricu<span>Logic</span></div>'
        '<div class="cl-brand-sub">Academic planning tool</div></div>',
        unsafe_allow_html=True,
    )
    st.radio("Navigation", PAGES, key="nav", label_visibility="collapsed")
    st.markdown(
        '<div class="cl-sidebar-foot"><strong>BAMAT205</strong><br>Discrete Mathematics and Linear Algebra'
        '<br>Undergraduate course project</div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════
#  Dashboard
# ════════════════════════════════════════════════════════════
def page_dashboard():
    show_flash()
    courses, completed = get_courses(), get_completed()
    page_header(
        "Overview", "Good to have you here",
        "CurricuLogic turns course prerequisites into a checked, credit-aware study plan "
        "using logic, graphs and counting from discrete mathematics.",
    )
    if not courses:
        empty_state("No courses yet", "Add your first course to start planning.")
        st.button("Open Course Management", type="primary", on_click=go_to, args=("Course Management",))
        return

    b1, b2, _ = st.columns([1, 1, 3])
    b1.button("Plan my semesters", type="primary", on_click=go_to, args=("Semester Planner",))
    b2.button("Check eligibility", on_click=go_to, args=("Eligibility Checker",))

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    total, done, elig_cnt, remaining_credits = get_metrics(courses, completed)
    cols = st.columns(4)
    for col, (label, val) in zip(cols, [("Total courses", total), ("Completed", done),
                                        ("Eligible now", elig_cnt), ("Remaining credits", remaining_credits)]):
        col.metric(label, val)

    eligible = get_eligible_courses(courses, completed)
    left, right = st.columns([3, 2], gap="large")
    with left:
        section_title("Prerequisite graph", "Arrows run from a prerequisite to the course that depends on it.")
        G = build_graph(courses)
        if detect_cycle(G):
            st.warning("The prerequisite data contains a cycle, so the graph cannot be drawn. Fix it in Course Management.")
        else:
            draw_graph(G, completed, eligible, compact=True)
            legend(GRAPH_LEGEND)
    with right:
        section_title("Ready to take", "Courses whose prerequisites are all completed.")
        if eligible:
            st.markdown("".join(
                course_card(c["code"], c["name"], f"{c['credits']} credits") for c in eligible
            ), unsafe_allow_html=True)
        elif remaining_credits == 0:
            st.success("Every course is completed.")
        else:
            st.info("Nothing is eligible yet. Mark completed courses in the Eligibility Checker.")

        section_title("Next step")
        total_cr = sum(c["credits"] for c in courses)
        done_cr = total_cr - remaining_credits
        st.progress(done_cr / total_cr if total_cr else 0.0, text=f"{done_cr} of {total_cr} credits completed")
        if remaining_credits == 0:
            st.caption("Nothing left to plan.")
        elif not completed:
            st.caption("No completed courses are recorded yet. Mark what you have finished so eligibility is accurate.")
        else:
            st.caption(f"{remaining_credits} credits remain. Generate a semester plan to schedule them.")


# ════════════════════════════════════════════════════════════
#  Course Management
# ════════════════════════════════════════════════════════════
def open_form(target):
    st.session_state["cm_form"] = target


def request_reset():
    st.session_state["pending"] = ("reset", None)


def course_form(target):
    courses = get_courses()
    existing = None if target == NEW else next((c for c in courses if c["code"] == target), None)
    if target != NEW and existing is None:
        st.session_state["cm_form"] = None
        return
    is_edit = existing is not None
    names = {c["code"]: c["name"] for c in courses}

    with st.container(border=True):
        st.markdown(f"**{'Edit ' + target if is_edit else 'Add a course'}**")
        with st.form(f"course_form_{target}"):
            c1, c2, c3 = st.columns([1, 2.5, 1])
            code = c1.text_input("Course code", value=existing["code"] if is_edit else "",
                                 disabled=is_edit, max_chars=10, placeholder="e.g. CS101")
            name = c2.text_input("Course name", value=existing["name"] if is_edit else "",
                                 max_chars=100, placeholder="e.g. Data Structures")
            credits = c3.number_input("Credits", min_value=1, max_value=10, step=1,
                                      value=int(existing["credits"]) if is_edit else 3)
            options = [c["code"] for c in courses if not (is_edit and c["code"] == existing["code"])]
            default = [p for p in existing["prereqs"] if p in options] if is_edit else []
            prereqs = st.multiselect(
                "Prerequisites", options, default=default,
                format_func=lambda x: f"{x} — {names.get(x, '')}",
                help="Choose existing courses that must be completed first. Leave empty if there are none.",
                placeholder="Choose prerequisites (optional)",
            )
            b1, b2, _ = st.columns([1, 1, 4])
            save = b1.form_submit_button("Save course", type="primary")
            cancel = b2.form_submit_button("Cancel")

        if cancel:
            st.session_state["cm_form"] = None
            st.rerun()
        if save:
            code = (existing["code"] if is_edit else code).strip().upper()
            errors = []
            if not code:
                errors.append("Course code is required.")
            elif not re.fullmatch(r"[A-Z0-9_-]{1,10}", code):
                errors.append("Course code may contain only letters, digits, hyphens and underscores.")
            elif not is_edit and code in names:
                errors.append(f"{code} already exists. Select it in the table above and choose Edit to change it.")
            if not name.strip():
                errors.append("Course name is required.")
            new = {"code": code, "name": name.strip(), "credits": int(credits), "prereqs": list(prereqs)}
            trial = [new if c["code"] == code else c for c in courses] if is_edit else courses + [new]
            if not errors:
                cyc = find_cycle_path(build_graph(trial))
                if cyc:
                    errors.append("Saving would create a circular prerequisite chain: " + " → ".join(cyc) + ".")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                store_courses(trial)
                st.session_state["cm_form"] = None
                set_flash("success", f"Course {code} {'updated' if is_edit else 'added'}.")
                st.rerun()


def page_courses():
    show_flash()
    courses = get_courses()
    page_header("Course catalogue", "Course Management",
                "Add, edit and remove courses. Prerequisite links drive every other page.")

    t1, t2, t3 = st.columns([3, 1, 1.4])
    search = t1.text_input("Search courses", placeholder="Search by code or name", label_visibility="collapsed")
    t2.button("Add course", type="primary", on_click=open_form, args=(NEW,))
    t3.button("Restore sample data", on_click=request_reset)

    if not courses:
        empty_state("No courses defined", "Choose “Add course” to create the first one, or restore the sample data.")
    else:
        q = search.strip().upper()
        shown = [c for c in courses if q in c["code"].upper() or q in c["name"].upper()] if q else courses
        if shown:
            rows = [{"Code": c["code"], "Course": c["name"], "Credits": c["credits"],
                     "Prerequisites": ", ".join(c["prereqs"]) if c["prereqs"] else "—"} for c in shown]
            st.dataframe(rows, hide_index=True, use_container_width=True, height=min(40 + 35 * len(rows), 430))
            st.caption(f"{len(shown)} of {len(courses)} courses · {sum(c['credits'] for c in shown)} credits shown")
        else:
            st.info("No courses match your search.")

        a1, a2, a3 = st.columns([3, 1, 1])
        sel = a1.selectbox("Select a course to edit or delete", [c["code"] for c in courses],
                           format_func=lambda x: f"{x} — {next(c['name'] for c in courses if c['code'] == x)}")
        a2.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        a3.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        a2.button("Edit", on_click=open_form, args=(sel,))
        if a3.button("Delete"):
            st.session_state["pending"] = ("delete", sel)

    pending = st.session_state["pending"]
    if pending:
        kind, val = pending
        with st.container(border=True):
            if kind == "delete":
                deps = [c["code"] for c in courses if val in c["prereqs"]]
                msg = f"Delete **{val}**? This cannot be undone."
                if deps:
                    msg += f" It is a prerequisite of {', '.join(deps)}; those links will be removed."
            else:
                msg = "Replace all current courses with the built-in sample data? Your edits and completed courses will be lost."
            st.warning(msg)
            c1, c2, _ = st.columns([1.2, 1, 4])
            if c1.button("Confirm", type="primary", key="pending_ok"):
                if kind == "delete":
                    store_courses([dict(c, prereqs=[p for p in c["prereqs"] if p != val])
                                   for c in courses if c["code"] != val])
                    st.session_state["completed"].discard(val)
                    if st.session_state["cm_form"] == val:
                        st.session_state["cm_form"] = None
                    set_flash("success", f"Course {val} deleted.")
                else:
                    store_courses(copy.deepcopy(SAMPLE_COURSES))
                    st.session_state["completed"] = set()
                    st.session_state["cm_form"] = None
                    set_flash("success", "Sample data restored.")
                st.session_state["pending"] = None
                st.rerun()
            if c2.button("Cancel", key="pending_cancel"):
                st.session_state["pending"] = None
                st.rerun()

    if st.session_state["cm_form"] is not None:
        course_form(st.session_state["cm_form"])


# ════════════════════════════════════════════════════════════
#  Eligibility Checker
# ════════════════════════════════════════════════════════════
def page_eligibility():
    show_flash()
    courses = get_courses()
    page_header("Eligibility", "Eligibility Checker",
                "A course is eligible when every one of its prerequisites is completed. Choose what you have finished.")
    if not courses:
        empty_state("No courses defined", "Add courses first in Course Management.")
        return

    codes = [c["code"] for c in courses]
    names = {c["code"]: c["name"] for c in courses}
    if "completed_widget" not in st.session_state:
        st.session_state["completed_widget"] = sorted(get_completed())

    def sync():
        st.session_state["completed"] = set(st.session_state["completed_widget"])

    def clear():
        st.session_state["completed_widget"] = []
        st.session_state["completed"] = set()

    with st.container(border=True):
        st.markdown("**Completed courses**")
        st.multiselect("Completed courses", codes, key="completed_widget", on_change=sync,
                       format_func=lambda x: f"{x} — {names[x]}", label_visibility="collapsed",
                       placeholder="Choose the courses you have finished")
        st.button("Clear selections", on_click=clear)

    completed = get_completed()
    elig = get_eligible_courses(courses, completed)
    elig_codes = {c["code"] for c in elig}
    done = [c for c in courses if c["code"] in completed]
    blocked = [c for c in courses if c["code"] not in completed and c["code"] not in elig_codes]

    if detect_cycle(build_graph(courses)):
        st.warning("The prerequisite data contains a cycle, so some courses can never become eligible.")

    col_done, col_elig, col_block = st.columns(3, gap="large")
    with col_done:
        st.markdown(f'<div class="cl-colhead">{badge("completed")}<span class="cl-count">{len(done)}</span></div>',
                    unsafe_allow_html=True)
        if done:
            st.markdown("".join(course_card(c["code"], c["name"], f"{c['credits']} credits") for c in done),
                        unsafe_allow_html=True)
        else:
            st.caption("No courses marked as completed.")
    with col_elig:
        st.markdown(f'<div class="cl-colhead">{badge("eligible", "Eligible now")}<span class="cl-count">{len(elig)}</span></div>',
                    unsafe_allow_html=True)
        if elig:
            cards = []
            for c in elig:
                why = ("No prerequisites" if not c["prereqs"] else "All prerequisites met: " + ", ".join(c["prereqs"]))
                cards.append(course_card(c["code"], c["name"], f"{c['credits']} credits · {why}"))
            st.markdown("".join(cards), unsafe_allow_html=True)
        else:
            st.caption("No courses are eligible right now.")
    with col_block:
        st.markdown(f'<div class="cl-colhead">{badge("blocked", "Blocked")}<span class="cl-count">{len(blocked)}</span></div>',
                    unsafe_allow_html=True)
        if blocked:
            cards = []
            for c in blocked:
                missing = get_missing_prereqs(c, completed)
                cards.append(course_card(c["code"], c["name"],
                                         f"{c['credits']} credits · Missing: " + ", ".join(missing)))
            st.markdown("".join(cards), unsafe_allow_html=True)
        else:
            st.caption("No courses are blocked.")


# ════════════════════════════════════════════════════════════
#  Dependency Graph
# ════════════════════════════════════════════════════════════
def page_graph():
    show_flash()
    courses, completed = get_courses(), get_completed()
    page_header("Visualisation", "Dependency Graph",
                "Each arrow points from a prerequisite to the course that depends on it.")
    if not courses:
        empty_state("No courses defined", "Add courses first in Course Management.")
        return

    codes = {c["code"] for c in courses}
    unknown = sorted({p for c in courses for p in c["prereqs"] if p not in codes})
    if unknown:
        st.warning("Ignored prerequisite codes that are not in the catalogue: " + ", ".join(unknown))

    G = build_graph(courses)
    cyc = find_cycle_path(G)
    if cyc:
        st.error("Circular prerequisite detected: " + " → ".join(cyc) +
                 ". Remove one of these links in Course Management to draw the graph.")
        return

    view = st.radio("Diagram", ["Prerequisite graph", "Hasse diagram"], horizontal=True,
                    key="graph_view", label_visibility="collapsed")
    eligible = get_eligible_courses(courses, completed)
    hasse = view == "Hasse diagram"
    if hasse:
        st.caption("The Hasse diagram is the transitive reduction: an edge is hidden when a longer "
                   "prerequisite chain already implies it. Arrows still point from prerequisite to dependent.")
    else:
        st.caption("Courses are arranged in columns by the length of their longest prerequisite chain. "
                   "Read left to right.")
    draw_graph(G, completed, eligible, hasse=hasse)
    legend(GRAPH_LEGEND)

    if hasse:
        hidden = redundant_edges(G, hasse_graph(G))
        if hidden:
            st.markdown("**Hidden as redundant:** " + ", ".join(f"`{u} → {v}`" for u, v in hidden))
        else:
            st.markdown("No redundant edges: this prerequisite graph is already its own Hasse diagram.")

    with st.expander("Course key"):
        elig_codes = {c["code"] for c in eligible}
        st.dataframe(
            [{"Code": c["code"], "Course": c["name"], "Credits": c["credits"],
              "Status": "Completed" if c["code"] in completed else ("Eligible" if c["code"] in elig_codes else "Blocked")}
             for c in courses],
            hide_index=True, use_container_width=True)


# ════════════════════════════════════════════════════════════
#  Semester Planner
# ════════════════════════════════════════════════════════════
def _plan_signature(courses, completed, mc, sems):
    return json.dumps([courses, sorted(completed), mc, sems], sort_keys=True)


def render_plan(stored, courses):
    result, mc = stored["result"], stored["mc"]
    by_code = {c["code"]: c for c in courses}
    status, plan = result["status"], result["plan"]

    if status == "infeasible":
        st.error(result["message"])
        return
    scheduled = sum(len(s) for s in plan)
    used_sems = sum(1 for s in plan if s)
    if status == "complete":
        st.success(f"Complete plan: all {scheduled} remaining courses fit in {used_sems} of {len(plan)} semesters.")
    else:
        st.warning(f"Partial plan: {scheduled} courses scheduled; {len(result['unscheduled'])} could not be placed.")
    st.caption("This is a greedy plan: it is valid, but it is not proven to use the fewest semesters, "
               "and a different ordering could sometimes schedule courses this one cannot.")

    for i, sem in enumerate(plan, 1):
        sem_courses = [by_code[c] for c in sem]
        used = sum(c["credits"] for c in sem_courses)
        with st.container(border=True):
            st.markdown(
                f'<div class="cl-sem-head"><span class="cl-sem-title">Semester {i}</span>'
                f'<span class="cl-sem-credits">{used} / {mc} credits · {mc - used} unused</span></div>'
                + util_bar(used, mc),
                unsafe_allow_html=True)
            if sem_courses:
                rows = [[f"<strong>{esc(c['code'])}</strong>", esc(c["name"]), str(c["credits"]),
                         esc(", ".join(c["prereqs"]) if c["prereqs"] else "—")] for c in sem_courses]
                st.markdown(html_table(["Code", "Course", "Credits", "Prerequisites"], rows,
                                       ["left", "left", "center", "left"],
                                       footer=["", "Total credits", str(used), ""]), unsafe_allow_html=True)
            else:
                st.caption("No courses scheduled in this semester.")

    if result["unscheduled"]:
        section_title("Not scheduled", "Why each course could not be placed.")
        rows = [[f"<strong>{esc(code)}</strong>", esc(by_code[code]["name"]), esc(reason)]
                for code, reason in result["unscheduled"].items()]
        st.markdown(html_table(["Code", "Course", "Reason"], rows), unsafe_allow_html=True)


def page_planner():
    show_flash()
    courses, completed = get_courses(), get_completed()
    page_header("Planning", "Semester Planner",
                "Spread the remaining courses across semesters without exceeding the credit limit or breaking prerequisites.")
    if not courses:
        empty_state("No courses defined", "Add courses first in Course Management.")
        return
    remaining = [c for c in courses if c["code"] not in completed]
    if not remaining:
        st.success("Every course is already completed. Nothing to plan.")
        return
    rem_credits = sum(c["credits"] for c in remaining)

    with st.container(border=True):
        c1, c2 = st.columns(2)
        mc = int(c1.number_input("Maximum credits per semester", min_value=1, max_value=30, value=12, key="plan_max"))
        sems = int(c2.number_input("Number of semesters", min_value=1, max_value=12, value=4, key="plan_sems"))
        chk = credit_capacity_check(rem_credits, mc, sems)
        st.caption(f"{len(remaining)} courses · {rem_credits} credits remaining · capacity {mc} × {sems} = {chk['capacity']} credits")
        if not chk["feasible"]:
            st.warning(f"By the pigeonhole principle some semester would need at least {chk['min_load']} credits, "
                       f"above the limit of {mc}. No plan can finish every course with these settings.")
        generate = st.button("Generate plan", type="primary")

    sig = _plan_signature(courses, completed, mc, sems)
    if generate:
        st.session_state["plan"] = {
            "sig": sig, "mc": mc, "sems": sems,
            "result": plan_semesters_detailed(courses, completed, mc, sems),
        }
    stored = st.session_state.get("plan")
    if stored and stored["sig"] == sig:
        render_plan(stored, courses)
    elif stored:
        st.info("Courses, completed courses or settings changed since the last plan. Generate the plan again.")
    else:
        empty_state("No plan yet", "Set your limits and choose “Generate plan”.")


# ════════════════════════════════════════════════════════════
#  Mathematics Lab
# ════════════════════════════════════════════════════════════
def page_math():
    show_flash()
    courses, completed = get_courses(), get_completed()
    page_header("Mathematics", "Mathematics Lab",
                "The discrete mathematics behind each feature, with examples drawn from your current course data.")
    tabs = st.tabs(["Logic", "Relations", "Partial orders", "Topological sort", "Pigeonhole", "Counting"])
    G = build_graph(courses)
    cyc = find_cycle_path(G)

    with tabs[0]:
        st.markdown("**Mathematical logic.** Eligibility is a conjunction of propositions. Let *done(p)* be true when "
                    "course *p* is completed. A course is eligible exactly when all of its prerequisites are done.")
        st.latex(r"\mathrm{eligible}(c) \iff \bigwedge_{p \in \mathrm{prereq}(c)} \mathrm{done}(p)")
        with_pre = [c for c in courses if c["prereqs"]]
        if with_pre:
            sel = st.selectbox("Worked example: choose a course", [c["code"] for c in with_pre],
                               format_func=lambda x: f"{x} — {next(c['name'] for c in with_pre if c['code'] == x)}")
            variables = next(c for c in with_pre if c["code"] == sel)["prereqs"]
        else:
            sel, variables = "C", ["A", "B"]
        if len(variables) <= 5:
            st.caption(f"Truth table for {sel}. 1 = completed. Only the last row makes the course eligible.")
            st.dataframe(truth_table(variables), hide_index=True, use_container_width=True)
        else:
            st.caption("This course has more than 5 prerequisites, so its truth table (more than 32 rows) is not shown.")
        st.caption("In the app: the Eligibility Checker evaluates this conjunction for every course.")

    with tabs[1]:
        st.markdown("**Relations and prerequisite graphs.** The prerequisite relation R on the set of courses C "
                    "contains the pair (p, c) when p is a direct prerequisite of c. Drawing each pair as an arrow gives a directed graph.")
        st.latex(r"R = \{(p, c) \in C \times C : p \text{ is a direct prerequisite of } c\}")
        pairs = list(G.edges())
        if pairs:
            shown = ", ".join(f"({u}, {v})" for u, v in pairs[:6]) + (", …" if len(pairs) > 6 else "")
            st.code(f"R = {{{shown}}}   # {len(pairs)} pairs in your data", language=None)
        else:
            st.caption("Your courses have no prerequisite links yet.")
        st.caption("In the app: the Dependency Graph page draws R.")

    with tabs[2]:
        st.markdown("**Partial orders and Hasse diagrams.** Write a ≤ b when there is a chain of prerequisites from a to b "
                    "(or a = b). This reflexive-transitive closure of the prerequisite relation is a partial order when the data has no cycles. "
                    "A Hasse diagram keeps only the covering pairs: b covers a when a < b and nothing lies strictly between them.")
        st.latex(r"b \text{ covers } a \iff a < b \text{ and there is no } c \text{ with } a < c < b")
        if cyc:
            st.warning("Your data has a cycle (" + " → ".join(cyc) + "), so it is not a partial order.")
        else:
            H = hasse_graph(G)
            hidden = redundant_edges(G, H)
            st.markdown(f"Your graph has **{G.number_of_edges()}** edges; its Hasse diagram has **{H.number_of_edges()}**.")
            if hidden:
                st.markdown("Removed because a longer chain implies them: " + ", ".join(f"`{u} → {v}`" for u, v in hidden))
        st.caption("In the app: choose “Hasse diagram” on the Dependency Graph page.")

    with tabs[3]:
        st.markdown("**Topological sorting.** A topological order lists every course so that each prerequisite appears "
                    "before the courses that depend on it. One exists exactly when the graph has no cycle.")
        st.latex(r"\text{for every edge } (u, v):\ \mathrm{position}(u) < \mathrm{position}(v)")
        if cyc:
            st.warning("No topological order exists because of the cycle " + " → ".join(cyc) + ".")
        elif courses:
            st.code(" → ".join(topological_sort(courses)), language=None)
            st.caption("One valid order for your courses (there are usually several).")
        st.caption("In the app: the planner uses a topological sort to reject circular data, then schedules each course "
                   "only after its prerequisites sit in earlier semesters.")

    with tabs[4]:
        st.markdown("**Pigeonhole principle.** If R credits must fit into s semesters, some semester carries at least "
                    "⌈R / s⌉ credits. If that exceeds the per-semester limit k, no plan can exist.")
        st.latex(r"\left\lceil \tfrac{R}{s} \right\rceil > k \implies \text{no valid plan}")
        st.markdown("**Example:** 40 credits over 3 semesters at 12 credits each: ⌈40 / 3⌉ = 14 > 12, so it is impossible.")
        rem = sum(c["credits"] for c in courses if c["code"] not in completed)
        p1, p2, p3 = st.columns(3)
        r_val = int(p1.number_input("Credits to schedule (R)", min_value=0, value=rem, key="ph_r"))
        k_val = int(p2.number_input("Max per semester (k)", min_value=1, value=12, key="ph_k"))
        s_val = int(p3.number_input("Semesters (s)", min_value=1, value=4, key="ph_s"))
        chk = credit_capacity_check(r_val, k_val, s_val)
        msg = f"⌈{r_val} / {s_val}⌉ = {chk['min_load']}  vs  k = {k_val}"
        (st.success if chk["feasible"] else st.error)(
            msg + (" → passes the check." if chk["feasible"] else " → impossible."))
        st.caption("Passing is necessary but not sufficient: prerequisite chains can still prevent a plan. "
                   "In the app: the Semester Planner shows this check above the Generate button.")

    with tabs[5]:
        st.markdown("**Permutations and combinations.** Choosing k courses from n without regard to order uses combinations; "
                    "when the order matters (for example a sequence of courses) use permutations.")
        st.latex(r"C(n,k) = \frac{n!}{k!\,(n-k)!} \qquad P(n,k) = \frac{n!}{(n-k)!}")
        eligible_n = len(get_eligible_courses(courses, completed))
        st.markdown("**Example:** choosing 3 of 10 electives gives C(10, 3) = 120 ways.")
        n1, n2 = st.columns(2)
        n = int(n1.number_input("Total items (n)", min_value=0, value=max(eligible_n, 5), key="cnt_n"))
        k = int(n2.number_input("Choose k", min_value=0, value=min(3, max(eligible_n, 5)), key="cnt_k"))
        st.success(f"C({n}, {k}) = {combinations(n, k):,}     P({n}, {k}) = {permutations(n, k):,}")
        if k > n:
            st.caption("k is larger than n, so there are 0 ways.")
        st.caption(f"The default n is your number of currently eligible courses ({eligible_n}).")

    st.caption("Scope: the app demonstrates logic, relations and partial orders, and counting. Other topics from the "
               "syllabus, including linear algebra, are not implemented.")


# ════════════════════════════════════════════════════════════
#  About
# ════════════════════════════════════════════════════════════
def page_about():
    page_header("Project", "About CurricuLogic",
                "Smart course prerequisite planner. BAMAT205: Discrete Mathematics and Linear Algebra.")
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown(
            """
<div class="cl-prose">

### Overview
CurricuLogic is a web application that models a degree's course prerequisites as a mathematical structure,
checks which courses a student may take, and builds a credit-limited semester plan.

### Problem statement
Students often learn too late that a course needed a prerequisite they skipped, or that a semester's credit load
makes a plan impossible. Prerequisite rules are a partial order, so the questions can be answered precisely with
discrete mathematics instead of by trial and error.

### Objectives
- Represent prerequisites as a directed graph and a Hasse diagram.
- Decide eligibility using propositional logic.
- Detect circular prerequisites and order courses topologically.
- Generate semester plans under a credit limit and report what cannot be scheduled.
- Illustrate the underlying mathematics with examples from the live data.

### Scope and limitations
- Data is stored in session state and a local JSON file; there is no login or multi-user support.
- The semester planner is a greedy heuristic; it does not prove the fewest-semester plan.
- Only direct prerequisites are modelled; co-requisites, course offerings by term and electives are not.
- Linear algebra topics are not implemented.

</div>
""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
<div class="cl-prose">

### Mathematical concepts
1. Propositional logic: conjunction of prerequisites.
2. Relations, partial orders and Hasse diagrams.
3. Topological sorting.
4. Counting: pigeonhole principle, permutations and combinations.

### Technology stack
- Python and Streamlit: application and interface
- NetworkX: graph algorithms
- Matplotlib: graph drawing
- pytest: automated tests

### Team responsibilities
| Member | Responsibility |
|---|---|
| Member 1 | Logic and eligibility |
| Member 2 | Graph algorithms and visualisation |
| Member 3 | Semester planning and counting |
| Member 4 | Interface and course management |
| Member 5 | Testing and documentation |

</div>
""",
            unsafe_allow_html=True,
        )
    st.caption("Developed by the BAMAT205 student team.")


PAGE_FUNCS = {
    "Dashboard": page_dashboard,
    "Course Management": page_courses,
    "Eligibility Checker": page_eligibility,
    "Dependency Graph": page_graph,
    "Semester Planner": page_planner,
    "Mathematics Lab": page_math,
    "About the Project": page_about,
}
PAGE_FUNCS[st.session_state["nav"]]()