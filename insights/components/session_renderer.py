import streamlit.components.v1 as components
from typing import List, Dict
import json


def render_session_cards(sessions: List[List[Dict]], height: int = 350) -> None:
    sessions_data = []
    for idx, session in enumerate(sessions):
        if not session:
            continue
        
        first_event = session[0]
        last_event = session[-1]
        
        session_info = {
            "id": idx + 1,
            "date": first_event.get("date", "Unknown"),
            "start_time": first_event.get("time", "")[:8],
            "end_time": last_event.get("time", "")[:8],
            "event_count": len(session),
            "events": [
                {
                    "name": e.get("event_name", "Unknown"),
                    "time": e.get("time", "")[:8],
                    "category": e.get("category", "")
                }
                for e in session
            ]
        }
        sessions_data.append(session_info)
    
    sessions_json = json.dumps(sessions_data)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: transparent; padding: 10px; }}
            .container {{ display: flex; flex-direction: row; gap: 15px; overflow-x: auto; overflow-y: hidden; padding: 10px 5px; min-height: 280px; }}
            .session-card {{ min-width: 200px; max-width: 200px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 15px; color: white; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; flex-shrink: 0; display: flex; flex-direction: column; }}
            .session-card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }}
            .session-header {{ font-weight: 600; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 8px; }}
            .session-meta {{ font-size: 11px; opacity: 0.9; margin-bottom: 10px; }}
            .event-list {{ flex: 1; overflow-y: auto; font-size: 11px; }}
            .event-item {{ background: rgba(255,255,255,0.15); border-radius: 4px; padding: 4px 6px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .event-time {{ opacity: 0.7; font-size: 10px; }}
            .overlay {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 1000; justify-content: center; align-items: center; padding: 20px; }}
            .overlay.active {{ display: flex; }}
            .expanded-card {{ background: #1a1a2e; border-radius: 16px; padding: 25px; max-width: 90%; max-height: 90%; overflow: auto; color: white; position: relative; }}
            .close-btn {{ position: absolute; top: 15px; right: 15px; background: #e74c3c; border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; }}
            .close-btn:hover {{ background: #c0392b; }}
            .expanded-header {{ font-size: 18px; font-weight: 600; margin-bottom: 15px; padding-right: 40px; }}
            .expanded-events {{ display: flex; flex-wrap: wrap; gap: 8px; }}
            .expanded-event {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 8px 12px; border-radius: 8px; font-size: 12px; }}
            .flow-arrow {{ display: flex; align-items: center; color: #667eea; font-size: 20px; }}
            .container::-webkit-scrollbar {{ height: 8px; }}
            .container::-webkit-scrollbar-track {{ background: #2d3748; border-radius: 4px; }}
            .container::-webkit-scrollbar-thumb {{ background: #667eea; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container" id="sessionContainer"></div>
        <div class="overlay" id="overlay" onclick="closeExpanded(event)">
            <div class="expanded-card" id="expandedCard" onclick="event.stopPropagation()">
                <button class="close-btn" onclick="closeExpanded(event)">X</button>
                <div class="expanded-header" id="expandedHeader"></div>
                <div class="expanded-events" id="expandedEvents"></div>
            </div>
        </div>
        <script>
            const sessions = {sessions_json};
            const container = document.getElementById('sessionContainer');
            sessions.forEach((session, idx) => {{
                const card = document.createElement('div');
                card.className = 'session-card';
                card.onclick = () => expandSession(session);
                let eventsHtml = '';
                const maxShow = 6;
                session.events.slice(0, maxShow).forEach(e => {{
                    eventsHtml += '<div class="event-item"><span class="event-time">' + e.time + '</span> ' + e.name + '</div>';
                }});
                if (session.events.length > maxShow) {{
                    eventsHtml += '<div class="event-item">... +' + (session.events.length - maxShow) + ' more</div>';
                }}
                card.innerHTML = '<div class="session-header">Session ' + session.id + '</div><div class="session-meta">' + session.date + '<br>' + session.start_time + ' - ' + session.end_time + '<br>' + session.event_count + ' events</div><div class="event-list">' + eventsHtml + '</div>';
                container.appendChild(card);
            }});
            function expandSession(session) {{
                const overlay = document.getElementById('overlay');
                const header = document.getElementById('expandedHeader');
                const events = document.getElementById('expandedEvents');
                header.textContent = 'Session ' + session.id + ': ' + session.date + ' (' + session.start_time + ' - ' + session.end_time + ')';
                let html = '';
                session.events.forEach((e, i) => {{
                    html += '<div class="expanded-event"><strong>' + e.time + '</strong><br>' + e.name + '</div>';
                    if (i < session.events.length - 1) {{ html += '<div class="flow-arrow">→</div>'; }}
                }});
                events.innerHTML = html;
                overlay.classList.add('active');
            }}
            function closeExpanded(event) {{
                if (event.target.classList.contains('overlay') || event.target.classList.contains('close-btn')) {{
                    document.getElementById('overlay').classList.remove('active');
                }}
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_content, height=height, scrolling=True)
