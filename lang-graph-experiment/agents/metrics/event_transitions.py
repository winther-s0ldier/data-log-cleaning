import json, os, pandas as pd
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_query_tools, create_transition_tools
from agents.charts import build_transition_chart

METRIC_NAME = "event_transitions"
TITLE = "Top Event Transitions"

SYSTEM_PROMPT = """You are a behavioral data scientist for ApniBus.
You are analysing the sequential event flow of the bus operator management app.

CONTEXT:
- The dataset contains User IDs (user_uuid), allowing you to see global behavior patterns.

TASK:
1. Call get_dataset_summary for context on total events and unique operators.
2. Call get_top_transitions to identify the most frequent A -> B event pairs.
3. Provide analysis covering:
   a) DOMINANT PATHWAYS: What are the top 5 transitions? What task sequences do they represent?
   b) DEAD ENDS: Are there frequent transitions into "error" or "failure" events?
   c) LOOPING: Identify events that transition back into themselves (A -> A), indicating 
      potential UI confusion or data entry friction.

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact transition counts."""

def event_transitions_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        
        ctx = {}
        tools = create_query_tools(df, ctx) + create_transition_tools(df, ctx)
        insights, iters = run_agent(SYSTEM_PROMPT, tools)
        chart_html = build_transition_chart(ctx)
        
        result = {
            "insights": insights, 
            "fig": chart_html,
            "data": ctx.get("top_transitions", []), 
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
