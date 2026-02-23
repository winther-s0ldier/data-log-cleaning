import json, os, pandas as pd
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_query_tools, create_workflow_tools
from agents.charts import build_workflow_chart

METRIC_NAME = "feature_adoption"
TITLE = "Operator Feature Adoption"

SYSTEM_PROMPT = """You are a product adoption specialist for ApniBus.
You are analysing how different sections of the operator app are being adopted.

CONTEXT:
- The dataset contains User IDs (user_uuid), allowing you to identify the percentage of the operator base that uses each feature.

TASK:
1. Call get_dataset_summary for context on total events and unique operators.
2. Call compute_workflow_volume with all predefined workflows.
3. Provide analysis covering:
   a) ADOPTION LEADERS: Which workflows (Hisab, Dashboard, etc.) have the highest user penetration?
   b) MATURATION: Contrast total volume vs. user breadh. Is one workflow dominated by a few users?
   c) STRATEGIC GAPS: Identify features with low adoption (< 10% of users) and suggest improvements.

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact counts, user numbers, and adoption percentages."""

def feature_adoption_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        tools = create_query_tools(df, ctx) + create_workflow_tools(df, ctx)
        insights, iters = run_agent(SYSTEM_PROMPT, tools)
        chart_html = build_workflow_chart(ctx)
        
        result = {
            "insights": insights, 
            "fig": chart_html,
            "data": ctx.get("workflow_volume", []), 
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
