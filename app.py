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

    section[data-testid="stSidebar"] {
        width: 400px !important;
        min-width: 400px !important;
    }

    section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
        min-height: 42px !important;
        display: flex !important;
        align-items: flex-end !important;
        margin-bottom: 4px !important;
    }

    div[data-testid="InputInstructions"], 
    .stInputInstructions, 
    div[aria-live="polite"] {
        display: none !important;
    }
    
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
    "Eigentumswohnung", "Einfamilienhaus", "Zweifamilienhaus",
    "Reihenhaus / Doppelhaushälfte", "Mehrfamilienhaus",
    "Wohn- und Geschäftshaus", "Mikroapartment / Studentisches Wohnen",
    "Pflege- / Seniorenimmobilie", "Gewerbeimmobilie / Sonstiges"
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
    st.session_state["ist_sqm"] = (monat / qm) if qm > 0 else 0.0
    if st.session_state.get("target_auto_sync", True):
        st.session_state["target_miete_monat"] = monat
        st.session_state["target_sqm"] = st.session_state["ist_sqm"]

def update_ist_from_sqm():
    qm = st.session_state.get("qm", 0.0)
    sqm_val = st.session_state.get("ist_sqm", 0.0)
    st.session_state["ist_miete_monat"] = (sqm_val * qm) if qm > 0 else 0.0
    if st.session_state.get("target_auto_sync", True):
        st.session_state["target_miete_monat"] = st.session_state["ist_miete_monat"]
        st.session_state["target_sqm"] = sqm_val

def update_target_from_monat():
    qm = st.session_state.get("qm", 0.0)
    monat = st.session_state.get("target_miete_monat", 0.0)
    st.session_state["target_sqm"] = (monat / qm) if qm > 0 else 0.0
    st.session_state["target_auto_sync"] = False

def update_target_from_sqm():
    qm = st.session_state.get("qm", 0.0)
    sqm_val = st.session_state.get("target_sqm", 0.0)
    st.session_state["target_miete_monat"] = (sqm_val * qm) if qm > 0 else 0.0
    st.session_state["target_auto_sync"] = False

def update_qm_callback():
    qm = st.session_state.get("qm", 0.0)
    if qm > 0:
        monat = st.session_state.get("ist_miete_monat", 0.0)
        if monat > 0:
            st.session_state["ist_sqm"] = monat / qm
        if st.session_state.get("target_auto_sync", True):
            st.session_state["target_miete_monat"] = monat
            st.session_state["target_sqm"] = monat / qm

# -----------------------------------------------------------------------------
# SECRETS & BULLETPROOF STORAGE (SUPABASE + LOCAL SESSION FALLBACK)
# -----------------------------------------------------------------------------
def get_gemini_api_key() -> str:
    return st.secrets.get("GEMINI_API_KEY", "") or st.session_state.get("gemini_api_key", "")

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
    # 1. Foolproof local backup in session state
    if "local_projects" not in st.session_state:
        st.session_state["local_projects"] = []
    
    existing_local = next((p for p in st.session_state["local_projects"] if p["project_name"] == project_name), None)
    if existing_local:
        existing_local["input_data"] = payload
    else:
        st.session_state["local_projects"].append({
            "id": f"local_{len(st.session_state['local_projects'])+1}",
            "user_id": user_id,
            "project_name": project_name,
            "input_data": payload
        })

    # 2. Try Supabase cloud sync
    if not supabase:
        st.success(f"Projekt '{project_name}' lokal gespeichert (Keine Cloud-Konfiguration aktiv).")
        return

    try:
        res = supabase.table("projects").select("id").eq("user_id", user_id).eq("project_name", project_name).execute()
        if res.data and len(res.data) > 0:
            pid = res.data[0]["id"]
            supabase.table("projects").update({"input_data": payload}).eq("id", pid).execute()
            st.success(f"Projekt '{project_name}' erfolgreich in Cloud & lokal gespeichert.")
        else:
            supabase.table("projects").insert({
                "user_id": user_id,
                "project_name": project_name,
                "input_data": payload
            }).execute()
            st.success(f"Projekt '{project_name}' erfolgreich in Cloud & lokal gespeichert.")
    except Exception as e:
        st.warning(f"⚠️ Cloud-Speicherung fehlgeschlagen (Supabase-Pfad/Schema-Fehler): {e}. Das Projekt wurde sicher **lokal** gespeichert, sodass du verlustfrei weiterarbeiten kannst!")

def db_get_projects(supabase: Client, user_id: str):
    cloud_projects = []
    if supabase:
        try:
            res = supabase.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            cloud_projects = res.data or []
        except Exception:
            pass
            
    local_projects = st.session_state.get("local_projects", [])
    
    seen = set()
    combined = []
    for p in cloud_projects:
        name = p.get("project_name")
        if name not in seen:
            seen.add(name)
            combined.append(p)
    for p in local_projects:
        name = p.get("project_name")
        if name not in seen:
            seen.add(name)
            combined.append(p)
    return combined

