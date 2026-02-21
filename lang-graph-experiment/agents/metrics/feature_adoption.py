import json, os, pandas as pd
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_business_query_tools, create_workflow_tools
from agents.charts import build_workflow_chart

METRIC_NAME = "feature_adoption"
TITLE = "Operator Feature Adoption"

SYSTEM_PROMPT = """You are a product adoption specialist. You are analysing how different 
sections of the ApniBus app are being adopted over time.

TASK:
1. Call get_business_dataset_summary for context.
2. Call compute_workflow_volume with all predefined workflows.
3. Review the volume distribution over the analysis span.
4. Provide analysis covering:
   a) ADOPTION LEADERS: Which workflow (Hisab, Dashboard, Pricing) is the primary driver 
      of app interaction?
   b) NEGLECTED FEATURES: Are there workflows with < 5% volume? What can be done to 
      increase adoption of these specific tools (e.g. smart ticketing, card wallets)?
   c) MATURATION: Based on the date range, characterize the product stage: is it in 
      early trial phase or core operations phase for the operators?

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact counts and adoption percentages."""

def feature_adoption_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        # Feature adoption is essentially a workflow distribution analysis
        tools = create_business_query_tools(df, ctx) + create_workflow_tools(df, ctx)
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
