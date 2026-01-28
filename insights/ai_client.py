import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI
from typing import Dict, Any

def get_ai_response(prompt: str) -> Dict[str, Any]:
    gemini_key = st.secrets.get("GEMINI_API_KEY")
    openai_key = st.secrets.get("OPENAI_API_KEY")
    
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return {"success": True, "content": response.text, "provider": "gemini"}
        except Exception as e:
            if not openai_key:
                return {"success": False, "error": f"Gemini failed: {str(e)}"}
    
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            return {"success": True, "content": response.choices[0].message.content, "provider": "openai"}
        except Exception as e:
            return {"success": False, "error": f"OpenAI failed: {str(e)}"}
    
    return {"success": False, "error": "No API keys configured in st.secrets"}
