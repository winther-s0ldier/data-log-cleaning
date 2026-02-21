import json, os, pandas as pd
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_business_query_tools, create_frequency_tools
from agents.charts import build_frequency_chart

METRIC_NAME = "operational_volume"
TITLE = "Operational System Volume"

SYSTEM_PROMPT = """You are a system operations analyst. You are evaluating the total 
operational load on a bus operator platform.

Since the data is aggregate, we focus on the sheer volume of events across different 
categories and identify peak usage periods.

TASK:
1. Call get_business_dataset_summary for context.
2. Call compute_frequency_distribution to get category counts and top events.
3. Provide analysis covering:
   a) VOLUME PROFILE: Is the volume primarily application-driven or system-driven (push, sync)?
   b) CRITICAL LOAD: Which specific events generate the most traffic? Cite counts.
   c) INFRASTRUCTURE IMPACT: Based on peaks and total volume, what does this tell us 
      about the system's scalability needs?

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact counts."""

def operational_volume_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        # Reuse frequency tools as they are mostly aggregate-friendly
        tools = create_business_query_tools(df, ctx) + create_frequency_tools(df, ctx)
        insights, iters = run_agent(SYSTEM_PROMPT, tools)
        chart_html = build_frequency_chart(ctx)
        
        result = {
            "insights": insights, 
            "fig": chart_html,
            "data": ctx.get("frequency_data", {}), 
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
