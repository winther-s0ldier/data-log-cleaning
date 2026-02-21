import pandas as pd
from agents.state import AnalyticsState


def orchestrator_node(state: AnalyticsState) -> dict:
    path = state["dataset_path"]
    df = pd.read_csv(path)
    df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", utc=True)
    df = df[df["category"] == "application"]

    # Calculate date metrics
    start_date = df["event_time"].min()
    end_date = df["event_time"].max()
    date_range_str = f"{start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')}"
    
    # event_day is already in source CSV
    peak_day = df["event_day"].mode()[0] if "event_day" in df.columns else "N/A"

    is_biz = state.get("pipeline_type") == "business"
    total_users = df["id"].nunique() if is_biz and "id" in df.columns else (df["user_uuid"].nunique() if "user_uuid" in df.columns else 0)

    summary = {
        "total_events": len(df),
        "total_users": int(total_users),
        "total_event_types": df["event_name"].nunique(),
        "days_covered": (end_date - start_date).days + 1,
        "date_range_str": date_range_str,
        "peak_day": peak_day,
        "date_range": {
            "start": str(start_date),
            "end": str(end_date),
        },
        "category_filter": "application",
        "top_events": df["event_name"].value_counts().head(15).to_dict(),
    }

    user_label = "IDs" if is_biz else "users"
    print(f"[Orchestrator] {summary['total_events']:,} application events | {summary['total_users']:,} {user_label} | {summary['total_event_types']} event types")
    print(f"[Orchestrator] Dispatching to metric agents...")

    return {"dataset_summary": summary}
