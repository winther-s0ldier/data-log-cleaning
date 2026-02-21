import json, os, pandas as pd
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_business_query_tools, create_growth_tools
from agents.charts import build_growth_chart

METRIC_NAME = "growth_trends"
TITLE = "PoP Growth & Volume Trends"

SYSTEM_PROMPT = """You are a product growth manager. You are looking at the period-over-period 
(PoP) growth of operator activity on the ApniBus platform.

TASK:
1. Call get_business_dataset_summary for context.
2. Call compute_daily_growth for 7-day and 14-day periods.
3. Provide analysis covering:
   a) GROWTH PERFORMANCE: Is the event volume growing or declining? Cite the percentage 
      change for 7-day vs 14-day.
   b) MOMENTUM: Does the 14-day trend confirm or contradict the 7-day trend? What does 
      this suggest about operator adoption speed?
   c) ACTIONABLE FORECAST: Given the current growth rate, should we increase training or 
      marketing efforts for the operators?

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact growth percentages and volume counts."""

def growth_trends_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        tools = create_business_query_tools(df, ctx) + create_growth_tools(df, ctx)
        insights, iters = run_agent(SYSTEM_PROMPT, tools)
        chart_html = build_growth_chart(ctx)
        
        result = {
            "insights": insights, 
            "fig": chart_html,
            "data": ctx.get("growth_metrics", {}), 
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
