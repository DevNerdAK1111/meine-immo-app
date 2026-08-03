import json
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import streamlit as st

def get_gemini_api_key() -> str:
    return st.secrets.get("GEMINI_API_KEY", "") or st.session_state.get("gemini_api_key", "")

def fetch_text_from_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(["script", "style", "header", "footer", "nav", "noscript"]):
            element.extract()
        return ' '.join(line.strip() for line in soup.get_text(separator=' ').splitlines() if line.strip())
    except Exception as e:
        st.error(f"Fehler beim Abrufen der URL: {e}")
        return ""

def analyze_text_with_gemini(api_key, raw_text):
    try:
        genai.configure(api_key=api_key)
        prompt = f"""
        Du bist ein Immobilien-Experte. Analysiere den folgenden Anzeigentext und extrahiere NUR die reinen Objekt-Fakten als valides JSON.
        Geforderte Felder:
        {{
            "kaufpreis": float, "wohnflaeche": float, "baujahr": int,
            "ist_miete_monat": float, "ist_miete_sqm": float, "hausgeld_monat": float,
            "bundesland": string, "stadt": string, "stadtteil": string,
            "objektart": string, "objektname": string
        }}
        Anzeigen-Text: {raw_text[:7000]}
        """
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        response = model.generate_content(prompt)
        cleaned = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned[cleaned.find('{'):cleaned.rfind('}')+1])
    except Exception as e:
        st.error(f"Fehler bei KI-Analyse: {e}")
        return None
