import copy
import json
import re

import streamlit as st

st.set_page_config(
    page_title="CurricuLogic — Smart Academic Planning",
    page_icon="🎓",
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
PAGE_ICONS = {
    "Dashboard": "📊 Dashboard",
    "Course Management": "📚 Course Management",
    "Eligibility Checker": "✅ Eligibility Checker",
    "Dependency Graph": "🕸️ Dependency Graph",
    "Semester Planner": "🗓️ Semester Planner",
    "Mathematics Lab": "🔬 Mathematics Lab",
    "About the Project": "ℹ️ About the Project",
}
GRAPH_LEGEND = [("Completed", COLOR_COMPLETED, "✓"), ("Eligible now", COLOR_ELIGIBLE, "★"), ("Blocked", COLOR_BLOCKED, "⊘")]

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
        '<div class="cl-brand">'
        '<div class="cl-wordmark">Curricu<span>Logic</span></div>'
        '<div class="cl-brand-sub">Smart Course Prerequisite Planner</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.radio("Navigation", PAGES, key="nav", format_func=lambda p: PAGE_ICONS.get(p, p), label_visibility="collapsed")
    st.markdown(
        '<div class="cl-sidebar-foot"><strong>BAMAT205</strong><br>Discrete Mathematics and Linear Algebra'
        '<br>Academic Project</div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════
#  Dashboard
# ════════════════════════════════════════════════════════════
def page_dashboard():
    show_flash()
    courses, completed = get_courses(), get_completed()
    page_header(
        "Overview", "Academic Planning Dashboard",
        "CurricuLogic models prerequisites as a mathematical partial order to generate conflict-free, credit-aware study plans.",
    )
    if not courses:
        empty_state("No courses in catalogue", "Add your first course to begin modeling your academic degree.")
        st.button("Open Course Management", type="primary", on_click=go_to, args=("Course Management",))
        return

    # Key metric cards
    total, done, elig_cnt, remaining_credits = get_metrics(courses, completed)
    blocked_cnt = total - done - elig_cnt
    total_cr = sum(c["credits"] for c in courses)
    done_cr = total_cr - remaining_credits

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Courses", f"{total}", f"{total_cr} credits")
    m2.metric("Completed", f"{done}", f"{done_cr} credits done")
    m3.metric("Eligible Now", f"{elig_cnt}", "Ready to enroll")
    m4.metric("Blocked", f"{blocked_cnt}", f"{remaining_credits} credits left")

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    eligible = get_eligible_courses(courses, completed)
    left, right = st.columns([1.75, 1.25], gap="large")

    with left:
        with st.container(border=True):
            st.markdown("### 🕸️ Prerequisite Dependency Structure")
            st.caption("Directed graph: arrows point from a prerequisite to the course that depends on it.")
            G = build_graph(courses)
            cyc = find_cycle_path(G)
            if cyc:
                st.error("⚠️ **Circular prerequisite detected:** " + " → ".join(cyc) + ". Planning is impossible until this cycle is fixed in Course Management.")
            else:
                draw_graph(G, completed, eligible, compact=True)
                legend(GRAPH_LEGEND)

    with right:
        with st.container(border=True):
            st.markdown("### 🚀 Quick Actions")
            st.button("🗓️ Plan My Semesters", type="primary", use_container_width=True, on_click=go_to, args=("Semester Planner",))
            st.button("✅ Check Course Eligibility", use_container_width=True, on_click=go_to, args=("Eligibility Checker",))

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.markdown("### 📚 Degree Progress")
            pct = done_cr / total_cr if total_cr else 0.0
            st.progress(pct, text=f"{done_cr} of {total_cr} credits completed ({int(pct*100)}%)")

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.markdown("### ★ Ready to Take Now")
            if eligible:
                cards = [course_card(c["code"], c["name"], f"{c['credits']} credits · Foundational" if not c["prereqs"] else f"{c['credits']} credits · Prereqs satisfied") for c in eligible[:4]]
                st.markdown("".join(cards), unsafe_allow_html=True)
                if len(eligible) > 4:
                    st.caption(f"+ {len(eligible) - 4} more courses available in Eligibility Checker.")
            elif remaining_credits == 0:
                st.success("🎉 All degree courses have been successfully completed!")
            else:
                st.info("No courses currently eligible. Mark your completed courses to unlock dependents.")


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
        st.markdown(f"### {'✏️ Edit Course ' + target if is_edit else '➕ Add New Course'}")
        with st.form(f"course_form_{target}"):
            c1, c2, c3 = st.columns([1.2, 2.8, 1])
            code = c1.text_input("Course Code *", value=existing["code"] if is_edit else "",
                                 disabled=is_edit, max_chars=10, placeholder="e.g. CS101")
            name = c2.text_input("Course Name *", value=existing["name"] if is_edit else "",
                                 placeholder="e.g. Data Structures & Algorithms")
            credits = c3.number_input("Credits *", min_value=1, max_value=10, step=1,
                                      value=int(existing["credits"]) if is_edit else 3)
            options = [c["code"] for c in courses if not (is_edit and c["code"] == existing["code"])]
            default = [p for p in existing["prereqs"] if p in options] if is_edit else []
            prereqs = st.multiselect(
                "Prerequisites (Must be completed strictly before this course)", options, default=default,
                format_func=lambda x: f"{x} — {names.get(x, '')}",
                help="Select one or more prerequisite courses. Leave empty for introductory / foundational courses.",
                placeholder="Select prerequisites (optional)",
            )
            b1, b2, _ = st.columns([1.2, 1, 3.8])
            save = b1.form_submit_button("Save Course", type="primary")
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
                errors.append("Course code may contain only letters, digits, hyphens and underscores (up to 10 characters).")
            elif not is_edit and code in names:
                errors.append(f"Course code '{code}' already exists. Select it from the table below to edit.")
            if not name.strip():
                errors.append("Course name is required.")
            new = {"code": code, "name": name.strip(), "credits": int(credits), "prereqs": list(prereqs)}
            trial = [new if c["code"] == code else c for c in courses] if is_edit else courses + [new]
            if not errors:
                cyc = find_cycle_path(build_graph(trial))
                if cyc:
                    errors.append("Saving would create a circular prerequisite dependency: " + " → ".join(cyc) + ".")
            if errors:
                for e in errors:
                    st.error(f"⚠️ {e}")
            else:
                store_courses(trial)
                st.session_state["cm_form"] = None
                set_flash("success", f"Course '{code}' successfully {'updated' if is_edit else 'added'}.")
                st.rerun()


def page_courses():
    show_flash()
    courses = get_courses()
    page_header("Curriculum Management", "Course Catalogue",
                "Create, update, and organize courses and prerequisite relationships.")

    # Top action bar
    t1, t2, t3 = st.columns([3, 1.2, 1.4])
    search = t1.text_input("Search courses", placeholder="🔍 Search courses by code or name...", label_visibility="collapsed")
    t2.button("➕ Add Course", type="primary", use_container_width=True, on_click=open_form, args=(NEW,))
    t3.button("↺ Restore Samples", use_container_width=True, on_click=request_reset)

    if st.session_state["cm_form"] is not None:
        course_form(st.session_state["cm_form"])

    pending = st.session_state["pending"]
    if pending:
        kind, val = pending
        with st.container(border=True):
            if kind == "delete":
                deps = [c["code"] for c in courses if val in c["prereqs"]]
                msg = f"Are you sure you want to delete course **{val}**? This action cannot be undone."
                if deps:
                    msg += f"\n\n*Note: {val} is a prerequisite of {', '.join(deps)}. It will be automatically removed from their prerequisites.*"
            else:
                msg = "Replace all current courses with the built-in sample curriculum? Any custom edits and completion states will be reset."
            st.warning(msg)
            c1, c2, _ = st.columns([1.2, 1, 4])
            if c1.button("Yes, Confirm", type="primary", key="pending_ok"):
                if kind == "delete":
                    store_courses([dict(c, prereqs=[p for p in c["prereqs"] if p != val])
                                   for c in courses if c["code"] != val])
                    st.session_state["completed"].discard(val)
                    if st.session_state["cm_form"] == val:
                        st.session_state["cm_form"] = None
                    set_flash("success", f"Course '{val}' deleted.")
                else:
                    store_courses(copy.deepcopy(SAMPLE_COURSES))
                    st.session_state["completed"] = set()
                    st.session_state["cm_form"] = None
                    set_flash("success", "Built-in sample curriculum restored.")
                st.session_state["pending"] = None
                st.rerun()
            if c2.button("Cancel", key="pending_cancel"):
                st.session_state["pending"] = None
                st.rerun()

    if not courses:
        empty_state("No courses defined", "Click “Add Course” above to create your first course, or restore sample data.")
    else:
        q = search.strip().upper()
        shown = [c for c in courses if q in c["code"].upper() or q in c["name"].upper()] if q else courses
        if shown:
            with st.container(border=True):
                rows = [{"Code": c["code"], "Course Name": c["name"], "Credits": c["credits"],
                         "Prerequisites": ", ".join(c["prereqs"]) if c["prereqs"] else "— (Foundational)"} for c in shown]
                st.dataframe(rows, hide_index=True, use_container_width=True, height=min(40 + 38 * len(rows), 420))
                st.caption(f"Showing {len(shown)} of {len(courses)} courses · {sum(c['credits'] for c in shown)} total credits")

            with st.container(border=True):
                st.markdown("#### Manage Existing Course")
                a1, a2, a3 = st.columns([3, 1, 1])
                sel = a1.selectbox("Select course", [c["code"] for c in courses],
                                   format_func=lambda x: f"{x} — {next(c['name'] for c in courses if c['code'] == x)}",
                                   label_visibility="collapsed")
                a2.button("✏️ Edit", use_container_width=True, on_click=open_form, args=(sel,))
                if a3.button("🗑️ Delete", use_container_width=True):
                    st.session_state["pending"] = ("delete", sel)
                    st.rerun()
        else:
            st.info("No courses match your search criteria.")


# ════════════════════════════════════════════════════════════
#  Eligibility Checker
# ════════════════════════════════════════════════════════════
def page_eligibility():
    show_flash()
    courses = get_courses()
    page_header("Prerequisite Verification", "Eligibility Checker",
                "A course is eligible when every prerequisite is met. Check off what you have finished to view real-time eligibility.")
    if not courses:
        empty_state("No courses defined", "Add courses in Course Management first.")
        return

    codes = [c["code"] for c in courses]
    names = {c["code"]: c["name"] for c in courses}
    current_completed = sorted(get_completed())
    if "completed_widget" not in st.session_state or set(st.session_state["completed_widget"]) != set(current_completed):
        st.session_state["completed_widget"] = current_completed

    def sync():
        st.session_state["completed"] = set(st.session_state["completed_widget"])

    def clear():
        st.session_state["completed_widget"] = []
        st.session_state["completed"] = set()

    with st.container(border=True):
        st.markdown("### 🎓 Record Completed Courses")
        st.caption("Select courses you have already passed. Dependent courses will automatically become eligible.")
        st.multiselect("Completed courses selector", codes, key="completed_widget", on_change=sync,
                       format_func=lambda x: f"{x} — {names[x]}", label_visibility="collapsed",
                       placeholder="Select courses you have completed...")
        st.button("Clear all selections", on_click=clear)

    completed = get_completed()
    elig = get_eligible_courses(courses, completed)
    elig_codes = {c["code"] for c in elig}
    done = [c for c in courses if c["code"] in completed]
    blocked = [c for c in courses if c["code"] not in completed and c["code"] not in elig_codes]

    if detect_cycle(build_graph(courses)):
        st.error("⚠️ The prerequisite graph contains a circular cycle. Courses in the cycle can never become eligible.")

    col_done, col_elig, col_block = st.columns(3, gap="large")
    with col_done:
        st.markdown(f'<div class="cl-colhead">{badge("completed")}<span class="cl-count">{len(done)} courses</span></div>',
                    unsafe_allow_html=True)
        if done:
            st.markdown("".join(course_card(c["code"], c["name"], f"{c['credits']} credits · Completed") for c in done),
                        unsafe_allow_html=True)
        else:
            st.caption("No courses marked as completed yet.")

    with col_elig:
        st.markdown(f'<div class="cl-colhead">{badge("eligible", "Eligible now")}<span class="cl-count">{len(elig)} courses</span></div>',
                    unsafe_allow_html=True)
        if elig:
            cards = []
            for c in elig:
                why = "Foundational (No prerequisites)" if not c["prereqs"] else "Prerequisites satisfied: " + ", ".join(c["prereqs"])
                cards.append(course_card(c["code"], c["name"], f"{c['credits']} credits · {why}"))
            st.markdown("".join(cards), unsafe_allow_html=True)
        else:
            st.caption("No courses are eligible right now.")

    with col_block:
        st.markdown(f'<div class="cl-colhead">{badge("blocked", "Blocked")}<span class="cl-count">{len(blocked)} courses</span></div>',
                    unsafe_allow_html=True)
        if blocked:
            cards = []
            for c in blocked:
                missing = get_missing_prereqs(c, completed)
                cards.append(course_card(c["code"], c["name"],
                                         f"{c['credits']} credits · Missing: " + ", ".join(missing)))
            st.markdown("".join(cards), unsafe_allow_html=True)
        else:
            st.caption("No courses are blocked!")


# ════════════════════════════════════════════════════════════
#  Dependency Graph
# ════════════════════════════════════════════════════════════
def page_graph():
    show_flash()
    courses, completed = get_courses(), get_completed()
    page_header("Graph Visualisation", "Prerequisite Dependency Graph",
                "Visualize academic progression. Directed arrows flow from prerequisites to their dependent courses.")
    if not courses:
        empty_state("No courses defined", "Add courses in Course Management first.")
        return

    codes = {c["code"] for c in courses}
    unknown = sorted({p for c in courses for p in c["prereqs"] if p not in codes})
    if unknown:
        st.warning("⚠️ Ignored prerequisite references not found in catalogue: " + ", ".join(unknown))

    G = build_graph(courses)
    cyc = find_cycle_path(G)
    if cyc:
        st.error("⚠️ **Circular prerequisite detected:** " + " → ".join(cyc) +
                 ". A valid dependency graph cannot be rendered until this cycle is broken.")
        return

    with st.container(border=True):
        g1, g2 = st.columns([1.5, 3])
        view = g1.radio("Diagram Mode", ["Prerequisite Graph (All Edges)", "Hasse Diagram (Transitive Reduction)"],
                        horizontal=True, key="graph_view")
        hasse = "Hasse" in view
        if hasse:
            g2.caption("The Hasse diagram removes redundant transitive edges (e.g. if A → B and B → C, the direct arrow A → C is omitted).")
        else:
            g2.caption("Courses are layered left-to-right according to the length of their longest prerequisite chain.")

        draw_graph(G, completed, get_eligible_courses(courses, completed), hasse=hasse)
        legend(GRAPH_LEGEND)

        if hasse:
            hidden = redundant_edges(G, hasse_graph(G))
            if hidden:
                st.info("💡 **Redundant transitive edges omitted in Hasse view:** " + ", ".join(f"`{u} → {v}`" for u, v in hidden))
            else:
                st.caption("No redundant edges detected: this prerequisite graph is already its own minimal Hasse diagram.")

    with st.expander("📋 View Complete Course Status Key"):
        eligible = get_eligible_courses(courses, completed)
        elig_codes = {c["code"] for c in eligible}
        st.dataframe(
            [{"Code": c["code"], "Course Name": c["name"], "Credits": c["credits"],
              "Status": "Completed" if c["code"] in completed else ("Eligible" if c["code"] in elig_codes else "Blocked")}
             for c in courses],
            hide_index=True, use_container_width=True)


# ════════════════════════════════════════════════════════════
#  Semester Planner
# ════════════════════════════════════════════════════════════
def _plan_signature(courses, completed, mc, sems, inc_comp=False):
    return json.dumps([courses, sorted(completed) if not inc_comp else [], mc, sems, inc_comp], sort_keys=True)


def render_plan(stored, courses):
    result, mc = stored["result"], stored["mc"]
    by_code = {c["code"]: c for c in courses}
    status, plan = result["status"], result["plan"]

    if status == "infeasible":
        st.error(f"❌ **Infeasible Plan:** {result['message']}")
        return
    scheduled = sum(len(s) for s in plan)
    used_sems = sum(1 for s in plan if s)
    if status == "complete":
        st.success(f"✓ **Complete Plan Generated:** All {scheduled} courses scheduled across {used_sems} of {len(plan)} semesters without exceeding {mc} credits per semester.")
    else:
        st.warning(f"⚠️ **Partial Plan:** {scheduled} courses placed; {len(result['unscheduled'])} course(s) could not be scheduled within {len(plan)} semesters.")

    with st.expander("ℹ️ Planning Heuristic Assumptions & Guarantees"):
        st.markdown(
            """
- **Topological Strictness**: Prerequisites are guaranteed to appear strictly in earlier semesters than dependent courses.
- **Credit Limit Hard Boundary**: No semester's total credit sum exceeds the configured maximum.
- **Greedy Approximation**: The planner schedules courses in priority topological order into the earliest feasible semester. While optimal for most standard degree programs, it is an approximation heuristic and not a proven minimum-semester solver.
            """
        )

    for i, sem in enumerate(plan, 1):
        sem_courses = [by_code[c] for c in sem]
        used = sum(c["credits"] for c in sem_courses)
        with st.container(border=True):
            st.markdown(
                f'<div class="cl-sem-head"><span class="cl-sem-title">Semester {i}</span>'
                f'<span class="cl-sem-credits"><strong>{used}</strong> / {mc} credits ({mc - used} available)</span></div>'
                + util_bar(used, mc),
                unsafe_allow_html=True)
            if sem_courses:
                rows = [[f"<strong>{esc(c['code'])}</strong>", esc(c["name"]), str(c["credits"]),
                         esc(", ".join(c["prereqs"]) if c["prereqs"] else "None (Foundational)")] for c in sem_courses]
                st.markdown(html_table(["Code", "Course Name", "Credits", "Prerequisites"], rows,
                                       ["left", "left", "center", "left"],
                                       footer=["", "Total Semester Credits", str(used), ""]), unsafe_allow_html=True)
            else:
                st.caption("No courses scheduled in this semester.")

    if result["unscheduled"]:
        section_title("Unscheduled Courses Breakdown", "Detailed constraint analysis for courses that could not be placed.")
        rows = [[f"<strong>{esc(code)}</strong>", esc(by_code[code]["name"]), esc(reason)]
                for code, reason in result["unscheduled"].items()]
        st.markdown(html_table(["Code", "Course Name", "Constraint Reason"], rows), unsafe_allow_html=True)


def page_planner():
    show_flash()
    courses, completed = get_courses(), get_completed()
    page_header("Degree Scheduling", "Semester Planner",
                "Generate an optimal semester-by-semester study schedule respecting prerequisite chains and maximum credit limits.")
    if not courses:
        empty_state("No courses defined", "Add courses in Course Management first.")
        return

    with st.container(border=True):
        st.markdown("### ⚙️ Plan Parameters")
        c1, c2, c3 = st.columns([1.5, 1.5, 2])
        mc = int(c1.number_input("Max Credits Per Semester", min_value=1, max_value=30, value=12, key="plan_max"))
        sems = int(c2.number_input("Number of Semesters", min_value=1, max_value=12, value=4, key="plan_sems"))
        inc_comp = c3.checkbox("Include Completed Courses", value=False,
                               help="Check this to plan the degree from semester 1, ignoring current completed checkboxes.")

        remaining = courses if inc_comp else [c for c in courses if c["code"] not in completed]
        if not remaining:
            st.success("Every course is already completed! Enable 'Include Completed Courses' above to plan the entire degree curriculum.")
            return

        rem_credits = sum(c["credits"] for c in remaining)
        chk = credit_capacity_check(rem_credits, mc, sems)
        st.caption(f"{len(remaining)} courses to schedule · {rem_credits} total credits · Maximum total capacity: {mc} × {sems} = {chk['capacity']} credits")
        if not chk["feasible"]:
            st.warning(f"⚠️ **Pigeonhole Principle Warning:** Spreading {rem_credits} credits across {sems} semesters requires at least ⌈{rem_credits}/{sems}⌉ = {chk['min_load']} credits in some semester, exceeding the limit of {mc}. A complete plan is mathematically impossible under these constraints.")
        generate = st.button("Generate Semester Plan", type="primary")

    sig = _plan_signature(courses, completed, mc, sems, inc_comp)
    if generate:
        st.session_state["plan"] = {
            "sig": sig, "mc": mc, "sems": sems,
            "result": plan_semesters_detailed(courses, completed, mc, sems, include_completed=inc_comp),
        }
    stored = st.session_state.get("plan")
    if stored and stored["sig"] == sig:
        render_plan(stored, courses)
    elif stored:
        st.info("Configuration parameters or course catalog changed. Click 'Generate Semester Plan' to refresh.")
    else:
        empty_state("No Plan Generated", "Configure semester parameters above and click “Generate Semester Plan”.")


# ════════════════════════════════════════════════════════════
#  Mathematics Lab
# ════════════════════════════════════════════════════════════
def page_math():
    show_flash()
    courses, completed = get_courses(), get_completed()
    page_header("Theoretical Foundations", "Mathematics Lab",
                "Explore the discrete mathematics concepts powering CurricuLogic with live interactive calculators and current course data.")
    tabs = st.tabs(["1. Propositional Logic", "2. Binary Relations", "3. Partial Orders & Hasse", "4. Topological Sorting", "5. Pigeonhole Principle", "6. Combinatorics"])
    G = build_graph(courses)
    cyc = find_cycle_path(G)

    with tabs[0]:
        st.markdown("### Propositional Logic & Conjunctions")
        st.markdown("Course eligibility is formally evaluated as the **conjunction** of propositions representing prerequisite completions. Let $\mathrm{done}(p)$ be a Boolean proposition. A course $c$ is eligible if and only if:")
        st.latex(r"\mathrm{eligible}(c) \iff \bigwedge_{p \in \mathrm{prereq}(c)} \mathrm{done}(p)")
        with_pre = [c for c in courses if c["prereqs"]]
        if with_pre:
            sel = st.selectbox("Worked Example: Select Course", [c["code"] for c in with_pre],
                               format_func=lambda x: f"{x} — {next(c['name'] for c in with_pre if c['code'] == x)}")
            variables = next(c for c in with_pre if c["code"] == sel)["prereqs"]
        else:
            sel, variables = "EXAMPLE", ["PRE_A", "PRE_B"]
        if len(variables) <= 5:
            st.caption(f"Truth table for course **{sel}**. Only the assignment where all prerequisites evaluate to 1 yields eligibility.")
            st.dataframe(truth_table(variables), hide_index=True, use_container_width=True)
        else:
            st.caption("Truth table exceeds 32 rows (more than 5 prerequisites).")

    with tabs[1]:
        st.markdown("### Binary Relations on Course Sets")
        st.markdown("The prerequisite relationship is a binary relation $R \subseteq C \times C$ over the course set $C$. The ordered pair $(p, c) \in R$ signifies that $p$ is an immediate prerequisite of $c$:")
        st.latex(r"R = \{(p, c) \in C \times C : p \text{ is an immediate prerequisite of } c\}")
        pairs = list(G.edges())
        if pairs:
            shown = ", ".join(f"({u}, {v})" for u, v in pairs[:8]) + (", …" if len(pairs) > 8 else "")
            st.code(f"R = {{{shown}}}   # {len(pairs)} prerequisite pairs in active curriculum", language=None)
        else:
            st.caption("No prerequisite pairs in current course data.")

    with tabs[2]:
        st.markdown("### Partial Orders & Transitive Reductions (Hasse Diagrams)")
        st.markdown("A curriculum is a **Partially Ordered Set (Poset)** $(C, \le)$ where $a \le b$ denotes a chain of prerequisites. When acyclic, the relation is reflexive, anti-symmetric, and transitive.")
        st.latex(r"b \text{ covers } a \iff a < b \text{ and } \nexists c \in C \text{ s.t. } a < c < b")
        if cyc:
            st.warning("Current curriculum contains a cycle (" + " → ".join(cyc) + "), violating anti-symmetry.")
        else:
            H = hasse_graph(G)
            hidden = redundant_edges(G, H)
            st.markdown(f"- Full prerequisite graph edges: **{G.number_of_edges()}**\n- Transitive reduction (Hasse diagram) edges: **{H.number_of_edges()}**")
            if hidden:
                st.info("Redundant edges eliminated in Hasse reduction: " + ", ".join(f"`{u} → {v}`" for u, v in hidden))

    with tabs[3]:
        st.markdown("### Topological Sorting on Directed Acyclic Graphs")
        st.markdown("A topological sort produces a linear ordering of vertices such that for every directed edge $(u, v)$, vertex $u$ comes before $v$:")
        st.latex(r"\forall (u, v) \in E,\quad \mathrm{position}(u) < \mathrm{position}(v)")
        if cyc:
            st.error("No topological ordering exists due to circular prerequisite cycle: " + " → ".join(cyc))
        elif courses:
            st.code(" → ".join(topological_sort(courses)), language=None)
            st.caption("One valid linear topological progression for your current curriculum.")

    with tabs[4]:
        st.markdown("### Generalized Pigeonhole Principle")
        st.markdown("If $R$ total credits must be partitioned across $s$ semesters, at least one semester must carry at least $\lceil R / s \rceil$ credits. If $\lceil R / s \rceil > k$, no valid schedule exists:")
        st.latex(r"\left\lceil \frac{R}{s} \right\rceil > k \implies \text{No feasible semester plan}")
        rem = sum(c["credits"] for c in courses if c["code"] not in completed)
        p1, p2, p3 = st.columns(3)
        r_val = int(p1.number_input("Credits to schedule (R)", min_value=0, value=rem, key="ph_r"))
        k_val = int(p2.number_input("Max credits/semester (k)", min_value=1, value=12, key="ph_k"))
        s_val = int(p3.number_input("Number of semesters (s)", min_value=1, value=4, key="ph_s"))
        chk = credit_capacity_check(r_val, k_val, s_val)
        msg = f"⌈{r_val} / {s_val}⌉ = {chk['min_load']} credits vs limit k = {k_val}"
        (st.success if chk["feasible"] else st.error)(
            msg + (" → Feasibility check passed." if chk["feasible"] else " → Impossible schedule (exceeds limit)."))

    with tabs[5]:
        st.markdown("### Permutations and Combinations")
        st.markdown("When selecting $k$ elective courses from $n$ available offerings without regard to order, we compute combinations $C(n, k)$:")
        st.latex(r"C(n,k) = \binom{n}{k} = \frac{n!}{k!(n-k)!} \qquad P(n,k) = \frac{n!}{(n-k)!}")
        eligible_n = len(get_eligible_courses(courses, completed))
        st.markdown("**Benchmark Calculation**: Choosing 3 electives from 5 available options yields:")
        c_calc1, c_calc2 = st.columns(2)
        n = int(c_calc1.number_input("Available Electives (n)", min_value=0, value=max(eligible_n, 5), key="cnt_n"))
        k = int(c_calc2.number_input("Electives to Choose (k)", min_value=0, value=min(3, max(eligible_n, 5)), key="cnt_k"))
        st.success(f"**C({n}, {k}) = {combinations(n, k):,} combinations**  |  **P({n}, {k}) = {permutations(n, k):,} permutations**")
        if k > n:
            st.caption("k > n: 0 valid selections possible.")


# ════════════════════════════════════════════════════════════
#  About
# ════════════════════════════════════════════════════════════
def page_about():
    page_header("Academic Project", "About CurricuLogic",
                "Smart Course Prerequisite Planner developed for BAMAT205: Discrete Mathematics and Linear Algebra.")
    left, right = st.columns([1.6, 1.4], gap="large")
    with left:
        st.markdown(
            """
<div class="cl-prose">

### Executive Overview
CurricuLogic models academic degree curricula as discrete mathematical structures. It solves the common dilemma where students discover unmet prerequisites too late or face impossible credit bottlenecks during degree completion.

### Core Objectives
1. **Mathematical Rigor**: Represent prerequisite structures as directed acyclic graphs (DAGs) and Hasse diagrams.
2. **Deterministic Eligibility**: Evaluate course enrollment readiness using propositional logic conjunctions.
3. **Cycle Elimination**: Detect and report circular dependencies before scheduling.
4. **Credit-Constrained Scheduling**: Generate realistic semester-by-semester roadmaps respecting credit caps and prerequisite ordering.
5. **Interactive Pedagogy**: Connect theory with practical degree management.

### Architectural Scope & Persistence
- Data is maintained in local JSON persistence and verified on each reload.
- The semester planner implements a greedy topological priority heuristic.
- Clean client-side rendering with no external tracking or telemetry.

</div>
""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
<div class="cl-prose">

### Theoretical Foundations
- **Propositional Logic**: Conjunction of completed prerequisite conditions.
- **Set Theory & Relations**: Binary relations, transitivity, and partial orderings.
- **Graph Theory**: DAGs, topological sorting, and transitive reduction algorithms.
- **Combinatorics**: Pigeonhole principle bounds and elective combinations.

### Technology Stack
- **Framework**: Streamlit & Python 3.11+
- **Graph Mathematics**: NetworkX
- **Diagram Generation**: Matplotlib with clean vector graphics
- **Quality Assurance**: pytest automated verification suite

### Academic Course
**BAMAT205**: Discrete Mathematics and Linear Algebra  
*Undergraduate Academic Project*

</div>
""",
            unsafe_allow_html=True,
        )


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