import json, os, pandas as pd
from agents.state import AnalyticsState
from agents.agent_runner import run_agent
from agents.tools import create_business_query_tools, create_workflow_tools
from agents.charts import build_workflow_chart

METRIC_NAME = "workflow_funnels"
TITLE = "Operational Workflow Analysis"

# Shared Business Workflows
WORKFLOWS = {
    "Hisab (Accounting)": [
        "viewed_hisab_page", "viewed_hisab_bus_detail", "viewed_hisab_trip_detail",
        "clicked_hisab_trip_detail_card", "clicked_hisab_bus_detail_card",
        "clicked_hisab_yestarday_btn", "clicked_hisab_coustom_date_btn",
        "clicked_hisab_today_btn", "clicked_hisab_bus_detail_yeaterday_btn",
    ],
    "Dashboard": [
        "viewed_dashboard_page", "dashboard_clicked_gps_vistar_se_dekhe_bus_card",
        "home_page_load_error", "dashboard_page_pay_btn",
    ],
    "Login / Auth": [
        "viewed_login_page", "viewed_login/signup_page", "viewed_login_otp_verify_page",
        "clicked_login_send_otp_btn", "clicked_login_verify_otp",
        "login_verify_otp_success", "login_verify_otp_failed",
        "User Login", "clicked_login_resend_otp",
    ],
    "Push Notifications": [
        "Push Sent", "Push Delivered", "Push Impression",
        "Push Dismiss", "Push Click", "Push Notification Failed",
    ],
    "Cash Settlement": [
        "clicked_cash_settlement_settle_btn", "clicked_cash_settlement_non_settled_btn",
        "clicked_cash_settlement_trip_setlle_btn",
    ],
}

SYSTEM_PROMPT = f"""You are a business operations analyst for ApniBus.
You are analysing telemetry from the bus operator management platform.

CONTEXT:
- The dataset now contains User IDs (user_uuid), allowing you to identify specific operators.
- You should analyze not just total event volume, but how many unique operators are performing these tasks.

Workflows defined:
{json.dumps(WORKFLOWS, indent=2)}

TASK:
1. Call get_dataset_summary for context on total events and unique operators.
2. Call compute_workflow_volume with the workflows provided above.
3. Call compute_workflow_funnel for the "Login / Auth" workflow using these stages:
   [
     {{"name": "Page View", "events": ["viewed_login_page", "viewed_login/signup_page"]}},
     {{"name": "OTP Request", "events": ["clicked_login_send_otp_btn"]}},
     {{"name": "OTP Verify", "events": ["clicked_login_verify_otp"]}},
     {{"name": "Success", "events": ["login_verify_otp_success", "User Login"]}}
   ]
4. Provide analysis covering:
   a) OPERATIONAL FOCUS: Which workflow has the highest event volume and user penetration? 
      What does this tell us about the most critical tasks for operators?
   b) CRITICAL FUNNELS: Analyze the Login funnel. Where is the biggest drop-off? 
      Cite exact counts and conversion percentages.
   c) OPERATOR BEHAVIOR: Mention if certain workflows are highly concentrated among a 
      few "power operators" or if adoption is broad.
   d) UNTRACKED ACTIVITY: Note any high-volume events not covered by defined workflows.

OUTPUT RULES:
- Use ONLY HTML tags: <h4>, <p>, <ul>, <li>, <strong>. No markdown.
- Cite exact counts and conversion percentages."""

def workflow_funnels_node(state: AnalyticsState) -> dict:
    try:
        df = pd.read_csv(state["dataset_path"])
        df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
        ctx = {}
        # Switch to standard query tools to enable user counting
        from agents.tools import create_query_tools
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