def db_delete_project(supabase: Client, project_id):
    # Remove from local if present
    if "local_projects" in st.session_state:
        st.session_state["local_projects"] = [p for p in st.session_state["local_projects"] if str(p.get("id")) != str(project_id)]
    
    if supabase and not str(project_id).startswith("local_"):
        try:
            supabase.table("projects").delete().eq("id", project_id).execute()
        except Exception:
            pass
    st.success("Projekt gelöscht.")

# -----------------------------------------------------------------------------
# SANITY CHECK & PROJECTION
# -----------------------------------------------------------------------------
def check_input_sanity(d: dict) -> list:
    warnings = []
    if d['hb_zins'] > 0.15:
        warnings.append(f"Zinssatz Hausbank ({fmt_pct(d['hb_zins']*100)}) ist ungewöhnlich hoch. Vertippt?")
    if d['kfw_zins'] > 0.15:
        warnings.append(f"Zinssatz KfW ({fmt_pct(d['kfw_zins']*100)}) ist sehr hoch angesetzt.")
    if d['tax_rate'] > 0.50:
        warnings.append(f"Grenzsteuersatz ({fmt_pct(d['tax_rate']*100)}) liegt über dem Höchstsatz.")
    return warnings

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
    eff_nicht_umlegbar = (hausgeld_tot * 0.25) if (hausgeld_tot > 0 and hausgeld_nu <= 0) else hausgeld_nu
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
            current_sqm_rent = data['target_sqm'] if yr == data['adj_year'] else current_sqm_rent * (1 + data['miet_inc'])
        
        gross_rent = (current_sqm_rent * data['qm'] + data['park']) * 12
        net_rent = gross_rent * (1 - data['vac_rate'])
        op_costs = (annual_nu_hausgeld + (data['inst_sqm'] * data['qm']) + (data['mgt_monat'] * 12)) * ((1 + data['cost_inc']) ** (yr - 1))
        capex = data['capex_j3'] if yr == 3 else (data['capex_j6'] if yr == 6 else 0)
        noi = net_rent - op_costs - capex
        
        zins_hb = restschuld_hb * data['hb_zins'] if restschuld_hb > 0 else 0.0
        tilg_hb = 0.0
        if restschuld_hb > 0 and yr > data['grace_years']:
            if loan_type == "Annuitätendarlehen":
                tilg_hb = max(0.0, min(restschuld_hb, hb_initial_annuity - zins_hb))
            elif loan_type == "Tilgungsdarlehen":
                tilg_hb = min(restschuld_hb, hb_loan * data['hb_tilg'])
            else:
                tilg_hb = restschuld_hb if (yr == max_yr or (not full_repayment and yr == 10)) else 0.0
                
        zins_kfw = restschuld_kfw * data['kfw_zins'] if (kfw_loan > 0 and restschuld_kfw > 0) else 0.0
        tilg_kfw = 0.0
        if kfw_loan > 0 and restschuld_kfw > 0 and yr > data.get('kfw_grace_years', 0):
            if loan_type == "Endfälliges Darlehen":
                tilg_kfw = restschuld_kfw if (yr == max_yr or (not full_repayment and yr == 10)) else 0.0
            else:
                tilg_kfw = max(0.0, min(restschuld_kfw, kfw_initial_annuity - zins_kfw))
                
        zins_tot = zins_hb + zins_kfw
        actual_sondertilg = min(restschuld_hb, data['sondertilg']) if (restschuld_hb > 0 and yr > data.get('grace_years', 0)) else 0.0
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
            
        taxable_inc = noi - zins_tot - afa_val - (disagio_betrag if yr == 1 else 0) - (san if (yr == 1 and san <= afa_base * 0.15) else 0)
        tax_val = taxable_inc * data['tax_rate']
        cf_n_st = cf_v_st - tax_val
        
        restschuld_hb = max(0.0, restschuld_hb - tilg_hb - actual_sondertilg)
        restschuld_kfw = max(0.0, restschuld_kfw - tilg_kfw)
        restschuld_tot = restschuld_hb + restschuld_kfw
        
        obj_val *= (1 + data['val_inc'])
        nav = obj_val - restschuld_tot
        
        rows.append({
            "Jahr": yr, "Bruttomietrendite": gross_rent / kp if kp > 0 else 0,
            "Brutto-Kaltmiete": gross_rent, "NOI": noi, "Zinsen": zins_tot,
            "Tilgung": tilg_tot, "CF v. St.": cf_v_st, "AfA": afa_val,
            "Steuer": tax_val, "CF n. St.": cf_n_st, "Restschuld": restschuld_tot,
            "Objektwert": obj_val, "NAV": nav, "LTV": restschuld_tot / obj_val if obj_val > 0 else 0
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

def get_metric_status(val, tg, ty):
    return ("green", "Zielwert erreicht") if val >= tg else ("yellow", "Im Toleranzbereich") if val >= ty else ("red", "Kriterium unterschritten")

# -----------------------------------------------------------------------------
# SESSION STATE INIT
# -----------------------------------------------------------------------------
for k, v in {
    "authenticated": False, "user_email": "", "gemini_api_key": "",
    "selected_strategy_name": "Konservativ / Ausgewogen (Standard)",
    "nav_choice": "Pipeline", "trigger_analysis": False, "target_auto_sync": True,
    "obj_name": "", "objektart": "Eigentumswohnung", "stadt": "", "stadtteil": "",
    "bundesland": "Niedersachsen", "kaufpreis": 0.0, "qm": 0.0, "baujahr": 2000,
    "sanierung": 0.0, "grund_anteil": 0.20, "grwt_p": 5.0, "notar_p": 2.0,
    "makler_p": 3.57, "sonst_nk": 0.0, "disagio_p": 0.0, "ek_euro": 0.0, "ek_quote": 0.20,
    "loan_type": "Annuitätendarlehen", "hb_zins": 3.8, "hb_tilg": 2.0, "grace_years": 0,
    "kfw_amt": 0.0, "kfw_zins": 2.1, "kfw_tilg": 3.0, "kfw_grace_years": 0, "kfw_grant": 0.0,
    "sondertilg": 0.0, "ist_miete_monat": 0.0, "ist_sqm": 0.0, "target_miete_monat": 0.0,
    "target_sqm": 0.0, "adj_year": 3, "park": 0.0, "vac_rate_pct": 2.0, "hausgeld": 0.0,
    "hausgeld_nicht_umlegbar": 0.0, "inst_sqm": 12.0, "mgt_monat": 30.0, "capex_j3": 0.0,
    "capex_j6": 0.0, "tax_rate_pct": 42.0, "afa_model": "1_Linear_Standard", "afa_lin": 2.0,
    "miet_inc": 1.5, "cost_inc": 2.0, "val_inc": 1.5, "wacc": 6.0, "exit_cost": 2.0
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

sb_client = get_supabase_client()

# -----------------------------------------------------------------------------
# AUTH GATE
# -----------------------------------------------------------------------------
if not st.session_state["authenticated"]:
    st.markdown("""
    <div class="landing-hero">
        <div class="landing-content">
            <div style="font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; color: #A37841; margin-bottom: 8px;">Institutional Grade Suite</div>
            <h1 style="font-size: 3.5rem; font-weight: 800; letter-spacing: -1.5px; color: #F7F4EC; margin-bottom: 15px; line-height: 1.05;">Valuon Estate</h1>
            <p style="font-size: 1.25rem; color: #D4C9B8; max-width: 650px; margin: 0 0 25px 0; font-weight: 300;">
                Die hochentwickelte Analyse- und Bewertungsumgebung für professionelle Immobilien-Investitionen.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_l1, col_l2 = st.columns([1.3, 1])
    with col_l1:
        st.image("https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80", use_container_width=True)
    with col_l2:
        st.markdown("<div class='valuon-card'>", unsafe_allow_html=True)
        st.markdown("### Zugangsportal")
        if st.button("🛠️ Als Entwickler einloggen (Permanenter Modus)", type="primary", use_container_width=True):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "developer@valuon-estate.de"
            st.rerun()
        st.divider()
        email_in = st.text_input("E-Mail-Adresse", key="login_email")
        pass_in = st.text_input("Passwort", type="password", key="login_pass")
        if st.button("Anmelden", use_container_width=True):
            if email_in and pass_in:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email_in
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -----------------------------------------------------------------------------
# TOP NAVIGATION
# -----------------------------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("""
    <div style="font-size: 2.3rem; font-weight: 800; letter-spacing: -0.8px; color: #13381A; line-height: 1.1;">Valuon Estate</div>
    <div style="font-size: 0.85rem; color: #A37841; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px;">Investment Suite</div>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<div style='text-align: right; font-size: 0.85rem; color: #555759; margin-top: 10px;'>Konto: {st.session_state['user_email']}</div>", unsafe_allow_html=True)
    if st.button("Abmelden", key="btn_logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user_email"] = ""
        st.rerun()

st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)

nav_items = ["Pipeline", "Analyse", "Vergleich", "Kaufpreis", "Immobilienwissen", "Einstellungen"]
nav_cols = st.columns(len(nav_items))
for idx, item in enumerate(nav_items):
    is_active = (st.session_state["nav_choice"] == item)
    if nav_cols[idx].button(item, key=f"nav_btn_{idx}", type="primary" if is_active else "secondary", use_container_width=True):
        st.session_state["nav_choice"] = item
        st.rerun()

st.divider()
nav_choice = st.session_state["nav_choice"]

# =============================================================================
# MODUL 1: PIPELINE
# =============================================================================
if nav_choice == "Pipeline":
    st.markdown("## Investment-Pipeline")
    st.markdown("<p style='color:#555759;'>Übersicht aller gespeicherten Objekte (inkl. lokalem Backup).</p>", unsafe_allow_html=True)

    projects = db_get_projects(sb_client, st.session_state["user_email"])
    
    # JSON BACKUP / RESTORE TOOLBAR
    col_bk1, col_bk2 = st.columns(2)
    if projects:
        projects_json = json.dumps(projects, default=str, ensure_ascii=False, indent=2)
        col_bk1.download_button(
            label="📥 Projekte als Backup herunterladen (.json)",
            data=projects_json,
            file_name="valuon_estate_backup.json",
            mime="application/json",
            use_container_width=True
        )
    
    uploaded_backup = col_bk2.file_uploader("📤 Backup wiederherstellen (.json)", type=["json"])
    if uploaded_backup:
        try:
            imported_data = json.load(uploaded_backup)
            if isinstance(imported_data, list):
                if "local_projects" not in st.session_state:
                    st.session_state["local_projects"] = []
                for p in imported_data:
                    if p not in st.session_state["local_projects"]:
                        st.session_state["local_projects"].append(p)
                st.success("Backup erfolgreich eingelesen!")
                st.rerun()
        except Exception as e:
            st.error(f"Fehler beim Einlesen des Backups: {e}")

    st.divider()

    if projects:
        table_rows = []
        for p in projects:
            d = p["input_data"]
            calc_p, _, _, _, irr_p, _, _ = calc_projection({
                'kaufpreis': d.get("kaufpreis", 0), 'sanierung': d.get("sanierung", 0),
                'bundesland': d.get("bundesland", "Niedersachsen"),
                'grwt_proz': d.get("grwt_p", 5.0)/100, 'notar_proz': d.get("notar_p", 2.0)/100,
                'makler_proz': d.get("makler_p", 3.57)/100, 'sonst_nk': d.get("sonst_nk", 0.0),
                'disagio_proz': d.get("disagio_p", 0)/100, 'ek_euro': d.get("ek_euro", 0.0),
                'ek_quote': d.get("ek_quote", 0.2), 'loan_type': d.get("loan_type", "Annuitätendarlehen"),
                'hb_zins': d.get("hb_zins", 3.8)/100, 'hb_tilg': d.get("hb_tilg", 2.0)/100,
                'grace_years': d.get("grace_years", 0), 'kfw_amt': d.get("kfw_amt", 0),
                'kfw_zins': d.get("kfw_zins", 2.1)/100, 'kfw_tilg': d.get("kfw_tilg", 3.0)/100,
                'kfw_grace_years': d.get("kfw_grace_years", 0), 'kfw_grant': d.get("kfw_grant", 0),
                'sondertilg': d.get("sondertilg", 0), 'ist_sqm': d.get("ist_sqm", 0),
                'target_sqm': d.get("target_sqm", 0) or d.get("ist_sqm", 0),
                'adj_year': d.get("adj_year", 3), 'park': d.get("park", 0),
                'vac_rate': d.get("vac_rate_pct", 2.0)/100, 'qm': d.get("qm", 0),
                'hausgeld': d.get("hausgeld", 0), 'hausgeld_nicht_umlegbar': d.get("hausgeld_nicht_umlegbar", 0),
                'inst_sqm': d.get("inst_sqm", 12.0), 'mgt_monat': d.get("mgt_monat", 30.0),
                'capex_j3': d.get("capex_j3", 0), 'capex_j6': d.get("capex_j6", 0),
                'tax_rate': d.get("tax_rate_pct", 42.0)/100, 'afa_model': d.get("afa_model", "1_Linear_Standard"),
                'afa_lin': d.get("afa_lin", 2.0)/100, 'miet_inc': d.get("miet_inc", 1.5)/100,
                'cost_inc': d.get("cost_inc", 2.0)/100, 'val_inc': d.get("val_inc", 1.5)/100,
                'wacc': d.get("wacc", 6.0)/100, 'exit_cost': d.get("exit_cost", 2.0)/100,
                'grund_anteil': d.get("grund_anteil", 0.2)
            }, full_repayment=False)
            
            loc = d.get("stadt", "")
            if d.get("stadtteil"): loc += f" ({d.get('stadtteil')})"
            if not loc: loc = d.get("bundesland", "Unbekannt")
                
            table_rows.append({
                "Objektname": p["project_name"],
                "Typ": d.get("objektart", "Eigentumswohnung"),
                "Standort": loc,
                "Kaufpreis": fmt_eur(d.get('kaufpreis', 0)),
                "Fläche": fmt_sqm(d.get('qm', 0)),
                "Cashflow (netto)": f"{fmt_de(calc_p.loc[0, 'CF n. St.']/12, 2)} €/M",
                "Bruttomietrendite": fmt_pct(calc_p.loc[0, 'Bruttomietrendite']*100),
                "10J-IRR": fmt_pct(irr_p*100)
            })
            
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
        
        st.divider()
        col_act1, col_act2 = st.columns(2)
        selected_proj = col_act1.selectbox("Projekt auswählen", [p["project_name"] for p in projects])
        
        if col_act1.button("In Analyse-Rechner laden", type="primary", use_container_width=True):
            p_target = next(p for p in projects if p["project_name"] == selected_proj)
            for k, v in p_target["input_data"].items():
                st.session_state[k] = v
            st.session_state["nav_choice"] = "Analyse"
            st.session_state["trigger_analysis"] = True
            st.rerun()

        if col_act2.button("Projekt löschen", use_container_width=True):
            p_target = next(p for p in projects if p["project_name"] == selected_proj)
            db_delete_project(sb_client, p_target["id"])
            st.rerun()
    else:
        st.info("Bisher keine Projekte gespeichert.")

# =============================================================================
# MODUL 2: ANALYSE & RECHNER
# =============================================================================
elif nav_choice == "Analyse":
    with st.sidebar:
        st.markdown("<span class='badge-expose'>1. Objektdaten (Exposé)</span>", unsafe_allow_html=True)
        with st.expander("🤖 KI-gestützter Import (Beta)", expanded=False):
            active_api_key = get_gemini_api_key()
            import_type = st.radio("Quellformat wählen:", ["Web-Link (URL)", "PDF Exposé", "Text manuell"])
            extracted_text = ""
            if import_type == "PDF Exposé":
                up_pdf = st.file_uploader("PDF hochladen", type=["pdf"])
                if up_pdf:
                    for page in PdfReader(up_pdf).pages:
                        extracted_text += page.extract_text() or ""
            elif import_type == "Web-Link (URL)":
                url_in = st.text_input("Inserat-URL:")
                if url_in:
                    extracted_text = fetch_text_from_url(url_in)
            elif import_type == "Text manuell":
                extracted_text = st.text_area("Exposé einfügen:", height=120)

            if extracted_text and active_api_key and st.button("Objektdaten auslesen", use_container_width=True, type="primary"):
                ai_data = analyze_text_with_gemini(active_api_key, extracted_text)
                if ai_data:
                    for k, v in ai_data.items():
                        if k == "kaufpreis" and v: st.session_state["kaufpreis"] = float(v)
                        if k == "wohnflaeche" and v: st.session_state["qm"] = float(v)
                        if k == "baujahr" and v: 
                            st.session_state["baujahr"] = int(v)
                            update_smart_defaults()
                        if k == "ist_miete_monat" and v:
                            st.session_state["ist_miete_monat"] = float(v)
                            st.session_state["target_miete_monat"] = float(v)
                            qm = st.session_state.get("qm", 0)
                            if qm > 0:
                                st.session_state["ist_sqm"] = float(v) / qm
                                st.session_state["target_sqm"] = float(v) / qm
                        if k == "hausgeld_monat" and v: st.session_state["hausgeld"] = float(v)
                        if k == "bundesland" and v in GRUNDERWERBSTEUER_MAP:
                            st.session_state["bundesland"] = v
                            update_grwt_from_bundesland()
                        if k == "stadt" and v != "Unbekannt": st.session_state["stadt"] = v
                        if k == "stadtteil" and v != "Unbekannt": st.session_state["stadtteil"] = v
                        if k == "objektart" and v in OBJEKTARTEN:
                            st.session_state["objektart"] = v
                            update_smart_defaults()
                        if k == "objektname" and v != "Unbekannt": st.session_state["obj_name"] = v
                    st.success("Daten übernommen.")
                    st.rerun()

        st.divider()
        st.markdown("### Parametrisierung")
        with st.expander("1. Objektdaten (Exposé)", expanded=True):
            st.text_input("Objektbezeichnung", key="obj_name")
            st.selectbox("Objektart / Typ", OBJEKTARTEN, key="objektart", on_change=update_smart_defaults)
            st.selectbox("Bundesland", list(GRUNDERWERBSTEUER_MAP.keys()), key="bundesland", on_change=update_grwt_from_bundesland)
            c1, c2 = st.columns(2)
            c1.text_input("Stadt", key="stadt")
            c2.text_input("Stadtteil", key="stadtteil")
            st.number_input("Kaufpreis (€) *", key="kaufpreis", step=5000.0, format="%.2f")
            st.number_input("Wohnfläche (m²) *", key="qm", step=5.0, format="%.2f", on_change=update_qm_callback)
            st.number_input("Baujahr", key="baujahr", step=1, on_change=update_smart_defaults)
            st.markdown("---")
            col_m1, col_m2 = st.columns(2)
            col_m1.number_input("Gesamtkaltmiete (€/Monat)", key="ist_miete_monat", step=50.0, format="%.2f", on_change=update_ist_from_monat)
            col_m2.number_input("Kaltmiete (€/m²)", key="ist_sqm", step=0.5, format="%.2f", on_change=update_ist_from_sqm)
            st.markdown("---")
            st.number_input("Hausgeld gesamt (€/Monat)", key="hausgeld", step=10.0, format="%.2f")
            with st.expander("⚙️ Hausgeld-Aufteilung", expanded=False):
                st.number_input("Davon nicht umlegbar (€/Monat)", key="hausgeld_nicht_umlegbar", step=5.0, format="%.2f")
            st.number_input("Sanierungsaufwand (€)", key="sanierung", step=2500.0, format="%.2f")

        with st.expander("2. Finanzierung & Nebenkosten", expanded=True):
            c_n1, c_n2 = st.columns(2)
            grwt_val = c_n1.number_input("1. Grunderwerbsteuer (%)", key="grwt_p", step=0.1, format="%.2f")
            notar_val = c_n2.number_input("2. Notar & Grundbuch (%)", key="notar_p", step=0.1, format="%.2f")
            kp = st.session_state["kaufpreis"]
            c_n1.markdown(f'<div class="nk-sub-badge">{fmt_eur(kp * grwt_val / 100)}</div>', unsafe_allow_html=True)
            c_n2.markdown(f'<div class="nk-sub-badge">{fmt_eur(kp * notar_val / 100)}</div>', unsafe_allow_html=True)

            c_n3, c_n4 = st.columns(2)
            makler_val = c_n3.number_input("3. Maklerprovision (%)", key="makler_p", step=0.1, format="%.2f")
            sonst_nk = c_n4.number_input("4. Sonst. NK (€)", key="sonst_nk", step=250.0, format="%.2f")
            c_n3.markdown(f'<div class="nk-sub-badge">{fmt_eur(kp * makler_val / 100)}</div>', unsafe_allow_html=True)
            c_n4.markdown(f'<div class="nk-sub-badge">{fmt_eur(sonst_nk)}</div>', unsafe_allow_html=True)

            tot_nk = kp * (grwt_val + notar_val + makler_val) / 100 + sonst_nk
            st.markdown(f'<div class="nk-total-badge"><span>Summe Kaufnebenkosten:</span><span>{fmt_eur(tot_nk)}</span></div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.selectbox("Darlehensart", ["Annuitätendarlehen", "Tilgungsdarlehen", "Endfälliges Darlehen"], key="loan_type")
            st.number_input("Hausbank Zins (%)", key="hb_zins", step=0.1, format="%.2f")
            st.number_input("Hausbank Tilgung (%)", key="hb_tilg", step=0.1, format="%.2f")
            st.number_input("Tilgungsfreie Jahre", key="grace_years", min_value=0, max_value=5)
            
            with st.expander("🏛️ KfW-Darlehen (Optional)", expanded=False):
                st.number_input("KfW Darlehen (€)", key="kfw_amt", step=10000.0, format="%.2f")
                ck1, ck2 = st.columns(2)
                ck1.number_input("KfW Zins (%)", key="kfw_zins", step=0.1, format="%.2f")
                ck2.number_input("KfW Tilgung (%)", key="kfw_tilg", step=0.1, format="%.2f")

            st.markdown("---")
            if st.session_state.get("ek_euro", 0.0) == 0.0 and tot_nk > 0:
                st.session_state["ek_euro"] = float(tot_nk)
            st.number_input("Eingesetztes Eigenkapital (€)", key="ek_euro", step=2500.0, format="%.2f")

        with st.expander("3. Zielmiete & Bewirtschaftung", expanded=False):
            c_zt1, c_zt2 = st.columns(2)
            c_zt1.number_input("Zielkaltmiete (€/Monat)", key="target_miete_monat", step=50.0, format="%.2f", on_change=update_target_from_monat)
            c_zt2.number_input("Zielkaltmiete (€/m²)", key="target_sqm", step=0.5, format="%.2f", on_change=update_target_from_sqm)
            st.number_input("Anpassung in Jahr", key="adj_year", min_value=1, max_value=10)
            st.markdown("---")
            st.number_input("Instandhaltung (€/m²/Jahr)", key="inst_sqm", step=1.0, format="%.2f")
            st.number_input("Verwaltung (€/Monat)", key="mgt_monat", step=5.0, format="%.2f")
            st.slider("Leerstandsquote (%)", 0.0, 10.0, key="vac_rate_pct", step=0.5, format="%.1f %%")

        with st.expander("4. Steuern & Makro", expanded=False):
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
        'objektart': st.session_state["objektart"], 'grwt_proz': st.session_state["grwt_p"]/100,
        'notar_proz': st.session_state["notar_p"]/100, 'makler_proz': st.session_state["makler_p"]/100,
        'sonst_nk': st.session_state["sonst_nk"], 'disagio_proz': st.session_state["disagio_p"]/100,
        'ek_euro': st.session_state["ek_euro"], 'ek_quote': st.session_state["ek_quote"],
        'loan_type': st.session_state["loan_type"], 'hb_zins': st.session_state["hb_zins"]/100,
        'hb_tilg': st.session_state["hb_tilg"]/100, 'grace_years': st.session_state["grace_years"],
        'kfw_amt': st.session_state["kfw_amt"], 'kfw_zins': st.session_state["kfw_zins"]/100,
        'kfw_tilg': st.session_state["kfw_tilg"]/100, 'kfw_grace_years': st.session_state["kfw_grace_years"],
        'kfw_grant': st.session_state["kfw_grant"], 'sondertilg': st.session_state["sondertilg"],
        'ist_sqm': st.session_state["ist_sqm"], 'target_sqm': target_sqm_resolved,
        'adj_year': st.session_state["adj_year"], 'park': st.session_state["park"],
        'vac_rate': st.session_state["vac_rate_pct"]/100, 'qm': st.session_state["qm"],
        'hausgeld': st.session_state["hausgeld"], 'hausgeld_nicht_umlegbar': st.session_state["hausgeld_nicht_umlegbar"],
        'inst_sqm': st.session_state["inst_sqm"], 'mgt_monat': st.session_state["mgt_monat"],
        'capex_j3': st.session_state["capex_j3"], 'capex_j6': st.session_state["capex_j6"],
        'tax_rate': st.session_state["tax_rate_pct"]/100, 'afa_model': st.session_state["afa_model"],
        'afa_lin': st.session_state["afa_lin"]/100, 'miet_inc': st.session_state["miet_inc"]/100,
        'cost_inc': st.session_state["cost_inc"]/100, 'val_inc': st.session_state["val_inc"]/100,
        'wacc': st.session_state["wacc"]/100, 'exit_cost': st.session_state["exit_cost"]/100,
        'grund_anteil': st.session_state["grund_anteil"]
    }

    if not st.session_state.get("trigger_analysis", False):
        st.markdown("""
        <div class="valuon-placeholder">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #13381A; margin-bottom: 10px;">Berechnung ausführen</h2>
            <p style="font-size: 1.05rem; color: #555759; max-width: 620px; margin: 0 auto 15px auto;">
                Tragen Sie Ihre Objektdaten ein und klicken Sie in der Seitenleiste auf <b>"🚀 Analyse starten"</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        if st.session_state["kaufpreis"] <= 0 or st.session_state["qm"] <= 0 or st.session_state["ist_sqm"] <= 0:
            st.error("⚠️ Bitte füllen Sie Kaufpreis, Wohnfläche und Miete aus.")
        else:
            col_hor1, _ = st.columns([2, 2])
            horizon_choice = col_hor1.selectbox("Projektionshorizont:", ["10 Jahre (Standard)", "Bis zur vollen Abzahlung des Darlehens (Volltilgung)"])
            full_rep = ("Volltilgung" in horizon_choice)

            df_proj, tot_inv, ek_abs, fk_tot, irr, afa_base, ek_quote_calc = calc_projection(input_data, full_repayment=full_rep)

            obj_name = st.session_state['obj_name'] or "Unbenanntes Objekt"
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                st.markdown(f"# {obj_name}")
                st.caption(f"Kaufpreis: {fmt_eur(st.session_state['kaufpreis'])} | EK: {fmt_eur(ek_abs)} ({fmt_pct(ek_quote_calc*100)})")
            with col_t2:
                if st.button("In Cloud / lokal speichern", type="primary", use_container_width=True):
                    current_payload = {k: st.session_state[k] for k in default_state.keys()} if 'default_state' in globals() else dict(st.session_state)
                    db_save_project(sb_client, st.session_state["user_email"], obj_name, input_data)

            strat = STRATEGIES[st.session_state.get("selected_strategy_name", "Konservativ / Ausgewogen (Standard)")]
            val_cf = df_proj.loc[0, 'CF n. St.'] / 12
            val_rendite = df_proj.loc[0, 'Bruttomietrendite'] * 100
            val_roe = (df_proj.loc[0, 'CF n. St.'] / ek_abs) * 100 if ek_abs > 0 else 0
            
            kfw_amt_val = max(0, st.session_state["kfw_amt"] - st.session_state["kfw_grant"])
            hb_loan_val = max(0.0, fk_tot - kfw_amt_val)
            hb_annu = hb_loan_val * ((st.session_state["hb_zins"] + st.session_state["hb_tilg"]) / 100)
            kfw_annu = kfw_amt_val * ((st.session_state["kfw_zins"] + st.session_state["kfw_tilg"]) / 100)
            val_dscr = df_proj.loc[0, 'NOI'] / (hb_annu + kfw_annu) if (hb_annu + kfw_annu) > 0 else 1.0

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-card metric-{get_metric_status(val_cf, strat["target_cf"], strat["tol_cf"])[0]}"><div class="metric-title">Cashflow netto</div><div class="metric-value">{fmt_de(val_cf, 2)} €/M</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card metric-{get_metric_status(val_rendite, strat["target_rendite"], strat["tol_rendite"])[0]}"><div class="metric-title">Bruttomietrendite</div><div class="metric-value">{fmt_pct(val_rendite)}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card metric-{get_metric_status(val_roe, strat["target_roe"], strat["tol_roe"])[0]}"><div class="metric-title">EK-Rendite</div><div class="metric-value">{fmt_pct(val_roe)}</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-card metric-{get_metric_status(val_dscr, strat["target_dscr"], strat["tol_dscr"])[0]}"><div class="metric-title">DSCR</div><div class="metric-value">{fmt_de(val_dscr, 2)}</div></div>', unsafe_allow_html=True)

            tab_dash, tab_plan = st.tabs(["Executive Dashboard", "Liquiditätsverlauf & Tilgung"])
            with tab_dash:
                col_chart1, col_chart2 = st.columns([2, 1])
                with col_chart1:
                    chart_mode = st.selectbox("Grafik-Ansicht wählen:", [
                        "1. Vermögensstruktur & NAV (Netto-Eigenkapital)",
                        "2. Cashflow-Entwicklung (Vor & Nach Steuern)",
                        "3. Kapitaldienst (Zins- & Tilgungsverlauf)"
                    ], key="chart_mode_select", label_visibility="collapsed")
                    
                    fig = go.Figure()
                    if "1." in chart_mode:
                        fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Objektwert'], name="Objektwert", line=dict(color="#13381A", width=3)))
                        fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Restschuld'], name="Restschuld", line=dict(color="#8b3a2b", width=3)))
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['NAV'], name="Netto-Eigenkapital (NAV)", marker_color="#A37841", opacity=0.85))
                        fig.update_layout(barmode='group')
                    elif "2." in chart_mode:
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['CF v. St.'], name="CF vor Steuern", marker_color="#13381A"))
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['CF n. St.'], name="CF nach Steuern", marker_color="#A37841"))
                        fig.update_layout(barmode='group')
                    else:
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['Zinsen'], name="Zinsaufwand", marker_color="#8b3a2b"))
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['Tilgung'], name="Tilgungsleistung", marker_color="#13381A"))
                        fig.update_layout(barmode='stack')

                    fig.update_layout(template="plotly_white", height=350, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(tickformat=",.0f", ticksuffix=" €"))
                    st.plotly_chart(fig, use_container_width=True)
                    
                with col_chart2:
                    st.markdown("### Kapitalstruktur")
                    fig_pie = px.pie(names=['Eigenkapital', 'Hausbank', 'KfW'], values=[ek_abs, hb_loan_val, kfw_amt_val], color_discrete_sequence=['#13381A', '#2B2D2F', '#A37841'], hole=0.5)
                    fig_pie.update_layout(height=390, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_pie, use_container_width=True)

            with tab_plan:
                st.dataframe(df_proj, use_container_width=True)

# =============================================================================
# OTHER MODULES
# =============================================================================
elif nav_choice == "Vergleich":
    st.markdown("## Multi-Deal Vergleich")
    st.info("🚀 Coming Soon.")
elif nav_choice == "Kaufpreis":
    st.markdown("## Maximaler Kaufpreis-Rechner")
    st.info("🚀 Coming Soon.")
elif nav_choice == "Immobilienwissen":
    st.markdown("## Immobilienwissen & Investment-Guide")
    st.markdown("Fundiertes Know-how und Kennzahlen.")
elif nav_choice == "Einstellungen":
    st.markdown("## System & Konfiguration")
    st.text_input("Gemini API Key", key="gemini_api_key", type="password")
    st.text_input("Supabase URL", key="supabase_url", type="password")
    st.text_input("Supabase Key", key="supabase_key", type="password")
