print("Starting server.py in root...")
import os
import sys
import time
import json
import glob
import threading
from contextlib import asynccontextmanager
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import hashlib
from dotenv import load_dotenv

# Use current directory as project root since simpler structure requested
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR

# Add lang-graph-experiment to sys.path to allow importing agents
sys.path.insert(0, os.path.join(PROJECT_ROOT, "lang-graph-experiment"))

load_dotenv()

DEMO_USER = "admin"
DEMO_PASS = "12345678"
DEMO_TOKEN = hashlib.sha256(f"{DEMO_USER}:{DEMO_PASS}".encode()).hexdigest()[:32]

OUTPUTS_DIR = os.path.join(SCRIPT_DIR, "lang-graph-experiment", "outputs")
OUTPUTS_JSON_DIR = os.path.join(OUTPUTS_DIR, "json")
SUBSET_PATH = os.path.join(SCRIPT_DIR, "lang-graph-experiment", "analysis_subset.csv")
SOURCE_CSV = os.path.join(PROJECT_ROOT, "Commuter Users Event data.csv")

PIPELINE_DIR = os.path.join(PROJECT_ROOT, "pipeline_deduplication")
CLEANED_EVENTS_FILE = os.path.join(PIPELINE_DIR, "cleaned_events.csv")
REPETITION_SUMMARY_FILE = os.path.join(PIPELINE_DIR, "repetition_summary.csv")
UNIQUE_USERS_FILE = os.path.join(PIPELINE_DIR, "unique_users_list.csv")

_pipeline_state = {
    "status": "idle",
    "started_at": None,
    "completed_at": None,
    "elapsed_sec": None,
    "metrics_completed": [],
    "errors": [],
    "report_path": None,
}
_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    yield


