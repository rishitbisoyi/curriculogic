# CurricuLogic — Smart Course Prerequisite Planner

> **Plan smarter. Understand the mathematics.**

A polished academic dashboard for visualizing course prerequisites, checking eligibility,
planning semesters, and exploring the discrete-mathematics concepts behind it all.

Built for **BAMAT205 — Discrete Mathematics and Linear Algebra**.

---

## Quick Start

### Prerequisites

- **Python 3.10+** (tested with 3.11 / 3.13)
- pip

### Install dependencies

```bash
cd curriculogic
pip install -r requirements.txt
```

### Run locally

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Access from Another Device on the Same Network

### 1. Start with network access

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

### 2. Find your laptop's private IPv4 address

**Linux / macOS:**

```bash
ip addr show | grep "inet "
# or
hostname -I
```

**Windows (PowerShell):**

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Select IPAddress
```

Look for the address on your Wi-Fi/Ethernet interface (e.g. `192.168.1.42`).

### 3. Open from the other device

On a phone, tablet, or another laptop connected to the **same Wi-Fi network**, open:

```
http://<YOUR_LAPTOP_IP>:8501
```

Replace `<YOUR_LAPTOP_IP>` with the address from step 2.

### 4. Troubleshooting

| Issue | Fix |
|-------|-----|
| **Firewall blocks port 8501** | Allow inbound TCP on port 8501 (`sudo ufw allow 8501` on Ubuntu, or add a Windows Firewall rule). |
| **"Connection refused" on the other device** | Verify both devices are on the same network and that you used `--server.address 0.0.0.0`. |
| **AP Isolation / Client Isolation** | Some routers block device-to-device traffic. Check your router settings or try a different network. |
| **Port already in use** | Change the port: `--server.port 8502` |

### 5. Stop the server

Press **Ctrl + C** in the terminal where Streamlit is running.

---

## Deployment on Streamlit Community Cloud (Free)

### Preparation checklist

- [x] `requirements.txt` lists all dependencies.
- [x] No absolute file paths — all paths are relative to the project root.
- [x] Sample data is embedded in `sample_data.py`; no external files required.
- [x] No API keys, tokens, or passwords in the codebase.
- [x] `.streamlit/config.toml` sets `headless = true`.

### Steps

1. Push this repository to **GitHub** (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **"New app"** and select your repository.
4. Set the **main file path** to: `curriculogic/app.py`
   *(adjust if your repo root differs)*
5. Click **Deploy**.

Your app will be available at a public HTTPS URL like:
`https://<your-app-name>.streamlit.app`

### Limitations of Streamlit Community Cloud

- **No persistent storage**: `courses.json` is written to the container filesystem and will be reset on each reboot. Session state persists only for the duration of a browser session.
- **Resource limits**: Free tier has limited CPU/RAM; sufficient for this app.
- **Sleep after inactivity**: The app may sleep after ~7 days of no traffic and will wake on next visit.

---

## Project Structure

```
curriculogic/
├── .streamlit/
│   └── config.toml          # Streamlit theme & server config
├── app.py                    # Main Streamlit application (entry point)
├── logic.py                  # Dashboard metrics calculation
├── graph_engine.py           # NetworkX graph building, cycle detection, drawing
├── planner.py                # Greedy semester planner with topological sort
├── counting.py               # Pigeonhole feasibility & combinations
├── sample_data.py            # Sample course data & JSON persistence
├── style.css                 # Custom CSS for modern UI
├── requirements.txt          # Python dependencies
├── __init__.py               # Package init
└── tests/
    ├── __init__.py
    └── test_logic.py         # Unit tests
```

## Running Tests

```bash
cd /path/to/maths
python -m pytest curriculogic/tests/ -v
```

---

## Mathematical Concepts

1. **Propositional Logic** — AND-conjunction of prerequisites determines eligibility.
2. **Counting** — Pigeonhole principle for feasibility checks; combinations calculator.
3. **Relations & Partial Orders** — Topological sorting of the prerequisite DAG; Hasse-diagram-style visualization.

---

## Technologies

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Web Framework | Streamlit |
| Graph Algorithms | NetworkX |
| Visualization | Matplotlib |
| Testing | pytest |

---

*Developed by the BAMAT205 student team.*
