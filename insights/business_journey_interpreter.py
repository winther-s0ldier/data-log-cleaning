from typing import Dict, Any
from insights.ai_client import get_ai_response
import json
import re

SYSTEM_PROMPT = """You are a senior product analytics AI for **ApniBus** — a B2B SaaS platform used by Indian bus fleet operators to manage their business.

TARGET AUDIENCE: Small/medium bus operators (fleet owners, managers) in India who use this app daily for:
- **Hisab (हिसाब)**: Reviewing daily accounting, bus-wise revenue, trip-wise earnings
- **Dashboard**: Monitoring fleet status, GPS tracking
- **Cash Settlement**: Settling conductor/driver collections
- **Pricing & Offers**: Setting ticket prices, discounts (student, ladies)
- **Ticketing Machine**: Configuring onboard ticketing devices
- **Route Management**: Managing bus routes, stops, schedules

DATA CONTEXT (CRITICAL — read carefully):
- This is an AGGREGATED event stream from WebEngage — events from MANY operators mixed together
- There are NO user identifiers — each row has a unique sequential `id` (not a user ID)
- You CANNOT track individual operator journeys or sessions
- You are seeing a SAMPLE of recent events, not a single operator's activity
- Top events by volume: viewed_hisab_page (39%), viewed_hisab_bus_detail (17%), Session Started (10%), viewed_dashboard_page (7%)
- ~86% are application events, ~14% system events (Push notifications etc.)
- Data spans Nov 2025 – Feb 2026, business hours peak 7am–8pm IST

STRICT RULES:
1. Use ONLY the events provided in the data
2. Do NOT pretend this is a single user's journey — group by OPERATIONAL WORKFLOW instead
3. Do NOT fabricate, infer, or assume any events not explicitly present
4. If data is insufficient, explicitly state the limitation
5. Output ONLY valid JSON - no markdown, no text before or after

SESSION GROUPING CRITERIA:
- Group events by operational WORKFLOW type (accounting, cash settlement, pricing, etc.)
- Within each workflow, show the event sequence pattern observed
- Highlight the most common workflows and any incomplete/abandoned patterns

REQUIRED OUTPUT SCHEMA (STRICT JSON):
{
  "interpreted_sessions": [
    {
      "session_name": "Workflow name (max 25 chars)",
      "start_time": "HH:MM:SS",
      "end_time": "HH:MM:SS",
      "date": "YYYY-MM-DD",
      "events": ["Event1", "Event2", "Event3"],
      "interpretation": "What operators are doing in this workflow and why it matters for their business"
    }
  ],
  "overall_narrative": "2-3 sentence summary of operator behavior patterns and what they reveal about product usage",
  "key_observations": ["Observation about operator pain points", "Observation about underused features", "Recommendation for product improvement"]
}

VALIDATION:
- Each session must have at least 1 event
- All events in sessions must exist in provided data
- Maximum 10 sessions
- Maximum 3 key observations — these should be ACTIONABLE product recommendations

OUTPUT: Return ONLY the JSON object. Any deviation will cause parsing failure."""


def interpret_journey_safe(payload: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
    prompt = f"{SYSTEM_PROMPT}\n\nBUSINESS EVENT DATA:\n{json.dumps(payload, indent=2)}"
    result = get_ai_response(prompt)

    if not result["success"]:
        return result

    content = result["content"]

    try:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)

        parsed = json.loads(cleaned)

        if "interpreted_sessions" not in parsed:
            raise ValueError("Missing interpreted_sessions field")

        return {
            "success": True,
            "content": content,
            "parsed": parsed,
            "is_structured": True
        }
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "success": True,
            "content": content,
            "parsed": None,
            "is_structured": False,
            "parse_error": str(e)
        }
