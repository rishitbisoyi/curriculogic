# CurricuLogic — Smart Course Prerequisite Planner

> **Plan smarter. Understand the mathematics.**

A polished academic dashboard for visualizing course prerequisites, checking eligibility, planning semesters, and exploring the discrete-mathematics concepts behind it all.

Built for **BAMAT205 — Discrete Mathematics and Linear Algebra**.

---

## Quick Start (React 19 + TypeScript + FastAPI)

### 1. Install Dependencies

```bash
# Install backend Python dependencies
pip install -r requirements.txt

# Install frontend Node dependencies
cd frontend && npm install && cd ..
```

### 2. Run the Application

#### Option A: Development Mode (Hot Reloading)

Run backend and frontend concurrently:

```bash
# Terminal 1: FastAPI Backend
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: React Frontend (Vite)
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

- **Frontend App**: [http://localhost:5173](http://localhost:5173)
- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Option B: Production Single-Server Mode

Build the frontend bundle and serve everything directly from FastAPI:

```bash
cd frontend && npm run build && cd ..
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

---

## Access from Another Device on the Same Network

1. Find your machine's private IPv4 address (`hostname -I` or `ip addr show`).
2. Start the Vite server with `--host 0.0.0.0`.
3. Open `http://<YOUR_IP>:5173` from any phone, tablet, or laptop on the same Wi-Fi network.

---

## Project Structure

```
curriculogic/
├── server.py                # FastAPI REST backend & static SPA host
├── graph_engine.py          # NetworkX DAG building, Hasse reduction, cycle detection
├── planner.py               # Greedy credit-constrained semester planner with topological sort
├── logic.py                 # Propositional logic & dashboard metrics calculation
├── counting.py              # Combinations, permutations, & pigeonhole feasibility checks
├── sample_data.py           # Sample course data & JSON persistence
├── courses.json             # Persistent course storage
├── requirements.txt         # Python backend dependencies
├── frontend/                # Modern React 19 + TypeScript + Vite web app
│   ├── src/
│   │   ├── App.tsx          # Main application router and state
│   │   ├── components/      # UI components (Graph, Modal, Matrix, Math Labs)
│   │   ├── types.ts         # TypeScript data definitions
│   │   └── index.css        # Premium design system stylesheet
│   ├── package.json
│   └── vite.config.ts
└── tests/                   # Automated pytest suite
    ├── test_counting.py
    ├── test_curriculogic.py
    ├── test_graph_engine.py
    ├── test_logic.py
    ├── test_planner.py
    └── test_sample_data.py
```

## Running Tests

Run the full automated test suite directly using `pytest`:

```bash
pytest -v
```

---

## Mathematical Concepts

1. **Propositional Logic** — AND-conjunction of prerequisites determines eligibility ($\bigwedge_{p \in \mathrm{prereqs}(c)} \mathrm{done}(p)$).
2. **Relations & Partial Orders** — Posets $(C, \le)$, Hasse diagrams (transitive reduction), and topological sorting for prerequisite DAGs.
3. **Counting & Pigeonhole Principle** — Combinatorics calculation ($C(n, k)$, $P(n, k)$) and credit feasibility bounds ($\lceil R / s \rceil \le k$).

---

## Technologies

| Component | Technology |
|---|---|
| Frontend | React 19, TypeScript, Lucide Icons, Canvas-Confetti, Vite |
| Backend API | FastAPI, Uvicorn, Pydantic |
| Graph Engine | NetworkX |
| Testing | pytest |

---

*Developed by the BAMAT205 student team.*
