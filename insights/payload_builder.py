import pandas as pd
from typing import Dict, Any
import json


def build_ai_payload(user_df: pd.DataFrame, repetition_df: pd.DataFrame, user_id: str) -> Dict[str, Any]:
    if user_df.empty:
        return {
            "user_id": user_id,
            "events_ordered": [],
            "repetition_summary": {
                "total_events": 0,
                "unique_event_types": 0,
                "most_repeated_event": None,
                "repeated_events": []
            }
        }

    user_df = user_df.sort_values(["event_date", "event_time_only"]).reset_index(drop=True)

    events_ordered = []
    for _, row in user_df.iterrows():
        events_ordered.append({
            "event_date": str(row["event_date"]),
            "event_time": str(row["event_time_only"]).strip("'"),
            "event_name": str(row["event_name"]),
            "category": str(row["category"]),
            "event_day": str(row["event_day"])
        })

    repeated_events = []
    if not repetition_df.empty:
        for _, row in repetition_df.iterrows():
            repeated_events.append({
                "event_name": str(row["event_name"]),
                "frequency": int(row["frequency"]),
                "repetitions_removed": int(row["repetitions_removed"])
            })

    most_repeated = None
    if repeated_events:
        most_repeated = max(repeated_events, key=lambda x: x["frequency"])["event_name"]

    repetition_summary = {
        "total_events": len(user_df),
        "unique_event_types": user_df["event_name"].nunique(),
        "most_repeated_event": most_repeated,
        "repeated_events": repeated_events
    }

    return {
        "user_id": user_id,
        "events_ordered": events_ordered,
        "repetition_summary": repetition_summary
    }


def payload_to_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2)