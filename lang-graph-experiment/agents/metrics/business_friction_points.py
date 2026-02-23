import json, os, pandas as pd
import numpy as np
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_business_query_tools
from langchain_core.tools import tool
from agents.charts import build_friction_chart

METRIC_NAME = "business_friction_points"
TITLE = "Operator Process Friction"

def create_business_friction_tools(df, ctx):
    @tool
    def detect_global_repetition(min_total: int = 10) -> str:
        """Detect events that repeat consecutively in the global stream (friction)."""
        d = df.sort_values("event_time").copy()
        d["prev_event"] = d["event_name"].shift(1)
        d["is_rep"] = d["event_name"] == d["prev_event"]
        
        agg = d.groupby("event_name")["is_rep"].agg(["sum", "count"])
        agg.columns = ["repeats", "total"]
        agg["rate"] = (agg["repeats"] / agg["total"] * 100).round(1)
        
        agg = agg[agg["total"] >= min_total].sort_values("rate", ascending=False).head(12)
        
        friction = []
        for evt, row in agg.iterrows():
            # For business data, we use 1 as avg_per_session since sessions aren't well-defined
            friction.append({
                "event": evt, 
                "repeat_rate": float(row["rate"]),
                "avg_per_session": 1.0, 
                "total": int(row["total"]), 
                "score": float(row["rate"])
            })
            
        ctx["friction_events"] = friction
        return json.dumps(friction, indent=2)
    return [detect_global_repetition]

SYSTEM_PROMPT = """You are a process efficiency expert for ApniBus.
You are looking for friction in the bus operator's workflow.

CONTEXT:
- The dataset contains User IDs (user_uuid), allowing for precise per-session friction analysis.
- Friction is defined as unnecessary repetition of events (e.g., clicking 'submit' or 'view hisab' multiple times in a row).

TASK:
1. Call get_dataset_summary for context on users and events.
2. Call detect_repeated_events to find the highest friction scores.
3. For the top friction points, analysis:
   a) OPERATIONAL IMPACT: How common are these repetitions among different operators?
   b) PROBABLE CAUSE: Why is the operator repeating this action? (e.g. slow DB load, 
      unclear button state, network lag).
   c) SOLUTION: How to optimize the operator's process or UI?

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact repetition rates and user impact."""

def business_friction_points_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        from agents.tools import create_query_tools, create_friction_tools
        tools = create_query_tools(df, ctx) + create_friction_tools(df, ctx)
        insights, iters = run_agent(SYSTEM_PROMPT, tools)
        chart_html = build_friction_chart(ctx)
        
        result = {
            "insights": insights, 
            "fig": chart_html,
            "data": ctx.get("friction_events", []), 
            "title": TITLE, 
            "iterations": iters
        }
        
        os.makedirs("outputs/json", exist_ok=True)
        with open(f"outputs/json/{METRIC_NAME}.json", "w") as f:
            json.dump({"metric": METRIC_NAME, "data": result["data"], "insights": insights}, f, indent=2)
            
        print(f"  [OK] {METRIC_NAME} ({iters} iterations)")
        return {"metric_results": {METRIC_NAME: result}}
    except Exception as e:
        print(f"  [FAIL] {METRIC_NAME}: {str(e)[:200]}")
        return {"errors": [f"{METRIC_NAME}: {str(e)[:200]}"]}
