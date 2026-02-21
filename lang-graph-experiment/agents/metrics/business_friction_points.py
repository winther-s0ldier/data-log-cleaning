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

SYSTEM_PROMPT = """You are a process efficiency expert. You are looking for friction in 
the bus operator's workflow. 

Friction is defined as an event occurring twice in a row (e.g. clicking 'submit' twice 
or viewing the same page twice consecutively). This suggests the UI didn't respond or 
the operator was confused.

TASK:
1. Call get_business_dataset_summary for context.
2. Call detect_global_repetition to find events with high repetition rates.
3. For the top 3 friction points, provide:
   a) OPERATIONAL IMPACT: How much time is wasted by these repetitions?
   b) PROBABLE CAUSE: Why is the operator repeating this action? (e.g. slow DB load, 
      unclear button state).
   c) SOLUTION: How to optimize the operator's process?

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact repetition rates."""

def business_friction_points_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        tools = create_business_query_tools(df, ctx) + create_business_friction_tools(df, ctx)
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