app = FastAPI(
    title="LangGraph Analytics API",
    description="Multi-agent analytics pipeline for commuter user event data",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login")
async def login(req: LoginRequest):
    if req.username == DEMO_USER and req.password == DEMO_PASS:
        return JSONResponse({"success": True, "token": DEMO_TOKEN})
    return JSONResponse({"success": False, "error": "Invalid credentials"}, status_code=401)


class PipelineResponse(BaseModel):
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    elapsed_sec: Optional[float] = None
    metrics_completed: list = []
    errors: list = []
    report_path: Optional[str] = None


def _run_pipeline():
    with _lock:
        _pipeline_state["status"] = "running"
        _pipeline_state["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _pipeline_state["completed_at"] = None
        _pipeline_state["metrics_completed"] = []
        _pipeline_state["errors"] = []

    try:
        if not os.path.exists(SUBSET_PATH):
            from create_subset import create_subset
            create_subset()

        # Import from lang-graph-experiment/agents via sys.path
        from agents.graph import build_graph

        graph = build_graph()
        initial_state = {
            "dataset_path": SUBSET_PATH,
            "dataset_summary": {},
            "metric_results": {},
            "compiled_report": {},
            "errors": [],
        }

        start = time.time()
        result = graph.invoke(initial_state)
        elapsed = time.time() - start

        compiled = result.get("compiled_report", {})

        with _lock:
            _pipeline_state["status"] = "completed"
            _pipeline_state["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _pipeline_state["elapsed_sec"] = round(elapsed, 1)
            _pipeline_state["metrics_completed"] = compiled.get("metrics_completed", [])
            _pipeline_state["errors"] = compiled.get("metrics_failed", [])
            _pipeline_state["report_path"] = compiled.get("html_path")

    except Exception as e:
        with _lock:
            _pipeline_state["status"] = "failed"
            _pipeline_state["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _pipeline_state["errors"] = [str(e)]


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join(SCRIPT_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<html><body><p>index.html not found</p></body></html>")


@app.get("/dashboard.js", response_class=FileResponse)
async def dashboard_js():
    js_path = os.path.join(SCRIPT_DIR, "dashboard.js")
    if os.path.exists(js_path):
        return FileResponse(js_path)
    raise HTTPException(status_code=404, detail="dashboard.js not found")


@app.post("/api/run", response_model=PipelineResponse)
async def run_pipeline():
    with _lock:
        if _pipeline_state["status"] == "running":
            raise HTTPException(status_code=409, detail="Pipeline is already running")

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    return PipelineResponse(status="started", started_at=time.strftime("%Y-%m-%d %H:%M:%S"))


@app.get("/api/status", response_model=PipelineResponse)
async def pipeline_status():
    with _lock:
        return PipelineResponse(**_pipeline_state)


@app.get("/api/metrics")
async def list_metrics():
    with _lock:
        return JSONResponse({
            "available_metrics": [
                "funnel_analysis", "dropoff_analysis", "friction_points",
                "session_metrics", "retention_analysis", "user_segmentation",
                "conversion_rates", "time_to_action", "event_frequency", "temporal_patterns",
            ],
            "completed": _pipeline_state["metrics_completed"],
            "errors": _pipeline_state["errors"],
        })


@app.get("/api/report")
async def get_report():
    report = os.path.join(OUTPUTS_DIR, "analytics_report.html")
    if not os.path.exists(report):
        raise HTTPException(status_code=404, detail="Report not generated. POST /api/run first.")
    return FileResponse(report, media_type="text/html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "pipeline": _pipeline_state["status"]}


@app.get("/api/overview")
async def overview():
    result = {"total_users": 0, "total_events": 0, "pipeline_data_available": False, "langgraph_data_available": False}
    if os.path.exists(UNIQUE_USERS_FILE) and os.path.exists(CLEANED_EVENTS_FILE):
        try:
            users_df = pd.read_csv(UNIQUE_USERS_FILE)
            events_df = pd.read_csv(CLEANED_EVENTS_FILE)
            result["total_users"] = int(users_df["user_uuid"].nunique())
            result["total_events"] = len(events_df)
            result["pipeline_data_available"] = True
        except Exception:
            pass
    json_files = glob.glob(os.path.join(OUTPUTS_JSON_DIR, "*.json"))
    result["langgraph_data_available"] = len(json_files) > 0
    result["langgraph_metrics_count"] = len(json_files)
    report_path = os.path.join(OUTPUTS_DIR, "analytics_report.html")
    result["report_available"] = os.path.exists(report_path)
    return JSONResponse(result)


@app.get("/api/users")
async def list_users():
    if not os.path.exists(UNIQUE_USERS_FILE):
        raise HTTPException(status_code=404, detail="User list not found. Run the deduplication pipeline first.")
    users_df = pd.read_csv(UNIQUE_USERS_FILE)
    user_ids = sorted(users_df["user_uuid"].unique().tolist())
    return JSONResponse({"users": user_ids, "count": len(user_ids)})


@app.get("/api/users/{user_id}/events")
async def user_events(user_id: str):
    if not os.path.exists(CLEANED_EVENTS_FILE):
        raise HTTPException(status_code=404, detail="Cleaned events file not found.")
    df = pd.read_csv(CLEANED_EVENTS_FILE)
    user_df = df[df["user_uuid"] == user_id]
    if user_df.empty:
        raise HTTPException(status_code=404, detail="User not found.")
    app_df = user_df[user_df["category"].str.lower() == "application"]
    app_df = app_df.sort_values(["event_date", "event_time_only"])
    cols = ["event_date", "event_day", "event_time_only", "event_name", "category"]
    available_cols = [c for c in cols if c in app_df.columns]
    records = app_df[available_cols].to_dict(orient="records")
    return JSONResponse({
        "user_id": user_id,
        "total_events": len(records),
        "unique_event_types": int(app_df["event_name"].nunique()),
        "events": records,
    })


@app.get("/api/users/{user_id}/repetitions")
async def user_repetitions(user_id: str):
    if not os.path.exists(REPETITION_SUMMARY_FILE):
        raise HTTPException(status_code=404, detail="Repetition summary file not found.")
    df = pd.read_csv(REPETITION_SUMMARY_FILE)
    user_df = df[df["user_uuid"] == user_id]
    if "category" in user_df.columns:
        user_df = user_df[user_df["category"].str.lower() == "application"]
    records = user_df.to_dict(orient="records")
    return JSONResponse({"user_id": user_id, "repetitions": records})


@app.get("/api/metrics/json")
async def all_metrics_json():
    if not os.path.exists(OUTPUTS_JSON_DIR):
        raise HTTPException(status_code=404, detail="No metric outputs found. Run the pipeline first.")
    result = {}
    for filepath in sorted(glob.glob(os.path.join(OUTPUTS_JSON_DIR, "*.json"))):
        name = os.path.splitext(os.path.basename(filepath))[0]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                result[name] = json.load(f)
        except Exception:
            result[name] = {"error": "Failed to load"}
    if not result:
        raise HTTPException(status_code=404, detail="No metric JSON files found.")
    return JSONResponse(result)


@app.get("/api/session-profile")
async def session_profile():
    profile_path = os.path.join(PROJECT_ROOT, "data_profile_report.json")
    if not os.path.exists(profile_path):
        raise HTTPException(status_code=404, detail="Session profile not found. Run the data profiler first.")
    with open(profile_path, "r", encoding="utf-8") as f:
        return JSONResponse(json.load(f))


@app.get("/api/pattern-discovery")
async def pattern_discovery():
    pattern_path = os.path.join(PROJECT_ROOT, "pattern_discovery_report.json")
    if not os.path.exists(pattern_path):
        raise HTTPException(status_code=404, detail="Pattern discovery report not found. Run: python run_pattern_discovery.py")
    with open(pattern_path, "r", encoding="utf-8") as f:
        return JSONResponse(json.load(f))


@app.get("/api/users/{user_id}/journey")
async def user_journey(user_id: str):
    if not os.path.exists(CLEANED_EVENTS_FILE):
        raise HTTPException(status_code=404, detail="Cleaned events file not found.")
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    from insights.journey_builder import build_user_journey, split_into_sessions

    df = pd.read_csv(CLEANED_EVENTS_FILE)
    user_df = df[df["user_uuid"] == user_id]
    if user_df.empty:
        raise HTTPException(status_code=404, detail="User not found.")
    app_df = user_df[user_df["category"].str.lower() == "application"]
    app_df = app_df.sort_values(["event_date", "event_time_only"])

    journey = build_user_journey(app_df)
    sessions_raw = split_into_sessions(journey["events"], gap_minutes=30)

    sessions_out = []
    for idx, sess_events in enumerate(sessions_raw):
        sessions_out.append({
            "session_number": idx + 1,
            "event_count": len(sess_events),
            "first_time": f"{sess_events[0]['date']} {sess_events[0]['time'][:8]}" if sess_events else "",
            "last_time": f"{sess_events[-1]['date']} {sess_events[-1]['time'][:8]}" if sess_events else "",
            "events": sess_events,
        })

    return JSONResponse({
        "user_id": user_id,
        "total_events": journey["total_events"],
        "unique_event_types": journey["unique_event_types"],
        "sessions_detected": len(sessions_raw),
        "metadata": journey["metadata"],
        "sessions": sessions_out,
    })


@app.post("/api/users/{user_id}/interpret")
async def interpret_user_journey(user_id: str):
    if not os.path.exists(CLEANED_EVENTS_FILE):
        raise HTTPException(status_code=404, detail="Cleaned events file not found.")
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    from insights.payload_builder import build_ai_payload
    from insights.journey_interpreter import interpret_journey_safe

    df = pd.read_csv(CLEANED_EVENTS_FILE)
    rep_df = pd.read_csv(REPETITION_SUMMARY_FILE) if os.path.exists(REPETITION_SUMMARY_FILE) else pd.DataFrame()
    user_df = df[df["user_uuid"] == user_id]
    if user_df.empty:
        raise HTTPException(status_code=404, detail="User not found.")
    app_df = user_df[user_df["category"].str.lower() == "application"]
    app_rep_df = rep_df[rep_df["user_uuid"] == user_id] if not rep_df.empty and "user_uuid" in rep_df.columns else pd.DataFrame()
    if "category" in app_rep_df.columns:
        app_rep_df = app_rep_df[app_rep_df["category"].str.lower() == "application"]

    payload = build_ai_payload(app_df, app_rep_df, user_id)
    result = interpret_journey_safe(payload)
    return JSONResponse(result)


@app.post("/api/users/{user_id}/insights")
async def generate_user_insights(user_id: str):
    if not os.path.exists(CLEANED_EVENTS_FILE):
        raise HTTPException(status_code=404, detail="Cleaned events file not found.")
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    from insights.payload_builder import build_ai_payload
    from insights.insights_generator import generate_insights_safe

    df = pd.read_csv(CLEANED_EVENTS_FILE)
    rep_df = pd.read_csv(REPETITION_SUMMARY_FILE) if os.path.exists(REPETITION_SUMMARY_FILE) else pd.DataFrame()
    user_df = df[df["user_uuid"] == user_id]
    if user_df.empty:
        raise HTTPException(status_code=404, detail="User not found.")
    app_df = user_df[user_df["category"].str.lower() == "application"]
    app_rep_df = rep_df[rep_df["user_uuid"] == user_id] if not rep_df.empty and "user_uuid" in rep_df.columns else pd.DataFrame()
    if "category" in app_rep_df.columns:
        app_rep_df = app_rep_df[app_rep_df["category"].str.lower() == "application"]

    payload = build_ai_payload(app_df, app_rep_df, user_id)
    result = generate_insights_safe(payload)
    return JSONResponse(result)
