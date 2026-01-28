import pandas as pd
from typing import List, Dict, Any
from datetime import datetime


def build_user_journey(user_df: pd.DataFrame) -> Dict[str, Any]:
    if user_df.empty:
        return {
            "user_id": None,
            "total_events": 0,
            "unique_event_types": 0,
            "events": [],
            "metadata": {}
        }

    user_df = user_df.sort_values(["event_date", "event_time_only"]).reset_index(drop=True)
    user_id = user_df["user_uuid"].iloc[0]

    events = []
    for idx, row in user_df.iterrows():
        events.append({
            "sequence": idx + 1,
            "event_name": row["event_name"],
            "category": row["category"],
            "date": row["event_date"],
            "day": row["event_day"],
            "time": str(row["event_time_only"]).strip("'")
        })

    first_event = user_df.iloc[0]
    last_event = user_df.iloc[-1]

    first_date = pd.to_datetime(first_event["event_date"])
    last_date = pd.to_datetime(last_event["event_date"])
    span_days = (last_date - first_date).days + 1

    metadata = {
        "total_events": len(user_df),
        "unique_event_types": user_df["event_name"].nunique(),
        "date_range": {
            "first_event": f"{first_event['event_date']} {str(first_event['event_time_only']).strip(chr(39))}",
            "last_event": f"{last_event['event_date']} {str(last_event['event_time_only']).strip(chr(39))}",
            "span_days": span_days
        },
        "event_categories": user_df["category"].value_counts().to_dict(),
        "event_breakdown": user_df["event_name"].value_counts().to_dict()
    }

    return {
        "user_id": user_id,
        "total_events": metadata["total_events"],
        "unique_event_types": metadata["unique_event_types"],
        "events": events,
        "metadata": metadata
    }


def format_journey_for_display(journey: Dict[str, Any]) -> str:
    if journey["total_events"] == 0:
        return "No events found for this user."
    event_names = [e["event_name"] for e in journey["events"]]
    return " -> ".join(event_names)


def get_journey_dataframe(journey: Dict[str, Any]) -> pd.DataFrame:
    if journey["total_events"] == 0:
        return pd.DataFrame()
    return pd.DataFrame(journey["events"])


def sanitize_mermaid_label(text: str) -> str:
    replacements = {
        '"': "'", '[': '(', ']': ')', '{': '(', '}': ')',
        '<': '', '>': '', '|': '-', '#': '', '&': 'and',
        ';': '', '\n': ' ', '\r': ''
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if len(text) > 30:
        text = text[:27] + "..."
    return text


def split_into_sessions(events: List[Dict], gap_minutes: int = 30) -> List[List[Dict]]:
    if not events:
        return []
    
    sessions = []
    current_session = [events[0]]
    
    for i in range(1, len(events)):
        prev_event = events[i - 1]
        curr_event = events[i]
        
        try:
            prev_dt = datetime.strptime(f"{prev_event['date']} {prev_event['time'][:8]}", "%Y-%m-%d %H:%M:%S")
            curr_dt = datetime.strptime(f"{curr_event['date']} {curr_event['time'][:8]}", "%Y-%m-%d %H:%M:%S")
            gap = (curr_dt - prev_dt).total_seconds() / 60
            
            if gap > gap_minutes or prev_event['date'] != curr_event['date']:
                sessions.append(current_session)
                current_session = [curr_event]
            else:
                current_session.append(curr_event)
        except:
            current_session.append(curr_event)
    
    if current_session:
        sessions.append(current_session)
    
    return sessions


def build_mermaid_flowchart(journey: Dict[str, Any], max_nodes: int = 50, category_filter: str = None) -> str:
    if journey["total_events"] == 0:
        return "flowchart LR\n    A[No Events Found]"
    
    events = journey["events"]
    
    if category_filter == "application":
        events = [e for e in events if e.get("category", "").lower() == "application"]
    
    if not events:
        return "flowchart LR\n    A[No Events Found]"
    
    sessions = split_into_sessions(events, gap_minutes=30)
    
    lines = ["flowchart TD"]
    node_counter = 1
    
    for session_idx, session_events in enumerate(sessions):
        session_events = session_events[:max_nodes]
        
        if len(sessions) > 1:
            first_time = session_events[0]["time"][:5]
            last_time = session_events[-1]["time"][:5]
            session_date = session_events[0]["date"]
            session_label = f"Session {session_idx + 1}: {session_date} ({first_time} - {last_time})"
            lines.append(f'    subgraph S{session_idx}["{session_label}"]')
            indent = "        "
        else:
            indent = "    "
        
        for i, event in enumerate(session_events):
            safe_name = sanitize_mermaid_label(event["event_name"])
            node_id = f"N{node_counter}"
            lines.append(f'{indent}{node_id}["{safe_name}"]')
            
            if i > 0:
                prev_node = f"N{node_counter - 1}"
                lines.append(f"{indent}{prev_node} --> {node_id}")
            
            node_counter += 1
        
        if len(sessions) > 1:
            lines.append("    end")
    
    lines.append("")
    lines.append("    classDef default fill:#4a5568,stroke:#2d3748,color:#fff")
    
    return "\n".join(lines)


def build_session_flowchart(journey: Dict[str, Any], max_nodes: int = 50) -> str:
    return build_mermaid_flowchart(journey, max_nodes)
