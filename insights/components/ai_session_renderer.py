import streamlit.components.v1 as components
from typing import Dict, Any
import json


def render_ai_session_cards(parsed_data: Dict[str, Any], height: int = 400) -> None:
    sessions = parsed_data.get("interpreted_sessions", [])
    overall_narrative = parsed_data.get("overall_narrative", "")
    key_observations = parsed_data.get("key_observations", [])
    
    if not sessions:
        components.html("<p>No sessions interpreted by AI.</p>", height=50)
        return
    
    sessions_json = json.dumps(sessions)
    narrative_json = json.dumps(overall_narrative)
    observations_json = json.dumps(key_observations)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: transparent; padding: 10px; color: #e2e8f0; }}
            .narrative {{ background: #2d3748; border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 4px solid #38a169; }}
            .narrative-title {{ font-weight: 600; margin-bottom: 8px; color: #a0aec0; font-size: 12px; text-transform: uppercase; }}
            .narrative-text {{ font-size: 14px; line-height: 1.5; }}
            .observations {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px; }}
            .observation {{ background: #4a5568; padding: 6px 12px; border-radius: 20px; font-size: 12px; }}
            .container {{ display: flex; flex-direction: row; gap: 15px; overflow-x: auto; overflow-y: hidden; padding: 10px 5px; min-height: 200px; }}
            .session-card {{ min-width: 220px; max-width: 220px; background: linear-gradient(135deg, #38a169 0%, #2f855a 100%); border-radius: 12px; padding: 15px; color: white; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; flex-shrink: 0; display: flex; flex-direction: column; }}
            .session-card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 30px rgba(56, 161, 105, 0.4); }}
            .session-header {{ font-weight: 600; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 8px; }}
            .session-meta {{ font-size: 11px; opacity: 0.9; margin-bottom: 10px; }}
            .interpretation {{ font-size: 12px; font-style: italic; opacity: 0.9; margin-bottom: 10px; padding: 8px; background: rgba(255,255,255,0.1); border-radius: 6px; }}
            .event-list {{ flex: 1; overflow-y: auto; font-size: 11px; }}
            .event-item {{ background: rgba(255,255,255,0.15); border-radius: 4px; padding: 4px 6px; margin-bottom: 4px; }}
            .overlay {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.85); z-index: 1000; justify-content: center; align-items: center; padding: 20px; }}
            .overlay.active {{ display: flex; }}
            .expanded-card {{ background: #1a1a2e; border-radius: 16px; padding: 25px; max-width: 90%; max-height: 90%; overflow: auto; color: white; position: relative; }}
            .close-btn {{ position: absolute; top: 15px; right: 15px; background: #e74c3c; border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer; font-size: 16px; }}
            .expanded-header {{ font-size: 18px; font-weight: 600; margin-bottom: 10px; padding-right: 40px; }}
            .expanded-interpretation {{ font-style: italic; color: #a0aec0; margin-bottom: 15px; padding: 10px; background: #2d3748; border-radius: 8px; }}
            .expanded-events {{ display: flex; flex-wrap: wrap; gap: 8px; }}
            .expanded-event {{ background: linear-gradient(135deg, #38a169 0%, #2f855a 100%); padding: 8px 12px; border-radius: 8px; font-size: 12px; }}
            .flow-arrow {{ display: flex; align-items: center; color: #38a169; font-size: 20px; }}
            .container::-webkit-scrollbar {{ height: 8px; }}
            .container::-webkit-scrollbar-track {{ background: #2d3748; border-radius: 4px; }}
            .container::-webkit-scrollbar-thumb {{ background: #38a169; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="narrative">
            <div class="narrative-title">AI Narrative</div>
            <div class="narrative-text" id="narrativeText"></div>
        </div>
        <div class="observations" id="observationsContainer"></div>
        <div class="container" id="sessionContainer"></div>
        <div class="overlay" id="overlay" onclick="closeExpanded(event)">
            <div class="expanded-card" onclick="event.stopPropagation()">
                <button class="close-btn" onclick="closeExpanded(event)">X</button>
                <div class="expanded-header" id="expandedHeader"></div>
                <div class="expanded-interpretation" id="expandedInterpretation"></div>
                <div class="expanded-events" id="expandedEvents"></div>
            </div>
        </div>
        <script>
            const sessions = {sessions_json};
            const narrative = {narrative_json};
            const observations = {observations_json};
            document.getElementById('narrativeText').textContent = narrative;
            const obsContainer = document.getElementById('observationsContainer');
            observations.forEach(obs => {{
                const div = document.createElement('div');
                div.className = 'observation';
                div.textContent = obs;
                obsContainer.appendChild(div);
            }});
            const container = document.getElementById('sessionContainer');
            sessions.forEach((session, idx) => {{
                const card = document.createElement('div');
                card.className = 'session-card';
                card.onclick = () => expandSession(session);
                let eventsHtml = '';
                const events = session.events || [];
                const maxShow = 4;
                events.slice(0, maxShow).forEach(e => {{
                    eventsHtml += '<div class="event-item">' + e + '</div>';
                }});
                if (events.length > maxShow) {{
                    eventsHtml += '<div class="event-item">... +' + (events.length - maxShow) + ' more</div>';
                }}
                card.innerHTML = '<div class="session-header">' + (session.session_name || 'Session ' + (idx + 1)) + '</div><div class="session-meta">' + (session.date || '') + '<br>' + (session.start_time || '') + ' - ' + (session.end_time || '') + '<br>' + events.length + ' events</div><div class="interpretation">' + (session.interpretation || '') + '</div><div class="event-list">' + eventsHtml + '</div>';
                container.appendChild(card);
            }});
            function expandSession(session) {{
                const overlay = document.getElementById('overlay');
                document.getElementById('expandedHeader').textContent = session.session_name || 'Session';
                document.getElementById('expandedInterpretation').textContent = session.interpretation || '';
                let html = '';
                (session.events || []).forEach((e, i) => {{
                    html += '<div class="expanded-event">' + e + '</div>';
                    if (i < (session.events || []).length - 1) {{ html += '<div class="flow-arrow">→</div>'; }}
                }});
                document.getElementById('expandedEvents').innerHTML = html;
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
