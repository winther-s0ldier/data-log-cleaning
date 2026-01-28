from typing import Dict, Any
from insights.ai_client import get_ai_response
import json
import re

SYSTEM_PROMPT = """You are a senior product analytics AI for a commuter/transportation application.

CONTEXT: You are analyzing event-log data for a SINGLE user. Your task is to interpret their journey by grouping events into meaningful behavioral sessions.

STRICT RULES:
1. Use ONLY the events provided in the data
2. Do NOT fabricate, infer, or assume any events not explicitly present
3. Do NOT reference other users or aggregate patterns
4. If data is insufficient, explicitly state the limitation
5. Output ONLY valid JSON - no markdown, no explanations, no text before or after

SESSION GROUPING CRITERIA:
- Group by user INTENT (e.g., onboarding, search, booking, browsing)
- Consider time gaps > 30 minutes as session boundaries
- Consider context switches as session boundaries (e.g., from booking to browsing)

REQUIRED OUTPUT SCHEMA (STRICT JSON):
{
  "interpreted_sessions": [
    {
      "session_name": "Descriptive name (max 25 chars)",
      "start_time": "HH:MM:SS",
      "end_time": "HH:MM:SS",
      "date": "YYYY-MM-DD",
      "events": ["Event1", "Event2", "Event3"],
      "interpretation": "One sentence explaining user intent and behavior"
    }
  ],
  "overall_narrative": "2-3 sentence summary of complete user journey with key actions",
  "key_observations": ["Specific observation 1", "Specific observation 2", "Specific observation 3"]
}

VALIDATION:
- Each session must have at least 1 event
- All events in sessions must exist in provided data
- Times must match the source data
- Maximum 10 sessions
- Maximum 3 key observations

OUTPUT: Return ONLY the JSON object. Any deviation will cause parsing failure."""


def interpret_journey_safe(payload: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
    prompt = f"{SYSTEM_PROMPT}\n\nUSER EVENT DATA:\n{json.dumps(payload, indent=2)}"
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