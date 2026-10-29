"""CurricuLogic FastAPI Backend API

Directly exposes all core mathematical models, graph algorithms,
semester planning, counting formulas, and course persistence to the modern frontend.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Set, Dict, Optional
import copy
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from logic import get_metrics, truth_table
from graph_engine import (
    build_graph, detect_cycle, find_cycle_path, get_eligible_courses,
    get_missing_prereqs, hasse_graph, redundant_edges, layered_positions
)
from planner import plan_semesters_detailed, topological_sort
from counting import combinations, permutations, credit_capacity_check
from sample_data import SAMPLE_COURSES, load_sample_courses, save_courses

app = FastAPI(title="CurricuLogic Core API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CourseModel(BaseModel):
    code: str
    name: str
    credits: int
    prereqs: List[str] = []

class PlanRequest(BaseModel):
    max_credits: int
    semesters: int
    completed: List[str] = []
    include_completed: bool = False

class TruthTableRequest(BaseModel):
    variables: List[str]

class CapacityCheckRequest(BaseModel):
    required_credits: int
    max_credits: int
    semesters: int

class CombinatoricsRequest(BaseModel):
    n: int
    k: int


@app.get("/api/courses", response_model=List[CourseModel])
def get_all_courses():
    return load_sample_courses()

@app.post("/api/courses", response_model=List[CourseModel])
def save_all_courses(courses: List[CourseModel]):
    data = [c.model_dump() for c in courses]
    save_courses(data)
    return data

@app.post("/api/courses/reset", response_model=List[CourseModel])
def reset_to_sample_courses():
    courses = copy.deepcopy(SAMPLE_COURSES)
    save_courses(courses)
    return courses

@app.post("/api/metrics")
def calculate_metrics(completed: List[str]):
    courses = load_sample_courses()
    completed_set = set(completed)
    total, done, elig_cnt, remaining_credits = get_metrics(courses, completed_set)
    total_cr = sum(c["credits"] for c in courses)
    return {
        "total": total,
        "completed": done,
        "eligible": elig_cnt,
        "blocked": total - done - elig_cnt,
        "total_credits": total_cr,
        "completed_credits": total_cr - remaining_credits,
        "remaining_credits": remaining_credits,
    }

@app.post("/api/eligibility")
def check_eligibility(completed: List[str]):
    courses = load_sample_courses()
    completed_set = set(completed)
    eligible = get_eligible_courses(courses, completed_set)
    elig_codes = {c["code"] for c in eligible}
    
    done = [c for c in courses if c["code"] in completed_set]
    blocked = [c for c in courses if c["code"] not in completed_set and c["code"] not in elig_codes]
    
    blocked_details = []
    for c in blocked:
        missing = get_missing_prereqs(c, completed_set)
        blocked_details.append({
            **c,
            "missing_prereqs": missing,
        })
        
    G = build_graph(courses)
    has_cycle = detect_cycle(G)
    cycle_path = find_cycle_path(G)
    
    return {
        "completed": done,
        "eligible": eligible,
        "blocked": blocked_details,
        "has_cycle": has_cycle,
        "cycle_path": cycle_path,
    }

@app.get("/api/graph")
def get_graph_data():
    courses = load_sample_courses()
    G = build_graph(courses)
    has_cycle = detect_cycle(G)
    cycle_path = find_cycle_path(G)
    
    nodes = []
    for c in courses:
        nodes.append({
            "id": c["code"],
            "code": c["code"],
            "name": c["name"],
            "credits": c["credits"],
            "prereqs": c["prereqs"],
        })
        
    edges = [{"source": u, "target": v} for u, v in G.edges()]
    
    positions = {}
    if not has_cycle:
        pos = layered_positions(G)
        positions = {k: {"x": float(v[0]), "y": float(v[1])} for k, v in pos.items()}
        
        H = hasse_graph(G)
        hasse_edges = [{"source": u, "target": v} for u, v in H.edges()]
        redundant = [{"source": u, "target": v} for u, v in redundant_edges(G, H)]
    else:
        hasse_edges = []
        redundant = []
        
    return {
        "nodes": nodes,
        "edges": edges,
        "hasse_edges": hasse_edges,
        "redundant_edges": redundant,
        "positions": positions,
        "has_cycle": has_cycle,
        "cycle_path": cycle_path,
    }

@app.post("/api/plan")
def generate_semester_plan(req: PlanRequest):
    courses = load_sample_courses()
    res = plan_semesters_detailed(
        courses,
        set(req.completed),
        req.max_credits,
        req.semesters,
        include_completed=req.include_completed,
    )
    return res

@app.post("/api/math/truth-table")
def get_truth_table(req: TruthTableRequest):
    if len(req.variables) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 variables allowed")
    return truth_table(req.variables)

@app.post("/api/math/capacity-check")
def check_credit_capacity(req: CapacityCheckRequest):
    try:
        return credit_capacity_check(req.required_credits, req.max_credits, req.semesters)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/math/combinatorics")
def calculate_combinatorics(req: CombinatoricsRequest):
    try:
        c_val = combinations(req.n, req.k)
        p_val = permutations(req.n, req.k)
        return {
            "n": req.n,
            "k": req.k,
            "combinations": c_val,
            "permutations": p_val,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/docs/pdf")
def download_documentation_pdf():
    pdf_path = os.path.join(os.path.dirname(__file__), "CurricuLogic_Academic_Documentation.pdf")
    if not os.path.exists(pdf_path):
        from generate_docs_pdf import build_pdf
        build_pdf(pdf_path)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="CurricuLogic_Academic_Documentation.pdf"
    )

# Serve modern frontend static assets and SPA fallback
dist_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(dist_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
