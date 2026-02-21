import json, os, pandas as pd
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_business_query_tools, create_push_roi_tools
from agents.charts import build_push_roi_chart

METRIC_NAME = "push_roi"
TITLE = "Push Notification Engagement ROI"

SYSTEM_PROMPT = """You are a marketing analytics expert. You are evaluating the return on 
effort (ROI) for push notifications sent to bus operators.

TASK:
1. Call get_business_dataset_summary for context.
2. Call get_push_metrics to obtain the Sent -> Delivered -> Click funnel.
3. Provide analysis covering:
   a) DELIVERY PERFORMANCE: Is the delivery rate (> 60% is good)? Identify bottlenecks 
      if rates are low (e.g. system notification failures).
   b) ENGAGEMENT DEPTH: Is the click-to-delivered rate healthy? What does this imply 
      about the relevance of the notifications being sent?
   c) OPERATIONAL IMPACT: High push click volume often triggers Hisab or Dashboard 
      activity. Link push success to platform engagement.

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact counts and rates."""

def push_roi_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        tools = create_business_query_tools(df, ctx) + create_push_roi_tools(df, ctx)
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
