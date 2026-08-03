import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai
from pypdf import PdfReader
import json
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

# -----------------------------------------------------------------------------
# GERMAN NUMBER FORMATTING HELPERS
# -----------------------------------------------------------------------------
def fmt_de(val, decimals=2, suffix=""):
    if val is None or np.isnan(val):
        return "-"
    formatted = f"{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} {suffix}".strip() if suffix else formatted

def fmt_eur(val, decimals=0):
    return fmt_de(val, decimals, "€")

def fmt_pct(val, decimals=2):
    return fmt_de(val, decimals, "%")

def fmt_sqm(val, decimals=0):
    return fmt_de(val, decimals, "m²")

# -----------------------------------------------------------------------------
# PAGE CONFIG & VALUON ESTATE DESIGN SYSTEM (CSS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Valuon Estate",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Typography & Heritage Color Palette */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        color: #2B2D2F;
        background-color: #F7F4EC;
    }
    
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
        background-color: #F7F4EC;
    }
    
    header[data-testid="stHeader"] {
        background: transparent !important;
        z-index: 1;
    }

    /* WIDER SIDEBAR FOR PERFECT INPUT ALIGNMENT */
    section[data-testid="stSidebar"] {
        width: 400px !important;
        min-width: 400px !important;
    }

    /* PERFECT HORIZONTAL ALIGNMENT FOR INPUT LABELS IN COLUMNS */
    section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
        min-height: 42px !important;
        display: flex !important;
        align-items: flex-end !important;
        margin-bottom: 4px !important;
    }

    /* HIDE STREAMLIT INSTRUCTION OVERLAYS COMPLETELY */
    div[data-testid="InputInstructions"], 
    .stInputInstructions, 
    div[aria-live="polite"] {
        display: none !important;
    }
    
    /* Immersive Landing Hero Background */
    .landing-hero {
        background: linear-gradient(135deg, #13381A 0%, #1c4d26 50%, #2b2d2f 100%);
        border-radius: 20px;
        padding: 50px 40px;
        color: #F7F4EC;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(19, 56, 26, 0.15);
        position: relative;
        overflow: hidden;
    }
    
    .landing-hero::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image: url('https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        opacity: 0.12;
        z-index: 0;
    }
    
    .landing-content {
        position: relative;
        z-index: 1;
    }

    /* Valuon Estate Cards */
    .valuon-card {
        background-color: #ffffff;
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        border: 1px solid #D4C9B8;
        box-shadow: 0 4px 12px rgba(19, 56, 26, 0.03);
    }
    
    .valuon-placeholder {
        background: linear-gradient(135deg, #ffffff 0%, #F7F4EC 100%);
        border: 2px dashed #D4C9B8;
        border-radius: 16px;
        padding: 35px 30px;
        text-align: center;
        margin: 20px 0;
    }
    
    /* Custom Button Design */
    .stButton > button {
        border-radius: 980px !important;
        font-weight: 500 !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease !important;
        border: 1px solid #D4C9B8 !important;
        background-color: #ffffff !important;
        color: #2B2D2F !important;
    }
    
    .stButton > button:hover {
        border-color: #13381A !important;
        color: #13381A !important;
        background-color: #F7F4EC !important;
    }
    
    .stButton > button[kind="primary"] {
        background-color: #13381A !important;
        color: #ffffff !important;
        border-color: #13381A !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #1b4d25 !important;
        color: #ffffff !important;
    }

    /* Metric Card System with Custom Hover Tooltips */
    .metric-card {
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        border: 1px solid #D4C9B8;
        background-color: #ffffff;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        position: relative;
        overflow: visible !important;
    }
    .metric-green { border-left: 4px solid #13381A; color: #13381A; }
    .metric-yellow { border-left: 4px solid #A37841; color: #5a4223; }
    .metric-red { border-left: 4px solid #8b3a2b; color: #6b2e22; }
    
    .metric-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .metric-title { 
        font-size: 0.78rem; 
        font-weight: 600; 
        text-transform: uppercase; 
        letter-spacing: 0.5px; 
        opacity: 0.75; 
    }
    .metric-value { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.5px; }
    .metric-status { font-size: 0.8rem; font-weight: 600; margin-top: 4px; }
    
    /* Interactive Tooltip CSS */
    .tooltip-container {
        position: relative;
        display: inline-block;
        cursor: pointer;
    }
    
    .tooltip-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 17px;
        height: 17px;
        border-radius: 50%;
        background-color: #F4EFE6;
        color: #A37841;
        border: 1px solid #D4C9B8;
        font-size: 0.7rem;
        font-weight: 700;
        font-family: serif;
        font-style: italic;
        transition: all 0.2s ease;
    }
    
    .tooltip-container:hover .tooltip-icon {
        background-color: #13381A;
        color: #F7F4EC;
        border-color: #13381A;
    }
    
    .tooltip-box {
        visibility: hidden;
        width: 260px;
        background-color: #2B2D2F;
        color: #F7F4EC;
        text-align: left;
        border-radius: 10px;
        padding: 12px 14px;
        position: absolute;
        z-index: 99;
        bottom: 130%;
        right: 0;
        opacity: 0;
        transition: opacity 0.2s ease, transform 0.2s ease;
        transform: translateY(6px);
        font-size: 0.78rem;
        font-weight: 400;
        line-height: 1.4;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        border: 1px solid #A37841;
        pointer-events: none;
    }

    .tooltip-box strong {
        color: #A37841;
        display: block;
        margin-bottom: 4px;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .tooltip-container:hover .tooltip-box {
        visibility: visible;
        opacity: 1;
        transform: translateY(0);
    }
    
    /* Section Badges */
    .badge-expose {
        background-color: #EBF2EC;
        color: #13381A;
        padding: 4px 12px;
        border-radius: 10px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 10px;
    }
    
    .nk-sub-badge {
        background-color: #F4EFE6;
        color: #555759;
        border: 1px solid #D4C9B8;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
        margin-top: -6px;
        margin-bottom: 10px;
    }

    .nk-total-badge {
        background-color: #F4EFE6;
        color: #13381A;
        border: 1px solid #D4C9B8;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 0.9rem;
        font-weight: 700;
        display: flex;
        justify-content: space-between;
        margin-top: 8px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONSTANTS & STRATEGIES
# -----------------------------------------------------------------------------
GRUNDERWERBSTEUER_MAP = {
    "Baden-Württemberg": 0.050, "Bayern": 0.035, "Berlin": 0.060,
    "Brandenburg": 0.065, "Bremen": 0.050, "Hamburg": 0.055,
    "Hessen": 0.060, "Mecklenburg-Vorpommern": 0.060, "Niedersachsen": 0.050,
    "Nordrhein-Westfalen": 0.065, "Rheinland-Pfalz": 0.050, "Saarland": 0.065,
    "Sachsen": 0.055, "Sachsen-Anhalt": 0.050, "Schleswig-Holstein": 0.065, "Thüringen": 0.065
}

OBJEKTARTEN = [
    "Eigentumswohnung",
    "Einfamilienhaus",
    "Zweifamilienhaus",
    "Reihenhaus / Doppelhaushälfte",
    "Mehrfamilienhaus",
    "Wohn- und Geschäftshaus",
    "Mikroapartment / Studentisches Wohnen",
    "Pflege- / Seniorenimmobilie",
    "Gewerbeimmobilie / Sonstiges"
]

STRATEGIES = {
    "Konservativ / Ausgewogen (Standard)": {
        "target_cf": 50.0, "tol_cf": 0.0,
        "target_rendite": 4.5, "tol_rendite": 3.8,
        "target_roe": 8.0, "tol_roe": 4.0,
        "target_dscr": 1.20, "tol_dscr": 1.05
    },
    "Cashflow-Fokus (B/C-Lage)": {
        "target_cf": 150.0, "tol_cf": 50.0,
        "target_rendite": 6.0, "tol_rendite": 5.0,
        "target_roe": 12.0, "tol_roe": 7.0,
        "target_dscr": 1.25, "tol_dscr": 1.10
    },
    "Wertwachstum / A-Lage": {
        "target_cf": 0.0, "tol_cf": -50.0,
        "target_rendite": 3.5, "tol_rendite": 2.8,
        "target_roe": 6.0, "tol_roe": 3.0,
        "target_dscr": 1.15, "tol_dscr": 1.05
    }
}

# -----------------------------------------------------------------------------
# CALLBACK HELPERS & RENT CALCULATIONS
# -----------------------------------------------------------------------------
def get_smart_defaults(baujahr, objektart):
    bj = int(baujahr) if baujahr else 2000
    obj = str(objektart) if objektart else "Eigentumswohnung"
    age = max(0, 2026 - bj)
    
    if any(k in obj for k in ["Mehrfamilienhaus", "Einfamilienhaus", "Zweifamilienhaus", "Reihenhaus", "Wohn- und Geschäftshaus"]):
        category = "MFH"
    elif "Gewerbe" in obj:
        category = "GEWERBE"
    else:
        category = "ETW"
        
    if age < 5:
        inst = 7.0 if category == "ETW" else (10.0 if category == "MFH" else 6.0)
    elif age <= 15:
        inst = 9.0 if category == "ETW" else (14.0 if category == "MFH" else 8.0)
    elif age <= 30:
        inst = 12.0 if category == "ETW" else (18.0 if category == "MFH" else 10.0)
    else:
        inst = 16.0 if category == "ETW" else (24.0 if category == "MFH" else 14.0)
        
    if "Mikroapartment" in obj:
        mgt = 45.0
    elif category == "MFH":
        mgt = 20.0
    elif category == "GEWERBE":
        mgt = 40.0
    else:
        mgt = 30.0
        
    if "Mikroapartment" in obj:
        vac = 4.0
    elif category == "GEWERBE":
        vac = 7.5
    else:
        vac = 2.0
        
    return inst, mgt, vac

def update_smart_defaults():
    bj = st.session_state.get("baujahr", 2000)
    obj = st.session_state.get("objektart", "Eigentumswohnung")
    inst, mgt, vac = get_smart_defaults(bj, obj)
    
    st.session_state["inst_sqm"] = inst
    st.session_state["mgt_monat"] = mgt
    st.session_state["vac_rate_pct"] = vac

def update_grwt_from_bundesland():
    bl = st.session_state.get("bundesland", "Niedersachsen")
    st.session_state["grwt_p"] = GRUNDERWERBSTEUER_MAP.get(bl, 0.05) * 100

def update_ist_from_monat():
    qm = st.session_state.get("qm", 0.0)
    monat = st.session_state.get("ist_miete_monat", 0.0)
    if qm > 0:
        st.session_state["ist_sqm"] = monat / qm
    else:
        st.session_state["ist_sqm"] = 0.0
        
    if st.session_state.get("target_auto_sync", True):
        st.session_state["target_miete_monat"] = monat
        if qm > 0:
            st.session_state["target_sqm"] = monat / qm

def update_ist_from_sqm():
    qm = st.session_state.get("qm", 0.0)
    sqm_val = st.session_state.get("ist_sqm", 0.0)
    if qm > 0:
        monat = sqm_val * qm
        st.session_state["ist_miete_monat"] = monat
    else:
        st.session_state["ist_miete_monat"] = 0.0
        
    if st.session_state.get("target_auto_sync", True):
        st.session_state["target_miete_monat"] = st.session_state.get("ist_miete_monat", 0.0)
        st.session_state["target_sqm"] = sqm_val

def update_target_from_monat():
    qm = st.session_state.get("qm", 0.0)
    monat = st.session_state.get("target_miete_monat", 0.0)
    if qm > 0:
        st.session_state["target_sqm"] = monat / qm
    else:
        st.session_state["target_sqm"] = 0.0
    st.session_state["target_auto_sync"] = False

def update_target_from_sqm():
    qm = st.session_state.get("qm", 0.0)
    sqm_val = st.session_state.get("target_sqm", 0.0)
    if qm > 0:
        st.session_state["target_miete_monat"] = sqm_val * qm
    else:
        st.session_state["target_miete_monat"] = 0.0
    st.session_state["target_auto_sync"] = False

def update_qm_callback():
    qm = st.session_state.get("qm", 0.0)
    if qm > 0:
        monat = st.session_state.get("ist_miete_monat", 0.0)
        if monat > 0:
            st.session_state["ist_sqm"] = monat / qm
        
        if st.session_state.get("target_auto_sync", True):
            st.session_state["target_miete_monat"] = monat
            st.session_state["target_sqm"] = monat / qm if qm > 0 else 0.0
        else:
            t_monat = st.session_state.get("target_miete_monat", 0.0)
            if t_monat > 0:
                st.session_state["target_sqm"] = t_monat / qm

# -----------------------------------------------------------------------------
# SECRETS & HELPERS
# -----------------------------------------------------------------------------
def get_gemini_api_key() -> str:
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if secret_key:
        return secret_key
    return st.session_state.get("gemini_api_key", "")

def get_supabase_client() -> Client:
    sb_url = st.secrets.get("SUPABASE_URL", "") or st.session_state.get("supabase_url", "")
    sb_key = st.secrets.get("SUPABASE_KEY", "") or st.session_state.get("supabase_key", "")
    if sb_url and sb_key:
        try:
            return create_client(sb_url, sb_key)
        except Exception:
            return None
    return None

def db_save_project(supabase: Client, user_id: str, project_name: str, payload: dict):
    try:
        res = supabase.table("projects").select("id").eq("user_id", user_id).eq("project_name", project_name).execute()
        if res.data and len(res.data) > 0:
            pid = res.data[0]["id"]
            supabase.table("projects").update({"input_data": payload}).eq("id", pid).execute()
            st.success(f"Projekt '{project_name}' aktualisiert.")
        else:
            supabase.table("projects").insert({
                "user_id": user_id,
                "project_name": project_name,
                "input_data": payload
            }).execute()
            st.success(f"Projekt '{project_name}' gespeichert.")
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")

def db_get_projects(supabase: Client, user_id: str):
    if not supabase:
        return []
    try:
        res = supabase.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def db_delete_project(supabase: Client, project_id: int):
    try:
        supabase.table("projects").delete().eq("id", project_id).execute()
        st.success("Projekt gelöscht.")
    except Exception as e:
        st.error(f"Fehler beim Löschen: {e}")

# -----------------------------------------------------------------------------
# SANITY & LOGIC CHECK FUNCTION
# -----------------------------------------------------------------------------
def check_input_sanity(d: dict) -> list:
    warnings = []
    if d['hb_zins'] > 0.15:
        warnings.append(f"Zinssatz Hausbank ({fmt_pct(d['hb_zins']*100)}) ist ungewöhnlich hoch. Vertippt? (z.B. 3,8% statt 38%)")
    if d['kfw_zins'] > 0.15:
        warnings.append(f"Zinssatz KfW ({fmt_pct(d['kfw_zins']*100)}) ist sehr hoch angesetzt.")
    if d['notar_proz'] > 0.10:
        warnings.append(f"Notar- und Gerichtskosten ({fmt_pct(d['notar_proz']*100)}) sind sehr hoch.")
    if d['makler_proz'] > 0.15:
        warnings.append(f"Maklerprovision ({fmt_pct(d['makler_proz']*100)}) ist sehr hoch.")
    if d['miet_inc'] > 0.10:
        warnings.append(f"Erwartete Mietsteigerung ({fmt_pct(d['miet_inc']*100)} p.a.) ist sehr hoch.")
    if d['val_inc'] > 0.10:
        warnings.append(f"Erwartete Wertsteigerung ({fmt_pct(d['val_inc']*100)} p.a.) ist sehr hoch.")
    if d['tax_rate'] > 0.50:
        warnings.append(f"Grenzsteuersatz ({fmt_pct(d['tax_rate']*100)}) liegt über dem Höchstsatz.")
    if d['hausgeld'] > 0 and d['hausgeld_nicht_umlegbar'] > d['hausgeld']:
        warnings.append("Das nicht umlegbare Hausgeld darf nicht größer sein als das Gesamthausgeld.")
    return warnings

# -----------------------------------------------------------------------------
# SCRAPING & AI FUNCTIONS
# -----------------------------------------------------------------------------
def fetch_text_from_url(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        response = requests.get(url, headers=headers, timeout=12)
        
        if response.status_code == 403 or "captcha" in response.text.lower():
            st.warning("Die Zielseite blockiert automatisierte Abfragen (Bot-Schutz). Bitte kopieren Sie den Anzeigentext manuell.")
            return ""
            
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for element in soup(["script", "style", "header", "footer", "nav", "noscript"]):
            element.extract()
            
        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return '\n'.join(chunk for chunk in chunks if chunk)
        
    except Exception as e:
        st.error(f"Fehler beim Abrufen der URL: {e}")
        return ""

def analyze_text_with_gemini(api_key, raw_text):
    try:
        genai.configure(api_key=api_key)
        
        prompt = f"""
        Du bist ein Immobilien-Experte. Analysiere den folgenden Anzeigentext und extrahiere NUR die reinen Objekt-Fakten als valides JSON.
        Verwende 0 oder "Unbekannt", falls ein Wert im Text nicht vorhanden ist.

        Geforderte Felder:
        {{
            "kaufpreis": float,
            "wohnflaeche": float,
            "baujahr": int,
            "ist_miete_monat": float,
            "ist_miete_sqm": float,
            "hausgeld_monat": float,
            "bundesland": string,
            "stadt": string,
            "stadtteil": string,
            "objektart": string,
            "objektname": string
        }}

        Anzeigen-Text:
        {raw_text[:7000]}
        """
        
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except Exception:
            pass

        preferred = [m for m in available_models if 'flash' in m.lower()] + \
                    [m for m in available_models if 'pro' in m.lower()] + \
                    available_models

        if not preferred:
            preferred = [
                'models/gemini-1.5-flash',
                'models/gemini-2.0-flash',
                'models/gemini-1.5-pro',
                'gemini-1.5-flash'
            ]

        candidate_models = list(dict.fromkeys(preferred))
        response = None
        last_exception = None

        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    break
            except Exception as m_err:
                last_exception = m_err
                continue

        if not response or not response.text:
            if last_exception:
                raise last_exception
            st.error("Keine Antwort von der KI erhalten.")
            return None

        cleaned_json = response.text.replace('```json', '').replace('```', '').strip()
        start_idx = cleaned_json.find('{')
        end_idx = cleaned_json.rfind('}')
        if start_idx != -1 and end_idx != -1:
            cleaned_json = cleaned_json[start_idx:end_idx+1]
            
        return json.loads(cleaned_json)

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "quota" in err_msg.lower():
            st.error("API-Limit von Google erreicht. Bitte einen Moment warten.")
        elif "API_KEY" in err_msg.upper() or "INVALID" in err_msg.upper():
            st.error("Ungültiger API-Schlüssel. Bitte in den Einstellungen prüfen.")
        else:
            st.error(f"Fehler bei der Datenextraktion: {err_msg}")
        return None

def calc_projection(data, full_repayment=False):
    kp = data['kaufpreis']
    san = data['sanierung']
    
    grwt_rate = data.get('grwt_proz', 0.05)
    nk_proz = grwt_rate + data['notar_proz'] + data['makler_proz']
    nk_abs = kp * nk_proz + data['sonst_nk']
    
    c_base = kp + san + nk_abs
    ek_euro_input = data.get('ek_euro', 0.0)
    
    disagio_p = data['disagio_proz']
    disagio_betrag = c_base * (1 - data.get('ek_quote', 0.20)) * disagio_p
    
    tot_inv = c_base + disagio_betrag
    ek_abs = min(ek_euro_input, tot_inv) if ek_euro_input > 0 else tot_inv * 0.20
    
    ek_quote_calculated = (ek_abs / tot_inv) if tot_inv > 0 else 0.0
    fk_tot = max(0.0, tot_inv - ek_abs)
    
    kfw_loan = max(0, data['kfw_amt'] - data['kfw_grant'])
    hb_loan = max(0.0, fk_tot - kfw_loan)
    
    afa_base = (kp + nk_abs) * (1 - data['grund_anteil'])
    
    rows = []
    restschuld_hb = hb_loan
    restschuld_kfw = kfw_loan
    obj_val = tot_inv
    
    current_sqm_rent = data['ist_sqm']
    
    hausgeld_tot = data['hausgeld']
    hausgeld_nu = data.get('hausgeld_nicht_umlegbar', 0.0)
    
    if hausgeld_tot > 0 and hausgeld_nu <= 0:
        eff_nicht_umlegbar = hausgeld_tot * 0.25
    else:
        eff_nicht_umlegbar = hausgeld_nu
        
    annual_nu_hausgeld = eff_nicht_umlegbar * 12
    
    loan_type = data.get('loan_type', 'Annuitätendarlehen')
    hb_initial_annuity = hb_loan * (data['hb_zins'] + data['hb_tilg']) if hb_loan > 0 else 0
    kfw_initial_annuity = kfw_loan * (data['kfw_zins'] + data['kfw_tilg']) if kfw_loan > 0 else 0
    
    yr = 1
    max_yr = 40 if full_repayment else 10
    
    building_book_value = afa_base
    
    while yr <= max_yr:
        if full_repayment and yr > 10 and restschuld_hb <= 0 and restschuld_kfw <= 0:
            break
            
        if yr >= data['adj_year']:
            if yr == data['adj_year']:
                current_sqm_rent = data['target_sqm']
            else:
                current_sqm_rent *= (1 + data['miet_inc'])
        
        gross_rent = (current_sqm_rent * data['qm'] + data['park']) * 12
        vacancy = gross_rent * data['vac_rate']
        net_rent = gross_rent - vacancy
        
        op_costs = (annual_nu_hausgeld + (data['inst_sqm'] * data['qm']) + (data['mgt_monat'] * 12)) * ((1 + data['cost_inc']) ** (yr - 1))
        
        capex = 0
        if yr == 3: capex = data['capex_j3']
        if yr == 6: capex = data['capex_j6']
        
        noi = net_rent - op_costs - capex
        
        # Hausbank Loan
        zins_hb = restschuld_hb * data['hb_zins'] if restschuld_hb > 0 else 0.0
        if restschuld_hb > 0:
            if yr <= data['grace_years']:
                tilg_hb = 0.0
            else:
                if loan_type == "Annuitätendarlehen":
                    target_payment = hb_initial_annuity
                    needed_tilg = target_payment - zins_hb
                    tilg_hb = max(0.0, min(restschuld_hb, needed_tilg))
                elif loan_type == "Tilgungsdarlehen":
                    tilg_hb = hb_loan * data['hb_tilg']
                    tilg_hb = min(restschuld_hb, tilg_hb)
                else:
                    tilg_hb = restschuld_hb if (yr == max_yr or (not full_repayment and yr == 10)) else 0.0
        else:
            zins_hb = 0.0
            tilg_hb = 0.0
            
        # KfW Loan
        zins_kfw = restschuld_kfw * data['kfw_zins'] if (kfw_loan > 0 and restschuld_kfw > 0) else 0.0
        if kfw_loan > 0 and restschuld_kfw > 0:
            kfw_grace = data.get('kfw_grace_years', 0)
            if yr <= kfw_grace:
                tilg_kfw = 0.0
            else:
                if loan_type == "Endfälliges Darlehen":
                    tilg_kfw = restschuld_kfw if (yr == max_yr or (not full_repayment and yr == 10)) else 0.0
                else:
                    target_kfw_pay = kfw_initial_annuity
                    needed_kfw_tilg = target_kfw_pay - zins_kfw
                    tilg_kfw = max(0.0, min(restschuld_kfw, needed_kfw_tilg))
        else:
            zins_kfw = 0.0
            tilg_kfw = 0.0
            
        zins_tot = zins_hb + zins_kfw
        sondertilg = data['sondertilg'] if yr > data.get('grace_years', 0) else 0.0
        actual_sondertilg = min(restschuld_hb, sondertilg) if restschuld_hb > 0 else 0.0
        
        tilg_tot = tilg_hb + tilg_kfw + actual_sondertilg
        
        cf_v_st = noi - zins_tot - tilg_tot
        
        if data['afa_model'] == "2_Degressiv_§7_5a":
            afa_val = building_book_value * 0.05
            building_book_value = max(0.0, building_book_value - afa_val)
        elif data['afa_model'] == "3_Sonder_AfA_§7b":
            afa_val = (afa_base * 0.02) + (afa_base * 0.05 if yr <= 4 else 0)
        elif data['afa_model'] == "4_Denkmal_§7h_7i":
            afa_val = afa_base * (0.09 if yr <= 8 else 0.07)
        else:
            afa_val = afa_base * data['afa_lin']
            
        disagio_deduct = disagio_betrag if yr == 1 else 0
        
        if yr == 1 and san <= (afa_base * 0.15):
            taxable_inc = noi - zins_tot - afa_val - disagio_deduct - san
        else:
            taxable_inc = noi - zins_tot - afa_val - disagio_deduct
            
        tax_val = taxable_inc * data['tax_rate']
        cf_n_st = cf_v_st - tax_val
        
        restschuld_hb = max(0.0, restschuld_hb - tilg_hb - actual_sondertilg)
        restschuld_rest = max(0.0, restschuld_kfw - tilg_kfw)
        restschuld_tot = restschuld_hb + restschuld_rest
        
        obj_val *= (1 + data['val_inc'])
        nav = obj_val - restschuld_tot
        ltv = restschuld_tot / obj_val if obj_val > 0 else 0.0
        
        bruttomietrendite = gross_rent / kp if kp > 0 else 0.0
        
        rows.append({
            "Jahr": yr,
            "Bruttomietrendite": bruttomietrendite,
            "Brutto-Kaltmiete": gross_rent,
            "NOI": noi,
            "Zinsen": zins_tot,
            "Tilgung": tilg_tot,
            "CF v. St.": cf_v_st,
            "AfA": afa_val,
            "Steuer": tax_val,
            "CF n. St.": cf_n_st,
            "Restschuld": restschuld_tot,
            "Objektwert": obj_val,
            "NAV": nav,
            "LTV": ltv
        })
        
        yr += 1
        if not full_repayment and yr > 10:
            break
            
    df = pd.DataFrame(rows)
    
    cf_stream = [-ek_abs] + list(df['CF n. St.'].iloc[:-1]) + [df['CF n. St.'].iloc[-1] + (df['Objektwert'].iloc[-1] * (1 - data['exit_cost']) - df['Restschuld'].iloc[-1])]
    try:
        irr = npf.irr(cf_stream)
    except:
        irr = 0.0
        
    return df, tot_inv, ek_abs, fk_tot, irr, afa_base, ek_quote_calculated

def get_metric_status(val, target_green, target_yellow):
    if val >= target_green:
        return "green", "Zielwert erreicht"
    elif val >= target_yellow:
        return "yellow", "Im Toleranzbereich"
    else:
        return "red", "Kriterium unterschritten"

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = ""
if "selected_strategy_name" not in st.session_state:
    st.session_state["selected_strategy_name"] = "Konservativ / Ausgewogen (Standard)"
if "nav_choice" not in st.session_state:
    st.session_state["nav_choice"] = "Pipeline"
if "trigger_analysis" not in st.session_state:
    st.session_state["trigger_analysis"] = False
if "target_auto_sync" not in st.session_state:
    st.session_state["target_auto_sync"] = True

default_state = {
    "obj_name": "", "objektart": "Eigentumswohnung", "stadt": "", "stadtteil": "",
    "bundesland": "Niedersachsen", "kaufpreis": 0.0,
    "qm": 0.0, "baujahr": 2000, "sanierung": 0.0, "grund_anteil": 0.20,
    "grwt_p": 5.0, "notar_p": 2.0, "makler_p": 3.57, "sonst_nk": 0.0, "disagio_p": 0.0,
    "ek_euro": 0.0, "ek_quote": 0.20, "loan_type": "Annuitätendarlehen", "hb_zins": 3.8, "hb_tilg": 2.0, "grace_years": 0,
    "kfw_amt": 0.0, "kfw_zins": 2.1, "kfw_tilg": 3.0, "kfw_grace_years": 0, "kfw_grant": 0.0, "sondertilg": 0.0,
    "ist_miete_monat": 0.0, "ist_sqm": 0.0, "target_miete_monat": 0.0, "target_sqm": 0.0, "adj_year": 3, "park": 0.0, 
    "vac_rate_pct": 2.0, "hausgeld": 0.0, "hausgeld_nicht_umlegbar": 0.0,
    "inst_sqm": 12.0, "mgt_monat": 30.0, "capex_j3": 0.0, "capex_j6": 0.0,
    "tax_rate_pct": 42.0, "afa_model": "1_Linear_Standard", "afa_lin": 2.0, "miet_inc": 1.5,
    "cost_inc": 2.0, "val_inc": 1.5, "wacc": 6.0, "exit_cost": 2.0
}

for k, v in default_state.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.get("notar_p", 0.0) == 0.0:
    st.session_state["notar_p"] = 2.00
if st.session_state.get("makler_p", 0.0) == 0.0:
    st.session_state["makler_p"] = 3.57
if st.session_state.get("grwt_p", 0.0) == 0.0:
    bl = st.session_state.get("bundesland", "Niedersachsen")
    st.session_state["grwt_p"] = GRUNDERWERBSTEUER_MAP.get(bl, 0.05) * 100

sb_client = get_supabase_client()

# -----------------------------------------------------------------------------
# AUTH GATE (WITH PERMANENT DEVELOPER LOGIN)
# -----------------------------------------------------------------------------
if not st.session_state["authenticated"]:
    st.markdown("""
    <div class="landing-hero">
        <div class="landing-content">
            <div style="font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; color: #A37841; margin-bottom: 8px;">Institutional Grade Suite</div>
            <h1 style="font-size: 3.5rem; font-weight: 800; letter-spacing: -1.5px; color: #F7F4EC; margin-bottom: 15px; line-height: 1.05;">Valuon Estate</h1>
            <p style="font-size: 1.25rem; color: #D4C9B8; max-width: 650px; margin: 0 0 25px 0; font-weight: 300;">
                Die hochentwickelte Analyse- und Bewertungsumgebung für professionelle Immobilien-Investitionen und Portfoliostrukturierung.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_landing1, col_landing2 = st.columns([1.3, 1])

    with col_landing1:
        col_img1, col_img2 = st.columns(2)
        with col_img1:
            st.image("https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=600&q=80", use_container_width=True)
            st.image("https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=600&q=80", use_container_width=True)
        with col_img2:
            st.image("https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=600&q=80", use_container_width=True)
            st.image("https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=600&q=80", use_container_width=True)
        
        st.markdown("""
        <div class="valuon-card" style="margin-top: 15px;">
            <h3 style="margin-top:0; color:#13381A; font-size:1.1rem;">Präzision in jedem Deal</h3>
            <p style="color:#555759; font-size:0.95rem; margin-bottom:0;">Automatisierter Exposé-Abgleich via Gemini AI, granulare Projektionen und automatisierte Risikotests im zeitlosen Heritage-Design.</p>
        </div>
        """, unsafe_allow_html=True)

    with col_landing2:
        st.markdown("<div class='valuon-card'>", unsafe_allow_html=True)
        st.markdown("### Zugangsportal")
        
        if st.button("🛠️ Als Entwickler einloggen (Permanenter Modus)", type="primary", use_container_width=True):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "developer@valuon-estate.de"
            st.rerun()

        st.divider()
        auth_tab1, auth_tab2 = st.tabs(["Login", "Registrieren"])
        
        with auth_tab1:
            email_in = st.text_input("E-Mail-Adresse", key="login_email")
            pass_in = st.text_input("Passwort", type="password", key="login_pass")
            
            if st.button("Anmelden", use_container_width=True):
                if sb_client:
                    try:
                        res = sb_client.auth.sign_in_with_password({"email": email_in, "password": pass_in})
                        st.session_state["authenticated"] = True
                        st.session_state["user_email"] = email_in
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login fehlgeschlagen: {e}")
                else:
                    if email_in and pass_in:
                        st.session_state["authenticated"] = True
                        st.session_state["user_email"] = email_in
                        st.rerun()
                    else:
                        st.error("Bitte Anmeldedaten eingeben.")

        with auth_tab2:
            reg_email = st.text_input("E-Mail-Adresse", key="reg_email")
            reg_pass = st.text_input("Passwort erstellen", type="password", key="reg_pass")
            if st.button("Konto erstellen", use_container_width=True):
                if sb_client:
                    try:
                        res = sb_client.auth.sign_up({"email": reg_email, "password": reg_pass})
                        st.success("Registrierung erfolgreich. Sie können sich nun anmelden.")
                    except Exception as e:
                        st.error(f"Registrierung fehlgeschlagen: {e}")
                else:
                    st.success("Demo-Profil angelegt. Bitte wechseln Sie zum Login-Tab.")
            
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# -----------------------------------------------------------------------------
# MAIN APPLICATION HEADER & TOP NAVIGATION
# -----------------------------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("""
    <div style="font-size: 2.3rem; font-weight: 800; letter-spacing: -0.8px; color: #13381A; line-height: 1.1;">
        Valuon Estate
    </div>
    <div style="font-size: 0.85rem; color: #A37841; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px;">
        Investment Suite
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<div style='text-align: right; font-size: 0.85rem; color: #555759; margin-top: 10px;'>Konto: {st.session_state['user_email']}</div>", unsafe_allow_html=True)
    if st.button("Abmelden", key="btn_logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user_email"] = ""
        st.session_state["trigger_analysis"] = False
        st.rerun()

st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)

nav_items = ["Pipeline", "Analyse", "Vergleich", "Kaufpreis", "Immobilienwissen", "Einstellungen"]
nav_cols = st.columns(len(nav_items))

for idx, item in enumerate(nav_items):
    is_active = (st.session_state["nav_choice"] == item)
    btn_type = "primary" if is_active else "secondary"
    if nav_cols[idx].button(item, key=f"nav_btn_{idx}", type=btn_type, use_container_width=True):
        st.session_state["nav_choice"] = item
        st.rerun()

st.divider()

nav_choice = st.session_state["nav_choice"]

# =============================================================================
# MODUL 1: PIPELINE
# =============================================================================
if nav_choice == "Pipeline":
    st.markdown("## Investment-Pipeline")
    st.markdown("<p style='color:#555759;'>Übersicht und Verwaltung aller bewerteten Objekte.</p>", unsafe_allow_html=True)

    projects = db_get_projects(sb_client, st.session_state["user_email"])
    
    if projects:
        table_rows = []
        for p in projects:
            d = p["input_data"]
            calc_p, _, ek_p, fk_p, irr_p, _, _ = calc_projection({
                'kaufpreis': d.get("kaufpreis", 0), 'sanierung': d.get("sanierung", 0),
                'bundesland': d.get("bundesland", "Niedersachsen"),
                'grwt_proz': d.get("grwt_p", 5.0)/100,
                'notar_proz': d.get("notar_p", 2.0)/100,
                'makler_proz': d.get("makler_p", 3.57)/100, 'sonst_nk': d.get("sonst_nk", 0.0),
                'disagio_proz': d.get("disagio_p", 0)/100, 'ek_euro': d.get("ek_euro", 0.0),
                'ek_quote': d.get("ek_quote", 0.2),
                'loan_type': d.get("loan_type", "Annuitätendarlehen"),
                'hb_zins': d.get("hb_zins", 3.8)/100,
                'hb_tilg': d.get("hb_tilg", 2.0)/100, 'grace_years': d.get("grace_years", 0),
                'kfw_amt': d.get("kfw_amt", 0), 'kfw_zins': d.get("kfw_zins", 2.1)/100,
                'kfw_tilg': d.get("kfw_tilg", 3.0)/100, 'kfw_grace_years': d.get("kfw_grace_years", 0), 'kfw_grant': d.get("kfw_grant", 0),
                'sondertilg': d.get("sondertilg", 0), 'ist_sqm': d.get("ist_sqm", 0),
                'target_sqm': d.get("target_sqm", 0) if d.get("target_sqm", 0) > 0 else d.get("ist_sqm", 0),
                'adj_year': d.get("adj_year", 3),
                'park': d.get("park", 0), 'vac_rate': d.get("vac_rate_pct", 2.0)/100,
                'qm': d.get("qm", 0), 'hausgeld': d.get("hausgeld", 0),
                'hausgeld_nicht_umlegbar': d.get("hausgeld_nicht_umlegbar", 0),
                'inst_sqm': d.get("inst_sqm", 12.0), 'mgt_monat': d.get("mgt_monat", 30.0),
                'capex_j3': d.get("capex_j3", 0), 'capex_j6': d.get("capex_j6", 0),
                'tax_rate': d.get("tax_rate_pct", 42.0)/100, 'afa_model': d.get("afa_model", "1_Linear_Standard"),
                'afa_lin': d.get("afa_lin", 2.0)/100, 'miet_inc': d.get("miet_inc", 1.5)/100,
                'cost_inc': d.get("cost_inc", 2.0)/100, 'val_inc': d.get("val_inc", 1.5)/100,
                'wacc': d.get("wacc", 6.0)/100, 'exit_cost': d.get("exit_cost", 2.0)/100,
                'grund_anteil': d.get("grund_anteil", 0.2)
            }, full_repayment=False)
            
            cf_m = calc_p.loc[0, 'CF n. St.'] / 12
            rendite = calc_p.loc[0, 'Bruttomietrendite'] * 100
            
            loc = d.get("stadt", "")
            if d.get("stadtteil"):
                loc += f" ({d.get('stadtteil')})"
            if not loc:
                loc = d.get("bundesland", "Unbekannt")
                
            table_rows.append({
                "Objektname": p["project_name"],
                "Typ": d.get("objektart", "Eigentumswohnung"),
                "Standort": loc,
                "Kaufpreis": fmt_eur(d.get('kaufpreis', 0)),
                "Fläche": fmt_sqm(d.get('qm', 0)),
                "Cashflow (netto)": f"{fmt_de(cf_m, 2)} €/M",
                "Bruttomietrendite": fmt_pct(rendite),
                "10J-IRR": fmt_pct(irr_p*100)
            })
            
        df_summary = pd.DataFrame(table_rows)
        st.dataframe(df_summary, use_container_width=True)
        
        st.divider()
        st.markdown("### Schnellaktionen")
        col_act1, col_act2 = st.columns(2)
        
        selected_project_name = col_act1.selectbox("Projekt auswählen", [p["project_name"] for p in projects])
        
        if col_act1.button("In Analyse-Rechner laden", type="primary", use_container_width=True):
            p_target = next(p for p in projects if p["project_name"] == selected_project_name)
            for k, v in p_target["input_data"].items():
                st.session_state[k] = v
            st.session_state["nav_choice"] = "Analyse"
            st.session_state["trigger_analysis"] = True
            st.rerun()

        if col_act2.button("Projekt löschen", use_container_width=True):
            p_target = next(p for p in projects if p["project_name"] == selected_project_name)
            db_delete_project(sb_client, p_target["id"])
            st.rerun()

    else:
        st.info("Bisher keine Projekte in der Datenbank hinterlegt. Nutzen Sie den Bereich 'Analyse', um ein neues Objekt zu erfassen.")

# =============================================================================
# MODUL 2: ANALYSE & RECHNER
# =============================================================================
elif nav_choice == "Analyse":
    
    with st.sidebar:
        st.markdown("<span class='badge-expose'>1. Objektdaten (Exposé)</span>", unsafe_allow_html=True)
        
        with st.expander("🤖 KI-gestützter Import (Beta)", expanded=False):
            active_api_key = get_gemini_api_key()
            import_type = st.radio("Quellformat wählen:", ["Web-Link (URL)", "PDF Exposé", "Text manuell"])
            extracted_text_to_analyze = ""
            
            if import_type == "PDF Exposé":
                uploaded_pdf = st.file_uploader("Exposé als PDF hochladen", type=["pdf"])
                if uploaded_pdf:
                    reader = PdfReader(uploaded_pdf)
                    for page in reader.pages:
                        extracted_text_to_analyze += page.extract_text() or ""

            elif import_type == "Web-Link (URL)":
                input_url = st.text_input("Inserat-URL (z. B. ImmoScout, Kleinanzeigen):")
                if input_url:
                    with st.spinner("Lade Inserat-Inhalte..."):
                        extracted_text_to_analyze = fetch_text_from_url(input_url)

            elif import_type == "Text manuell":
                extracted_text_to_analyze = st.text_area("Exposé-Text einfügen:", height=120)

            if extracted_text_to_analyze and active_api_key:
                if st.button("Objektdaten auslesen", use_container_width=True, type="primary"):
                    with st.spinner("Analysiere Objekt-Fakten..."):
                        ai_data = analyze_text_with_gemini(active_api_key, extracted_text_to_analyze)
                        if ai_data:
                            if ai_data.get("kaufpreis"): st.session_state["kaufpreis"] = float(ai_data["kaufpreis"])
                            if ai_data.get("wohnflaeche"): 
                                st.session_state["qm"] = float(ai_data["wohnflaeche"])
                            if ai_data.get("baujahr"): 
                                st.session_state["baujahr"] = int(ai_data["baujahr"])
                                update_smart_defaults()
                            
                            qm_val = st.session_state.get("qm", 0.0)
                            if ai_data.get("ist_miete_monat"):
                                monat_val = float(ai_data["ist_miete_monat"])
                                st.session_state["ist_miete_monat"] = monat_val
                                st.session_state["target_miete_monat"] = monat_val
                                if qm_val > 0:
                                    st.session_state["ist_sqm"] = monat_val / qm_val
                                    st.session_state["target_sqm"] = monat_val / qm_val
                            elif ai_data.get("ist_miete_sqm"): 
                                sqm_val = float(ai_data["ist_miete_sqm"])
                                st.session_state["ist_sqm"] = sqm_val
                                st.session_state["target_sqm"] = sqm_val
                                if qm_val > 0:
                                    st.session_state["ist_miete_monat"] = sqm_val * qm_val
                                    st.session_state["target_miete_monat"] = sqm_val * qm_val
                                    
                            if ai_data.get("hausgeld_monat"): st.session_state["hausgeld"] = float(ai_data["hausgeld_monat"])
                            if ai_data.get("bundesland") and str(ai_data["bundesland"]) in GRUNDERWERBSTEUER_MAP: 
                                st.session_state["bundesland"] = str(ai_data["bundesland"])
                                update_grwt_from_bundesland()
                            if ai_data.get("stadt") and str(ai_data["stadt"]) != "Unbekannt": st.session_state["stadt"] = str(ai_data["stadt"])
                            if ai_data.get("stadtteil") and str(ai_data["stadtteil"]) != "Unbekannt": st.session_state["stadtteil"] = str(ai_data["stadtteil"])
                            if ai_data.get("objektart") and str(ai_data["objektart"]) in OBJEKTARTEN: 
                                st.session_state["objektart"] = str(ai_data["objektart"])
                                update_smart_defaults()
                            if ai_data.get("objektname") and str(ai_data["objektname"]) != "Unbekannt": st.session_state["obj_name"] = str(ai_data["objektname"])
                            st.success("Objektdaten erfolgreich übernommen.")
                            st.rerun()

        st.divider()
        st.markdown("### Parametrisierung")
        
        with st.expander("1. Objektdaten (Exposé)", expanded=True):
            st.text_input("Objektbezeichnung", key="obj_name", placeholder="z. B. Mehrfamilienhaus Bonn")
            st.selectbox("Objektart / Typ", OBJEKTARTEN, key="objektart", on_change=update_smart_defaults)
            
            st.selectbox("Bundesland", list(GRUNDERWERBSTEUER_MAP.keys()), key="bundesland", on_change=update_grwt_from_bundesland)
            
            c_loc1, c_loc2 = st.columns(2)
            c_loc1.text_input("Stadt", key="stadt", placeholder="z. B. Hannover")
            c_loc2.text_input("Stadtteil", key="stadtteil", placeholder="z. B. List")
            
            st.number_input("Kaufpreis (€) *", key="kaufpreis", step=5000.0, format="%.2f")
            st.number_input("Wohnfläche (m²) *", key="qm", step=5.0, format="%.2f", on_change=update_qm_callback)
            st.number_input("Baujahr", key="baujahr", step=1, on_change=update_smart_defaults)
            
            st.markdown("---")
            st.markdown("**Mieteinnahmen (IST)**")
            col_m1, col_m2 = st.columns(2)
            
            col_m1.number_input("Gesamtkaltmiete (€/Monat)", key="ist_miete_monat", step=50.0, format="%.2f", on_change=update_ist_from_monat)
            col_m2.number_input("Kaltmiete (€/m²)", key="ist_sqm", step=0.50, format="%.2f", on_change=update_ist_from_sqm)

            st.markdown("---")
            st.number_input(
                "Hausgeld gesamt (€/Monat)", 
                key="hausgeld", 
                step=10.0, 
                format="%.2f",
                help="Falls keine spezifische Aufteilung eingetragen wird, nimmt die Berechnung automatisch an, dass 75 % umlegbare Betriebskosten und 25 % nicht umlegbare Kosten sind."
            )
            
            with st.expander("⚙️ Hausgeld-Aufteilung anpassen", expanded=(st.session_state.get("hausgeld_nicht_umlegbar", 0.0) > 0)):
                st.number_input(
                    "Davon nicht umlegbar (€/Monat)", 
                    key="hausgeld_nicht_umlegbar", 
                    step=5.0, 
                    format="%.2f"
                )

            st.number_input("Sanierungsaufwand (€)", key="sanierung", step=2500.0, format="%.2f")

        with st.expander("2. Finanzierung & Nebenkosten", expanded=True):
            st.markdown("**Kaufnebenkosten**")
            
            c_nk1, c_nk2 = st.columns(2)
            grwt_val = c_nk1.number_input("1. Grunderwerbsteuer (%)", key="grwt_p", step=0.1, format="%.2f")
            notar_val = c_nk2.number_input("2. Notar & Grundbuch (%)", key="notar_p", step=0.1, format="%.2f")
            
            kp_val = st.session_state["kaufpreis"]
            grwt_euro = kp_val * (grwt_val / 100)
            notar_euro = kp_val * (notar_val / 100)
            
            c_nk1.markdown(f'<div class="nk-sub-badge">{fmt_eur(grwt_euro)}</div>', unsafe_allow_html=True)
            c_nk2.markdown(f'<div class="nk-sub-badge">{fmt_eur(notar_euro)}</div>', unsafe_allow_html=True)

            c_nk3, c_nk4 = st.columns(2)
            makler_val = c_nk3.number_input("3. Maklerprovision (%)", key="makler_p", step=0.1, format="%.2f")
            sonst_nk_val = c_nk4.number_input("4. Sonst. Nebenkosten (€)", key="sonst_nk", step=250.0, format="%.2f")
            
            makler_euro = kp_val * (makler_val / 100)
            tot_nebenkosten = grwt_euro + notar_euro + makler_euro + sonst_nk_val
            
            c_nk3.markdown(f'<div class="nk-sub-badge">{fmt_eur(makler_euro)}</div>', unsafe_allow_html=True)
            c_nk4.markdown(f'<div class="nk-sub-badge">{fmt_eur(sonst_nk_val)}</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="nk-total-badge"><span>Summe Kaufnebenkosten:</span><span>{fmt_eur(tot_nebenkosten)}</span></div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("**Bank-Kredit & Zinsen**")
            st.selectbox(
                "Darlehensart",
                ["Annuitätendarlehen", "Tilgungsdarlehen", "Endfälliges Darlehen"],
                key="loan_type"
            )
            st.number_input("Hausbank Zins (%)", key="hb_zins", step=0.1, format="%.2f")
            st.number_input("Hausbank Tilgung (%)", key="hb_tilg", step=0.1, format="%.2f")
            st.number_input("Tilgungsfreie Jahre", key="grace_years", min_value=0, max_value=5)
            
            with st.expander("🏛️ KfW-Darlehen (Optional)", expanded=(st.session_state.get("kfw_amt", 0.0) > 0)):
                st.number_input("KfW Darlehen (€)", key="kfw_amt", step=10000.0, format="%.2f")
                c_kfw1, c_kfw2 = st.columns(2)
                c_kfw1.number_input("KfW Zins (%)", key="kfw_zins", step=0.1, format="%.2f")
                c_kfw2.number_input("KfW Tilgung (%)", key="kfw_tilg", step=0.1, format="%.2f")
                st.number_input("KfW tilgungsfreie Jahre", key="kfw_grace_years", min_value=0, max_value=10, step=1)

            st.markdown("---")
            st.markdown("**Eigenkapital**")
            
            if st.session_state.get("ek_euro", 0.0) == 0.0 and tot_nebenkosten > 0:
                st.session_state["ek_euro"] = float(tot_nebenkosten)
                
            ek_input = st.number_input("Eingesetztes Eigenkapital (€)", key="ek_euro", step=2500.0, format="%.2f")
            
            est_tot_inv = kp_val + tot_nebenkosten + st.session_state["sanierung"]
            calculated_quote = (ek_input / est_tot_inv * 100) if est_tot_inv > 0 else 0.0
            
            st.caption(f"💡 Standardmäßig sind die Kaufnebenkosten (**{fmt_eur(tot_nebenkosten)}**) als Eigenkapital-Richtwert hinterlegt. Rechnerische EK-Quote: **{fmt_pct(calculated_quote)}**.")

        with st.expander("3. Zielmiete & Bewirtschaftung", expanded=False):
            st.markdown("**Zielmiete (Soll-Miete)**")
            
            if st.session_state.get("target_sqm", 0.0) == 0.0 and st.session_state.get("ist_sqm", 0.0) > 0 and st.session_state.get("target_auto_sync", True):
                st.session_state["target_sqm"] = st.session_state["ist_sqm"]
                st.session_state["target_miete_monat"] = st.session_state["ist_miete_monat"]

            col_zt1, col_zt2 = st.columns(2)
            col_zt1.number_input("Zielkaltmiete (€/Monat)", key="target_miete_monat", step=50.0, format="%.2f", on_change=update_target_from_monat)
            col_zt2.number_input("Zielkaltmiete (€/m²)", key="target_sqm", step=0.50, format="%.2f", on_change=update_target_from_sqm)
            
            st.number_input("Anpassung in Jahr", key="adj_year", min_value=1, max_value=10)
            
            st.markdown("---")
            curr_bj = st.session_state.get("baujahr", 2000)
            curr_obj = st.session_state.get("objektart", "Eigentumswohnung")
            smart_inst, smart_mgt, smart_vac = get_smart_defaults(curr_bj, curr_obj)

            st.markdown("**Bewirtschaftung & Rücklagen**")
            st.number_input("Instandhaltung (€/m²/Jahr)", key="inst_sqm", step=1.0, format="%.2f")
            st.number_input("Verwaltung (€/Monat)", key="mgt_monat", step=5.0, format="%.2f")
            st.slider("Leerstandsquote (%)", 0.0, 10.0, key="vac_rate_pct", step=0.5, format="%.1f %%")

        with st.expander("4. Steuern & Makro-Annahmen", expanded=False):
            st.slider("Grenzsteuersatz (%)", 0.0, 50.0, key="tax_rate_pct", step=1.0, format="%.1f %%")
            st.selectbox("AfA-Modell", ["1_Linear_Standard", "2_Degressiv_§7_5a", "3_Sonder_AfA_§7b", "4_Denkmal_§7h_7i"], key="afa_model")
            st.number_input("Mietsteigerung p.a. (%)", key="miet_inc", step=0.1, format="%.2f")
            st.number_input("Wertsteigerung p.a. (%)", key="val_inc", step=0.1, format="%.2f")

        st.divider()
        if st.button("🚀 Analyse starten / aktualisieren", type="primary", use_container_width=True):
            st.session_state["trigger_analysis"] = True
            st.rerun()

    target_sqm_resolved = st.session_state["target_sqm"] if st.session_state["target_sqm"] > 0 else st.session_state["ist_sqm"]

    input_data = {
        'kaufpreis': st.session_state["kaufpreis"], 'sanierung': st.session_state["sanierung"],
        'bundesland': st.session_state["bundesland"], 'stadt': st.session_state["stadt"], 'stadtteil': st.session_state["stadtteil"],
        'objektart': st.session_state["objektart"],
        'grwt_proz': st.session_state["grwt_p"] / 100,
        'notar_proz': st.session_state["notar_p"] / 100, 'makler_proz': st.session_state["makler_p"] / 100, 'sonst_nk': st.session_state["sonst_nk"],
        'disagio_proz': st.session_state["disagio_p"] / 100, 'ek_euro': st.session_state["ek_euro"],
        'ek_quote': st.session_state["ek_quote"],
        'loan_type': st.session_state["loan_type"],
        'hb_zins': st.session_state["hb_zins"] / 100,
        'hb_tilg': st.session_state["hb_tilg"] / 100, 'grace_years': st.session_state["grace_years"],
        'kfw_amt': st.session_state["kfw_amt"], 'kfw_zins': st.session_state["kfw_zins"] / 100,
        'kfw_tilg': st.session_state["kfw_tilg"] / 100, 'kfw_grace_years': st.session_state["kfw_grace_years"], 'kfw_grant': st.session_state["kfw_grant"],
        'sondertilg': st.session_state["sondertilg"], 'ist_sqm': st.session_state["ist_sqm"],
        'target_sqm': target_sqm_resolved, 
        'adj_year': st.session_state["adj_year"],
        'park': st.session_state["park"], 'vac_rate': st.session_state["vac_rate_pct"] / 100,
        'qm': st.session_state["qm"], 'hausgeld': st.session_state["hausgeld"],
        'hausgeld_nicht_umlegbar': st.session_state["hausgeld_nicht_umlegbar"],
        'inst_sqm': st.session_state["inst_sqm"], 'mgt_monat': st.session_state["mgt_monat"],
        'capex_j3': st.session_state["capex_j3"], 'capex_j6': st.session_state["capex_j6"],
        'tax_rate': st.session_state["tax_rate_pct"] / 100, 'afa_model': st.session_state["afa_model"],
        'afa_lin': st.session_state["afa_lin"] / 100, 'miet_inc': st.session_state["miet_inc"] / 100,
        'cost_inc': st.session_state["cost_inc"] / 100, 'val_inc': st.session_state["val_inc"] / 100,
        'wacc': st.session_state["wacc"] / 100, 'exit_cost': st.session_state["exit_cost"] / 100,
        'grund_anteil': st.session_state["grund_anteil"]
    }

    if not st.session_state.get("trigger_analysis", False):
        st.markdown("""
        <div class="valuon-placeholder">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #13381A; margin-bottom: 10px;">Berechnung ausführen</h2>
            <p style="font-size: 1.05rem; color: #555759; max-width: 620px; margin: 0 auto 15px auto;">
                Tragen Sie Ihre Objektdaten in der Seitenleiste ein und klicken Sie unten auf <b>"🚀 Analyse starten"</b>, um das Dashboard zu erzeugen.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.image(
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
            use_container_width=True
        )
    else:
        missing_fields = []
        if st.session_state["kaufpreis"] <= 0:
            missing_fields.append("Kaufpreis (€)")
        if st.session_state["qm"] <= 0:
            missing_fields.append("Wohnfläche (m²)")
        if st.session_state["ist_sqm"] <= 0:
            missing_fields.append("Mieteinnahmen (€)")

        if missing_fields:
            missing_str = ", ".join([f"<b>{f}</b>" for f in missing_fields])
            st.error(f"⚠️ Bitte vervollständigen Sie vor der Analyse folgende Pflichtfelder: {missing_str}")
        else:
            col_hor1, col_hor2 = st.columns([2, 2])
            horizon_choice = col_hor1.selectbox(
                "Projektionshorizont:",
                ["10 Jahre (Standard)", "Bis zur vollen Abzahlung des Darlehens (Volltilgung)"],
                key="horizon_choice"
            )
            full_rep = ("Volltilgung" in horizon_choice)

            df_proj, tot_inv, ek_abs, fk_tot, irr, afa_base, ek_quote_calc = calc_projection(input_data, full_repayment=full_rep)

            sanity_warnings = check_input_sanity(input_data)
            if sanity_warnings:
                for w in sanity_warnings:
                    st.warning(f"⚠️ **Plausibilitäts-Hinweis:** {w}")

            obj_display_name = st.session_state['obj_name'] if st.session_state['obj_name'] else "Unbenanntes Objekt"
            
            loc_str = st.session_state['stadt']
            if st.session_state['stadtteil']:
                loc_str += f" ({st.session_state['stadtteil']})"
            if loc_str:
                loc_str += f", {st.session_state['bundesland']}"
            else:
                loc_str = st.session_state['bundesland']

            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                st.markdown(f"# {obj_display_name}")
                st.caption(f"Typ: {st.session_state['objektart']} | Standort: {loc_str} | Fläche: {fmt_sqm(st.session_state['qm'])} | Kaufpreis: {fmt_eur(st.session_state['kaufpreis'])} | Eigenkapital: {fmt_eur(ek_abs)} ({fmt_pct(ek_quote_calc*100)})")
            with col_t2:
                current_payload = {k: st.session_state[k] for k in default_state.keys()}
                if sb_client and st.button("In Cloud speichern", type="primary", use_container_width=True):
                    db_save_project(sb_client, st.session_state["user_email"], obj_display_name, current_payload)

            strat_name = st.session_state.get("selected_strategy_name", "Konservativ / Ausgewogen (Standard)")
            strat = STRATEGIES.get(strat_name, STRATEGIES["Konservativ / Ausgewogen (Standard)"])
            
            val_cf = df_proj.loc[0, 'CF n. St.'] / 12
            val_rendite = df_proj.loc[0, 'Bruttomietrendite'] * 100
            val_roe = (df_proj.loc[0, 'CF n. St.'] / ek_abs) * 100 if ek_abs > 0 else 0.0
            
            kfw_amt_val = max(0, st.session_state["kfw_amt"] - st.session_state["kfw_grant"])
            hb_loan_val = max(0.0, fk_tot - kfw_amt_val)
            hb_annu = hb_loan_val * ((st.session_state["hb_zins"] + st.session_state["hb_tilg"]) / 100)
            kfw_annu = kfw_amt_val * ((st.session_state["kfw_zins"] + st.session_state["kfw_tilg"]) / 100)
            val_dscr = df_proj.loc[0, 'NOI'] / (hb_annu + kfw_annu) if (hb_annu + kfw_annu) > 0 else 1.0

            status_cf, label_cf = get_metric_status(val_cf, strat["target_cf"], strat["tol_cf"])
            status_rendite, label_rendite = get_metric_status(val_rendite, strat["target_rendite"], strat["tol_rendite"])
            status_roe, label_roe = get_metric_status(val_roe, strat["target_roe"], strat["tol_roe"])
            status_dscr, label_dscr = get_metric_status(val_dscr, strat["target_dscr"], strat["tol_dscr"])

            c1, c2, c3, c4 = st.columns(4)
            
            c1.markdown(f'''
            <div class="metric-card metric-{status_cf}">
                <div class="metric-header">
                    <span class="metric-title">Cashflow (netto)</span>
                    <div class="tooltip-container">
                        <span class="tooltip-icon">i</span>
                        <div class="tooltip-box">
                            <strong>Bedeutung & Relevanz</strong>
                            Monatlicher Überschuss nach Abzug aller Bewirtschaftungskosten, Kreditraten und Steuern.
                        </div>
                    </div>
                </div>
                <div class="metric-value">{fmt_de(val_cf, 2)} €/M</div>
                <div class="metric-status">{label_cf}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            c2.markdown(f'''
            <div class="metric-card metric-{status_rendite}">
                <div class="metric-header">
                    <span class="metric-title">Bruttomietrendite</span>
                    <div class="tooltip-container">
                        <span class="tooltip-icon">i</span>
                        <div class="tooltip-box">
                            <strong>Bedeutung & Relevanz</strong>
                            Verhältnis der jährlichen Bruttokaltmiete zum Kaufpreis.
                        </div>
                    </div>
                </div>
                <div class="metric-value">{fmt_pct(val_rendite)}</div>
                <div class="metric-status">{label_rendite}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            c3.markdown(f'''
            <div class="metric-card metric-{status_roe}">
                <div class="metric-header">
                    <span class="metric-title">Eigenkapitalrendite</span>
                    <div class="tooltip-container">
                        <span class="tooltip-icon">i</span>
                        <div class="tooltip-box">
                            <strong>Bedeutung & Relevanz</strong>
                            Prozentuale Verzinsung Ihres eingebrachten Eigenkapitals.
                        </div>
                    </div>
                </div>
                <div class="metric-value">{fmt_pct(val_roe)}</div>
                <div class="metric-status">{label_roe}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            c4.markdown(f'''
            <div class="metric-card metric-{status_dscr}">
                <div class="metric-header">
                    <span class="metric-title">DSCR Schuldendienst</span>
                    <div class="tooltip-container">
                        <span class="tooltip-icon">i</span>
                        <div class="tooltip-box">
                            <strong>Bedeutung & Relevanz</strong>
                            Debt Service Coverage Ratio: Verhältnis des NOI zum jährlichen Schuldendienst.
                        </div>
                    </div>
                </div>
                <div class="metric-value">{fmt_de(val_dscr, 2)}</div>
                <div class="metric-status">{label_dscr}</div>
            </div>
            ''', unsafe_allow_html=True)

            tab_dash, tab_plan = st.tabs(["Executive Dashboard", "Liquiditätsverlauf & Tilgung"])

            with tab_dash:
                col_chart1, col_chart2 = st.columns([2, 1])
                with col_chart1:
                    st.markdown("### Portfolio & Wertentwicklung")
                    
                    # CHART VIEW DROPDOWN SELECTOR FOR THE USER
                    chart_mode = st.selectbox(
                        "Grafik-Ansicht wählen:",
                        [
                            "1. Vermögensstruktur & NAV (Netto-Eigenkapital)",
                            "2. Cashflow-Entwicklung (Vor & Nach Steuern)",
                            "3. Kapitaldienst (Zins- & Tilgungsverlauf)"
                        ],
                        key="chart_mode_select",
                        label_visibility="collapsed"
                    )
                    
                    fig = go.Figure()
                    
                    if "1." in chart_mode:
                        fig.add_trace(go.Scatter(
                            x=df_proj['Jahr'], y=df_proj['Objektwert'], 
                            name="Objektwert", 
                            line=dict(color="#13381A", width=3),
                            hovertemplate="<b>Jahr %{x}</b><br>Objektwert: %{y:,.0f} €<extra></extra>"
                        ))
                        fig.add_trace(go.Scatter(
                            x=df_proj['Jahr'], y=df_proj['Restschuld'], 
                            name="Restschuld", 
                            line=dict(color="#8b3a2b", width=3),
                            hovertemplate="<b>Jahr %{x}</b><br>Restschuld: %{y:,.0f} €<extra></extra>"
                        ))
                        fig.add_trace(go.Bar(
                            x=df_proj['Jahr'], y=df_proj['NAV'], 
                            name="Netto-Eigenkapital (NAV)", 
                            marker_color="#A37841", opacity=0.85,
                            hovertemplate="<b>Jahr %{x}</b><br>NAV: %{y:,.0f} €<extra></extra>"
                        ))
                        fig.update_layout(barmode='group')
                        
                    elif "2." in chart_mode:
                        fig.add_trace(go.Bar(
                            x=df_proj['Jahr'], y=df_proj['CF v. St.'], 
                            name="Cashflow vor Steuern", 
                            marker_color="#13381A",
                            hovertemplate="<b>Jahr %{x}</b><br>CF vor Steuern: %{y:,.0f} €<extra></extra>"
                        ))
                        fig.add_trace(go.Bar(
                            x=df_proj['Jahr'], y=df_proj['CF n. St.'], 
                            name="Cashflow nach Steuern", 
                            marker_color="#A37841",
                            hovertemplate="<b>Jahr %{x}</b><br>CF nach Steuern: %{y:,.0f} €<extra></extra>"
                        ))
                        fig.update_layout(barmode='group')
                        
                    else:
                        fig.add_trace(go.Bar(
                            x=df_proj['Jahr'], y=df_proj['Zinsen'], 
                            name="Zinsaufwand", 
                            marker_color="#8b3a2b",
                            hovertemplate="<b>Jahr %{x}</b><br>Zinsen: %{y:,.0f} €<extra></extra>"
                        ))
                        fig.add_trace(go.Bar(
                            x=df_proj['Jahr'], y=df_proj['Tilgung'], 
                            name="Tilgungsleistung", 
                            marker_color="#13381A",
                            hovertemplate="<b>Jahr %{x}</b><br>Tilgung: %{y:,.0f} €<extra></extra>"
                        ))
                        fig.update_layout(barmode='stack')

                    fig.update_layout(
                        template="plotly_white", 
                        height=350, 
                        margin=dict(l=10, r=10, t=10, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        yaxis=dict(tickformat=",.0f", ticksuffix=" €")
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                with col_chart2:
                    st.markdown("### Kapitalstruktur")
                    fig_pie = px.pie(
                        names=['Eigenkapital', 'Hausbank', 'KfW'],
                        values=[ek_abs, hb_loan_val, kfw_amt_val],
                        color_discrete_sequence=['#13381A', '#2B2D2F', '#A37841'],
                        hole=0.5
                    )
                    fig_pie.update_traces(hovertemplate="<b>%{label}</b><br>Anteil: %{value:,.0f} € (%{percent})<extra></extra>")
                    fig_pie.update_layout(height=390, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_pie, use_container_width=True)

            with tab_plan:
                st.markdown(f"### Liquiditätsverlauf ({len(df_proj)} Jahre)")
                st.dataframe(df_proj.style.format({
                    "Bruttomietrendite": lambda x: fmt_pct(x*100),
                    "Brutto-Kaltmiete": lambda x: fmt_eur(x),
                    "NOI": lambda x: fmt_eur(x),
                    "Zinsen": lambda x: fmt_eur(x),
                    "Tilgung": lambda x: fmt_eur(x),
                    "CF v. St.": lambda x: fmt_eur(x),
                    "AfA": lambda x: fmt_eur(x),
                    "Steuer": lambda x: fmt_eur(x),
                    "CF n. St.": lambda x: fmt_eur(x),
                    "Restschuld": lambda x: fmt_eur(x),
                    "Objektwert": lambda x: fmt_eur(x),
                    "NAV": lambda x: fmt_eur(x),
                    "LTV": lambda x: fmt_pct(x*100, 1)
                }), use_container_width=True)

# =============================================================================
# MODUL 3: DEAL-VERGLEICH
# =============================================================================
elif nav_choice == "Vergleich":
    st.markdown("## Multi-Deal Vergleich")
    st.markdown("<p style='color:#555759;'>Parallele Gegenüberstellung mehrerer Investitionsvorhaben.</p>", unsafe_allow_html=True)
    st.info("🚀 **Coming Soon:** Dieses Modul befindet sich aktuell in der Entwicklung.")

# =============================================================================
# MODUL 4: MAXIMALER KAUFPREIS
# =============================================================================
elif nav_choice == "Kaufpreis":
    st.markdown("## Maximaler Kaufpreis-Rechner")
    st.markdown("<p style='color:#555759;'>Ermittlung der strategischen Gebots-Obergrenze.</p>", unsafe_allow_html=True)
    st.info("🚀 **Coming Soon:** Dieses Modul befindet sich aktuell in der Entwicklung.")

# =============================================================================
# MODUL 5: IMMOBILIENWISSEN
# =============================================================================
elif nav_choice == "Immobilienwissen":
    st.markdown("## Immobilienwissen & Investment-Guide")
    st.markdown("<p style='color:#555759;'>Fundiertes Know-how, Kennzahlen-Erklärungen und Schutz vor typischen Investor-Fehlern.</p>", unsafe_allow_html=True)

    w_tab1, w_tab2, w_tab3 = st.tabs(["Indikatoren & KPIs", "Die 5 häufigsten Fehler", "Investment-Grundsätze"])

    with w_tab1:
        st.markdown("### Die wichtigsten Kennzahlen im Überblick")
        
        with st.expander("📌 Cashflow (netto nach Steuern)", expanded=True):
            st.markdown("""
            **Was ist das?**  
            Der Netto-Cashflow ist das Geld, das am Monatsende nach Abzug *aller* Kosten übrig bleibt.
            """)

        with st.expander("📌 Bruttomietrendite vs. Nettomietrendite"):
            st.markdown("""
            **Was ist das?**  
            Die Rendite setzt den jährlichen Ertrag ins Verhältnis zum Kaufpreis.
            """)

    with w_tab2:
        st.markdown("### Die 5 teuersten Anfängerfehler")
        st.error("**Fehler 1: Hausgeld nicht in umlegbar & nicht umlegbar trennen**")

    with w_tab3:
        st.markdown("### Fundamentale Investment-Regeln")
        st.markdown("#### 1. Der Eigenkapital-Hebel (Leverage-Effekt)")

# =============================================================================
# MODUL 6: EINSTELLUNGEN
# =============================================================================
elif nav_choice == "Einstellungen":
    st.markdown("## System & Konfiguration")
    st.markdown("<p style='color:#555759;'>Verwaltung von API-Schnittstellen und Investment-Strategien.</p>", unsafe_allow_html=True)

    tab_s1, tab_s2 = st.tabs(["Schnittstellen", "Strategie-Parameter"])

    with tab_s1:
        st.markdown("### Google Gemini API-Schlüssel")
        gem_secrets = st.secrets.get("GEMINI_API_KEY", "")
        if gem_secrets:
            masked_key = gem_secrets[:6] + "..." + gem_secrets[-4:] if len(gem_secrets) > 10 else "Aktiv"
            st.success(f"API-Key aktiv geladen über Secrets (`{masked_key}`)")
        else:
            st.warning("Kein API-Schlüssel in den Secrets hinterlegt.")
        
        gemini_key = st.text_input("Manueller Override", value=st.session_state.get("gemini_api_key", ""), type="password")
        if gemini_key:
            st.session_state["gemini_api_key"] = gemini_key
            st.success("API-Schlüssel zwischengespeichert.")

        st.divider()
        st.markdown("### Supabase Datenanbindung")
        sb_u_secrets = st.secrets.get("SUPABASE_URL", "")
        if sb_u_secrets:
            st.success("Supabase-Datenbank erfolgreich über Secrets verbunden.")
            
        sb_u = st.text_input("Supabase URL", value=st.session_state.get("supabase_url", ""), type="password")
        sb_k = st.text_input("Supabase Anon Key", value=st.session_state.get("supabase_key", ""), type="password")
        if sb_u and sb_k:
            st.session_state["supabase_url"] = sb_u
            st.session_state["supabase_key"] = sb_k
            st.success("Verbindungsparameter aktualisiert.")

    with tab_s2:
        st.markdown("### Investment-Profil")
        chosen_strat = st.selectbox("Aktive Strategie", list(STRATEGIES.keys()), index=0)
        st.session_state["selected_strategy_name"] = chosen_strat
        st.json(STRATEGIES[chosen_strat])
