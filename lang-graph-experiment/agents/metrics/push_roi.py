import json, os, pandas as pd
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_query_tools, create_push_roi_tools
from agents.charts import build_push_roi_chart

METRIC_NAME = "push_roi"
TITLE = "Push Notification Engagement ROI"

SYSTEM_PROMPT = """You are a marketing analytics expert for ApniBus.
You are evaluating the performance of push notifications sent to bus operators.

CONTEXT:
- The dataset contains User IDs (user_uuid), allowing you to see how many unique operators are being reached.
- High push engagement is often a leading indicator for platform stickiness.

TASK:
1. Call get_dataset_summary for context on total users and push events.
2. Call get_push_metrics to obtain the Sent -> Delivered -> Click funnel.
3. Provide analysis covering:
   a) DELIVERY PERFORMANCE: Is the delivery rate (> 60% is good)? 
   b) ENGAGEMENT DEPTH: What percentage of unique operators actually click push notifications? 
   c) OPERATIONAL IMPACT: Explain how push engagement correlates with overall operator active users.

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact counts, unique user numbers, and rates."""

def push_roi_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        tools = create_query_tools(df, ctx) + create_push_roi_tools(df, ctx)
        insights, iters = run_agent(SYSTEM_PROMPT, tools)
        chart_html = build_push_roi_chart(ctx)
        
        result = {
            "insights": insights, 
            "fig": chart_html,
            "data": ctx.get("push_metrics", {}), 
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
