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
        padding: 40px 30px;
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
    .badge-investor {
        background-color: #F4EFE6;
        color: #A37841;
        padding: 4px 12px;
        border-radius: 10px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 10px;
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
            "ist_miete_sqm": float,
            "hausgeld_monat": float,
            "bundesland": string,
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

def calc_10y_projection(data):
    kp = data['kaufpreis']
    san = data['sanierung']
    bl = data['bundesland']
    grwt_rate = GRUNDERWERBSTEUER_MAP.get(bl, 0.05)
    
    nk_proz = grwt_rate + data['notar_proz'] + data['makler_proz']
    nk_abs = kp * nk_proz + data['sonst_nk']
    
    disagio_betrag = (kp + san + nk_abs) * (1 - data['ek_quote']) * data['hb_share'] * data['disagio_proz']
    tot_inv = kp + san + nk_abs + disagio_betrag
    
    ek_abs = tot_inv * data['ek_quote']
    fk_tot = tot_inv - ek_abs
    
    hb_loan = fk_tot * data['hb_share']
    kfw_loan = max(0, data['kfw_amt'] - data['kfw_grant'])
    
    afa_base = (kp + nk_abs) * (1 - data['grund_anteil'])
    
    rows = []
    restschuld_hb = hb_loan
    restschuld_kfw = kfw_loan
    obj_val = tot_inv
    
    current_sqm_rent = data['ist_sqm']
    
    for yr in range(1, 11):
        if yr >= data['adj_year']:
            if yr == data['adj_year']:
                current_sqm_rent = data['target_sqm']
            else:
                current_sqm_rent *= (1 + data['miet_inc'])
        
        gross_rent = (current_sqm_rent * data['qm'] + data['park']) * 12
        vacancy = gross_rent * data['vac_rate']
        net_rent = gross_rent - vacancy
        
        op_costs = ((data['hausgeld'] * 12) + (data['inst_sqm'] * data['qm']) + (data['mgt_monat'] * 12)) * ((1 + data['cost_inc']) ** (yr - 1))
        
        capex = 0
        if yr == 3: capex = data['capex_j3']
        if yr == 6: capex = data['capex_j6']
        
        noi = net_rent - op_costs - capex
        
        zins_hb = restschuld_hb * data['hb_zins']
        tilg_hb = (hb_loan * data['hb_tilg']) if yr > data['grace_years'] else 0
        
        zins_kfw = restschuld_kfw * data['kfw_zins'] if kfw_loan > 0 else 0
        tilg_kfw = (kfw_loan * data['kfw_tilg']) if kfw_loan > 0 else 0
        
        zins_tot = zins_hb + zins_kfw
        tilg_tot = tilg_hb + tilg_kfw
        sondertilg = data['sondertilg']
        
        cf_v_st = noi - zins_tot - tilg_tot - sondertilg
        
        if data['afa_model'] == "2_Degressiv_§7_5a":
            afa_val = (afa_base - (yr - 1) * (afa_base * 0.05)) * 0.05
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
        
        restschuld_hb = max(0, restschuld_hb - tilg_hb - sondertilg)
        restschuld_rest = max(0, restschuld_kfw - tilg_kfw)
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
            "Tilgung": tilg_tot + sondertilg,
            "CF v. St.": cf_v_st,
            "AfA": afa_val,
            "Steuer": tax_val,
            "CF n. St.": cf_n_st,
            "Restschuld": restschuld_tot,
            "Objektwert": obj_val,
            "NAV": nav,
            "LTV": ltv
        })
        
    df = pd.DataFrame(rows)
    
    cf_stream = [-ek_abs] + list(df['CF n. St.'].iloc[:-1]) + [df['CF n. St.'].iloc[-1] + (df['Objektwert'].iloc[-1] * (1 - data['exit_cost']) - df['Restschuld'].iloc[-1])]
    try:
        irr = npf.irr(cf_stream)
    except:
        irr = 0.0
        
    return df, tot_inv, ek_abs, fk_tot, irr, afa_base

def get_metric_status(val, target_green, target_yellow):
    if val >= target_green:
        return "green", "Zielwert erreicht"
    elif val >= target_yellow:
        return "yellow", "Im Toleranzbereich"
    else:
        return "red", "Kriterium unterschritten"

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION (CLEAN SLATE: 0.0 DEFAULTS FOR KAUFPREIS & QM)
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

default_state = {
    "obj_name": "", "bundesland": "Niedersachsen", "kaufpreis": 0.0,
    "qm": 0.0, "baujahr": 2000, "sanierung": 0.0, "grund_anteil": 0.20,
    "notar_p": 1.5, "makler_p": 3.57, "sonst_nk": 1000.0, "disagio_p": 0.0,
    "ek_quote": 0.20, "hb_share": 0.80, "hb_zins": 3.8, "hb_tilg": 2.0, "grace_years": 0,
    "kfw_amt": 0.0, "kfw_zins": 2.1, "kfw_tilg": 3.0, "kfw_grant": 0.0, "sondertilg": 0.0,
    "ist_sqm": 0.0, "target_sqm": 0.0, "adj_year": 3, "park": 0.0, "vac_rate": 0.02,
    "hausgeld": 0.0, "inst_sqm": 10.0, "mgt_monat": 25.0, "capex_j3": 0.0, "capex_j6": 0.0,
    "tax_rate": 0.42, "afa_model": "1_Linear_Standard", "afa_lin": 2.0, "miet_inc": 1.5,
    "cost_inc": 2.0, "val_inc": 1.5, "wacc": 6.0, "exit_cost": 2.0
}

for k, v in default_state.items():
    if k not in st.session_state:
        st.session_state[k] = v

sb_client = get_supabase_client()

# -----------------------------------------------------------------------------
# AUTH GATE (IMMERSIVE EDITORIAL LANDING PAGE WITH PARALLAX HERO & GALLERY)
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
            <p style="color:#555759; font-size:0.95rem; margin-bottom:0;">Automatisierter Exposé-Abgleich via Gemini AI, granulare 10-Jahres-Projektionen und automatisierte Risikotests im zeitlosen Heritage-Design.</p>
        </div>
        """, unsafe_allow_html=True)

    with col_landing2:
        st.markdown("<div class='valuon-card'>", unsafe_allow_html=True)
        st.markdown("### Zugangsportal")
        auth_tab1, auth_tab2 = st.tabs(["Login", "Registrieren"])
        
        with auth_tab1:
            email_in = st.text_input("E-Mail-Adresse", key="login_email")
            pass_in = st.text_input("Passwort", type="password", key="login_pass")
            
            if st.button("Anmelden", type="primary", use_container_width=True):
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

        st.divider()
        if st.button("Demo-Modus starten", use_container_width=True):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "analyst@valuon-estate.de"
            # Clean Slate initialization
            st.session_state["kaufpreis"] = 0.0
            st.session_state["qm"] = 0.0
            st.session_state["obj_name"] = ""
            st.session_state["ist_sqm"] = 0.0
            st.session_state["target_sqm"] = 0.0
            st.rerun()
            
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
        st.rerun()

st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)

nav_items = ["Pipeline", "Analyse", "Vergleich", "Kaufpreis", "Einstellungen"]
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
            calc_p, _, ek_p, fk_p, irr_p, _ = calc_10y_projection({
                'kaufpreis': d.get("kaufpreis", 0), 'sanierung': d.get("sanierung", 0),
                'bundesland': d.get("bundesland", "Niedersachsen"), 'notar_proz': d.get("notar_p", 1.5)/100,
                'makler_proz': d.get("makler_p", 3.57)/100, 'sonst_nk': d.get("sonst_nk", 1000),
                'disagio_proz': d.get("disagio_p", 0)/100, 'ek_quote': d.get("ek_quote", 0.2),
                'hb_share': d.get("hb_share", 0.8), 'hb_zins': d.get("hb_zins", 3.8)/100,
                'hb_tilg': d.get("hb_tilg", 2.0)/100, 'grace_years': d.get("grace_years", 0),
                'kfw_amt': d.get("kfw_amt", 0), 'kfw_zins': d.get("kfw_zins", 2.1)/100,
                'kfw_tilg': d.get("kfw_tilg", 3.0)/100, 'kfw_grant': d.get("kfw_grant", 0),
                'sondertilg': d.get("sondertilg", 0), 'ist_sqm': d.get("ist_sqm", 0),
                'target_sqm': d.get("target_sqm", 0), 'adj_year': d.get("adj_year", 3),
                'park': d.get("park", 0), 'vac_rate': d.get("vac_rate", 0.02),
                'qm': d.get("qm", 0), 'hausgeld': d.get("hausgeld", 0),
                'inst_sqm': d.get("inst_sqm", 10), 'mgt_monat': d.get("mgt_monat", 25),
                'capex_j3': d.get("capex_j3", 0), 'capex_j6': d.get("capex_j6", 0),
                'tax_rate': d.get("tax_rate", 0.42), 'afa_model': d.get("afa_model", "1_Linear_Standard"),
                'afa_lin': d.get("afa_lin", 2.0)/100, 'miet_inc': d.get("miet_inc", 1.5)/100,
                'cost_inc': d.get("cost_inc", 2.0)/100, 'val_inc': d.get("val_inc", 1.5)/100,
                'wacc': d.get("wacc", 6.0)/100, 'exit_cost': d.get("exit_cost", 2.0)/100,
                'grund_anteil': d.get("grund_anteil", 0.2)
            })
            
            cf_m = calc_p.loc[0, 'CF n. St.'] / 12
            rendite = calc_p.loc[0, 'Bruttomietrendite'] * 100
            
            table_rows.append({
                "Objektname": p["project_name"],
                "Standort": d.get("bundesland", "Unbekannt"),
                "Kaufpreis": f"{d.get('kaufpreis',0):,.0f} €",
                "Fläche": f"{d.get('qm',0):,.0f} m²",
                "Cashflow (netto)": f"{cf_m:,.2f} €/M",
                "Bruttomietrendite": f"{rendite:.2f} %",
                "10J-IRR": f"{irr_p*100:.2f} %"
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
        
        # VERSTECKTER KI-IMPORT IN EXPANDER (BETA)
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
                            if ai_data.get("wohnflaeche"): st.session_state["qm"] = float(ai_data["wohnflaeche"])
                            if ai_data.get("baujahr"): st.session_state["baujahr"] = int(ai_data["baujahr"])
                            if ai_data.get("ist_miete_sqm"): st.session_state["ist_sqm"] = float(ai_data["ist_miete_sqm"])
                            if ai_data.get("hausgeld_monat"): st.session_state["hausgeld"] = float(ai_data["hausgeld_monat"])
                            if ai_data.get("objektname") and str(ai_data["objektname"]) != "Unbekannt": 
                                st.session_state["obj_name"] = str(ai_data["objektname"])
                            st.success("Objektdaten erfolgreich übernommen.")
                            st.rerun()

        st.divider()
        st.markdown("### Parametrisierung")
        
        # FORMULAR FÜR PARAMETER (RECHENUPDATE ERST BEIM BESTÄTIGEN)
        with st.form(key="parameter_form"):
            with st.expander("1. Objektdaten (Exposé)", expanded=True):
                st.text_input("Objektbezeichnung", key="obj_name", placeholder="z. B. Mehrfamilienhaus Bonn")
                st.selectbox("Bundesland", list(GRUNDERWERBSTEUER_MAP.keys()), key="bundesland")
                st.number_input("Kaufpreis (€)", key="kaufpreis", step=5000.0)
                st.number_input("Wohnfläche (m²)", key="qm", step=5.0)
                st.number_input("Baujahr", key="baujahr", step=1)
                st.number_input("Ist-Kaltmiete (€/m²)", key="ist_sqm")
                st.number_input("Hausgeld (€/Monat)", key="hausgeld")
                st.number_input("Sanierungsaufwand (€)", key="sanierung", step=2500.0)

            with st.expander("2. Finanzierung & Nebenkosten", expanded=False):
                st.markdown("<span class='badge-investor'>Investor-Parameter</span>", unsafe_allow_html=True)
                st.slider("Eigenkapitalquote (%)", 0.0, 0.50, key="ek_quote", step=0.05)
                st.number_input("Hausbank Zins (%)", key="hb_zins")
                st.number_input("Hausbank Tilgung (%)", key="hb_tilg")
                st.number_input("Tilgungsfreie Jahre", key="grace_years", min_value=0, max_value=5)
                st.number_input("Notar (%)", key="notar_p")
                st.number_input("Makler (%)", key="makler_p")
                st.number_input("Sonstige NK (€)", key="sonst_nk")
                st.number_input("KfW Darlehen (€)", key="kfw_amt", step=10000.0)
                st.number_input("KfW Zins (%)", key="kfw_zins")
                st.number_input("KfW Tilgung (%)", key="kfw_tilg")

            with st.expander("3. Zielmiete & Bewirtschaftung", expanded=False):
                st.number_input("Ziel-Kaltmiete (€/m²)", key="target_sqm")
                st.number_input("Anpassung in Jahr", key="adj_year", min_value=1, max_value=10)
                st.number_input("Instandhaltung (€/m²/Jahr)", key="inst_sqm")
                st.number_input("Verwaltung (€/Monat)", key="mgt_monat")
                st.slider("Leerstandsquote (%)", 0.0, 0.10, key="vac_rate")

            with st.expander("4. Steuern & Makro-Annahmen", expanded=False):
                st.slider("Grenzsteuersatz (%)", 0.0, 0.50, key="tax_rate", step=0.01)
                st.selectbox("AfA-Modell", ["1_Linear_Standard", "2_Degressiv_§7_5a", "3_Sonder_AfA_§7b", "4_Denkmal_§7h_7i"], key="afa_model")
                st.number_input("Mietsteigerung p.a. (%)", key="miet_inc")
                st.number_input("Wertsteigerung p.a. (%)", key="val_inc")

            st.form_submit_button("Eingaben bestätigen & Berechnen", type="primary", use_container_width=True)

    input_data = {
        'kaufpreis': st.session_state["kaufpreis"], 'sanierung': st.session_state["sanierung"],
        'bundesland': st.session_state["bundesland"], 'notar_proz': st.session_state["notar_p"] / 100,
        'makler_proz': st.session_state["makler_p"] / 100, 'sonst_nk': st.session_state["sonst_nk"],
        'disagio_proz': st.session_state["disagio_p"] / 100, 'ek_quote': st.session_state["ek_quote"],
        'hb_share': st.session_state["hb_share"], 'hb_zins': st.session_state["hb_zins"] / 100,
        'hb_tilg': st.session_state["hb_tilg"] / 100, 'grace_years': st.session_state["grace_years"],
        'kfw_amt': st.session_state["kfw_amt"], 'kfw_zins': st.session_state["kfw_zins"] / 100,
        'kfw_tilg': st.session_state["kfw_tilg"] / 100, 'kfw_grant': st.session_state["kfw_grant"],
        'sondertilg': st.session_state["sondertilg"], 'ist_sqm': st.session_state["ist_sqm"],
        'target_sqm': st.session_state["target_sqm"] if st.session_state["target_sqm"] > 0 else st.session_state["ist_sqm"], 
        'adj_year': st.session_state["adj_year"],
        'park': st.session_state["park"], 'vac_rate': st.session_state["vac_rate"],
        'qm': st.session_state["qm"], 'hausgeld': st.session_state["hausgeld"],
        'inst_sqm': st.session_state["inst_sqm"], 'mgt_monat': st.session_state["mgt_monat"],
        'capex_j3': st.session_state["capex_j3"], 'capex_j6': st.session_state["capex_j6"],
        'tax_rate': st.session_state["tax_rate"], 'afa_model': st.session_state["afa_model"],
        'afa_lin': st.session_state["afa_lin"] / 100, 'miet_inc': st.session_state["miet_inc"] / 100,
        'cost_inc': st.session_state["cost_inc"] / 100, 'val_inc': st.session_state["val_inc"] / 100,
        'wacc': st.session_state["wacc"] / 100, 'exit_cost': st.session_state["exit_cost"] / 100,
        'grund_anteil': st.session_state["grund_anteil"]
    }

    has_minimum_data = (st.session_state["kaufpreis"] > 0) and (st.session_state["qm"] > 0)

    if not has_minimum_data:
        st.markdown("""
        <div class="valuon-placeholder">
            <h2 style="font-size: 1.8rem; font-weight: 700; color: #13381A; margin-bottom: 10px;">Objektbewertung initialisieren</h2>
            <p style="font-size: 1.05rem; color: #555759; max-width: 580px; margin: 0 auto 15px auto;">
                Bitte erfassen Sie in der linken Seitenleiste mindestens den <b>Kaufpreis</b> und die <b>Wohnfläche</b> und klicken Sie auf <b>„Eingaben bestätigen & Berechnen“</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.image(
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
            use_container_width=True
        )
    else:
        df_proj, tot_inv, ek_abs, fk_tot, irr, afa_base = calc_10y_projection(input_data)

        obj_display_name = st.session_state['obj_name'] if st.session_state['obj_name'] else "Unbenanntes Objekt"
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.markdown(f"# {obj_display_name}")
            st.caption(f"Standort: {st.session_state['bundesland']} | Fläche: {st.session_state['qm']:.0f} m² | Kaufpreis: {st.session_state['kaufpreis']:,.0f} €")
        with col_t2:
            current_payload = {k: st.session_state[k] for k in default_state.keys()}
            if sb_client and st.button("In Cloud speichern", type="primary", use_container_width=True):
                db_save_project(sb_client, st.session_state["user_email"], obj_display_name, current_payload)

        strat_name = st.session_state.get("selected_strategy_name", "Konservativ / Ausgewogen (Standard)")
        strat = STRATEGIES.get(strat_name, STRATEGIES["Konservativ / Ausgewogen (Standard)"])
        
        val_cf = df_proj.loc[0, 'CF n. St.'] / 12
        val_rendite = df_proj.loc[0, 'Bruttomietrendite'] * 100
        val_roe = (df_proj.loc[0, 'CF n. St.'] / ek_abs) * 100 if ek_abs > 0 else 0.0
        hb_annu = fk_tot * (st.session_state["hb_share"]) * ((st.session_state["hb_zins"] + st.session_state["hb_tilg"]) / 100)
        kfw_annu = max(0, st.session_state["kfw_amt"] - st.session_state["kfw_grant"]) * ((st.session_state["kfw_zins"] + st.session_state["kfw_tilg"]) / 100)
        val_dscr = df_proj.loc[0, 'NOI'] / (hb_annu + kfw_annu) if (hb_annu + kfw_annu) > 0 else 1.0

        status_cf, label_cf = get_metric_status(val_cf, strat["target_cf"], strat["tol_cf"])
        status_rendite, label_rendite = get_metric_status(val_rendite, strat["target_rendite"], strat["tol_rendite"])
        status_roe, label_roe = get_metric_status(val_roe, strat["target_roe"], strat["tol_roe"])
        status_dscr, label_dscr = get_metric_status(val_dscr, strat["target_dscr"], strat["tol_dscr"])

        # KPI CARDS WITH CUSTOM HOVER TOOLTIPS
        c1, c2, c3, c4 = st.columns(4)
        
        c1.markdown(f'''
        <div class="metric-card metric-{status_cf}">
            <div class="metric-header">
                <span class="metric-title">Cashflow (netto)</span>
                <div class="tooltip-container">
                    <span class="tooltip-icon">i</span>
                    <div class="tooltip-box">
                        <strong>Bedeutung & Relevanz</strong>
                        Monatlicher Überschuss nach Abzug aller Bewirtschaftungskosten, Kreditraten (Zins & Tilgung) und Steuern.<br><br>
                        <em>Warum entscheidend?</em> Sichert Ihre laufende Liquidität und verhindert ungewollte Nachzahlungen aus dem Privatvermögen.
                    </div>
                </div>
            </div>
            <div class="metric-value">{val_cf:,.2f} €/M</div>
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
                        Verhältnis der jährlichen Bruttokaltmiete zum reinen Kaufpreis des Objekts.<br><br>
                        <em>Warum entscheidend?</em> Erlaubt eine erste Standort- und Markt-Einschätzung, blendet jedoch Nebenkosten und Finanzierungsstruktur aus.
                    </div>
                </div>
            </div>
            <div class="metric-value">{val_rendite:.2f} %</div>
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
                        Prozentuale Verzinsung Ihres tatsächlich eingebrachten Eigenkapitals bezogen auf den Jahres-Cashflow.<br><br>
                        <em>Warum entscheidend?</em> Zeigt die Effizienz Ihres Kapitals und macht den Hebeleffekt (Leverage-Effekt) der Bankfinanzierung sichtbar.
                    </div>
                </div>
            </div>
            <div class="metric-value">{val_roe:.2f} %</div>
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
                        Debt Service Coverage Ratio: Verhältnis des Netto-Betriebseinkommens (NOI) zum jährlichen Schuldendienst (Zins + Tilgung).<br><br>
                        <em>Warum entscheidend?</em> Die Key-Kennzahl für Banken. Ein Wert über 1,20 belegt ausreichend Puffer, um den Kredit auch bei Mietausfällen sicher zu bedienen.
                    </div>
                </div>
            </div>
            <div class="metric-value">{val_dscr:.2f}</div>
            <div class="metric-status">{label_dscr}</div>
        </div>
        ''', unsafe_allow_html=True)

        # LAUNCH TABS
        tab_dash, tab_plan = st.tabs(["Executive Dashboard", "10-Jahres-Modell"])

        with tab_dash:
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                st.markdown("### Vermögensentwicklung vs. Restschuld")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Objektwert'], name="Objektwert (€)", line=dict(color="#13381A", width=3)))
                fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Restschuld'], name="Restschuld (€)", line=dict(color="#A37841", width=3)))
                fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['NAV'], name="Netto-Eigenkapital (NAV)", marker_color="#2B2D2F", opacity=0.2))
                fig.update_layout(template="plotly_white", height=380, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
                
            with col_chart2:
                st.markdown("### Kapitalstruktur")
                fig_pie = px.pie(
                    names=['Eigenkapital', 'Hausbank', 'KfW'],
                    values=[ek_abs, fk_tot * st.session_state["hb_share"], max(0, st.session_state["kfw_amt"] - st.session_state["kfw_grant"])],
                    color_discrete_sequence=['#13381A', '#2B2D2F', '#A37841'],
                    hole=0.5
                )
                fig_pie.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_pie, use_container_width=True)

        with tab_plan:
            st.markdown("### Liquiditätsverlauf (10 Jahre)")
            st.dataframe(df_proj.style.format({
                "Bruttomietrendite": "{:.2%}", "Brutto-Kaltmiete": "{:,.0f} €", "NOI": "{:,.0f} €",
                "Zinsen": "{:,.0f} €", "Tilgung": "{:,.0f} €", "CF v. St.": "{:,.0f} €",
                "AfA": "{:,.0f} €", "Steuer": "{:,.0f} €", "CF n. St.": "{:,.0f} €",
                "Restschuld": "{:,.0f} €", "Objektwert": "{:,.0f} €", "NAV": "{:,.0f} €", "LTV": "{:.1%}"
            }), use_container_width=True)

        # VERSTECKTES MULTI-TAB CODE-SEGMENT (BLEIBT ERHALTEN)
        if False:
            tab_tax, tab_stress = st.tabs(["Steuer-Struktur", "Stresstest"])
            
            with tab_tax:
                st.markdown("### Rechtsform-Vergleich (Privat vs. VV-GmbH)")
                tot_taxable = df_proj['NOI'].sum() - df_proj['Zinsen'].sum() - df_proj['AfA'].sum()
                tax_privat = tot_taxable * st.session_state["tax_rate"]
                tax_gmbh = tot_taxable * 0.15825
                c_t1, c_t2, c_t3 = st.columns(3)
                c_t1.metric("Steuerlast Privat", f"{tax_privat:,.0f} €")
                c_t2.metric("Steuerlast VV-GmbH", f"{tax_gmbh:,.0f} €")
                c_t3.metric("Steuerdifferenz", f"{tax_privat - tax_gmbh:,.0f} €")

            with tab_stress:
                st.markdown("### Zinsänderungsrisiko (Anschlussfinanzierung Jahr 11)")
                restschuld_10 = df_proj.loc[9, 'Restschuld']
                rates = [0.035, 0.045, 0.055, 0.065, 0.075]
                refin_data = []
                for r in rates:
                    new_rate = (restschuld_10 * (r + (st.session_state["hb_tilg"] / 100))) / 12
                    new_dscr = df_proj.loc[9, 'NOI'] / (new_rate * 12) if new_rate > 0 else 0
                    refin_data.append({"Sollzins": f"{r*100:.1f} %", "Monatliche Rate": f"{new_rate:,.2f} €", "DSCR": f"{new_dscr:.2f}"})
                st.table(pd.DataFrame(refin_data))

# =============================================================================
# MODUL 3: DEAL-VERGLEICH
# =============================================================================
elif nav_choice == "Vergleich":
    st.markdown("## Multi-Deal Vergleich")
    st.markdown("<p style='color:#555759;'>Parallele Gegenüberstellung mehrerer Investitionsvorhaben.</p>", unsafe_allow_html=True)
    
    st.info("🚀 **Coming Soon:** Dieses Modul befindet sich aktuell in der Entwicklung und wird in Kürze freigeschaltet. Valuon Estate wächst stetig weiter.")
    
    # VERSTECKER CODE FÜR DEN DEAL-VERGLEICH
    if False:
        projects = db_get_projects(sb_client, st.session_state["user_email"])
        
        if len(projects) >= 2:
            selected_deals = st.multiselect("Projekte auswählen:", [p["project_name"] for p in projects], default=[p["project_name"] for p in projects[:2]])
            
            if len(selected_deals) >= 2:
                cols = st.columns(len(selected_deals))
                
                for idx, deal_name in enumerate(selected_deals):
                    p = next(proj for proj in projects if proj["project_name"] == deal_name)
                    d = p["input_data"]
                    
                    df_c, tot_inv, ek_abs, fk_tot, irr, _ = calc_10y_projection({
                        'kaufpreis': d.get("kaufpreis", 0), 'sanierung': d.get("sanierung", 0),
                        'bundesland': d.get("bundesland", "Niedersachsen"), 'notar_proz': d.get("notar_p", 1.5)/100,
                        'makler_proz': d.get("makler_p", 3.57)/100, 'sonst_nk': d.get("sonst_nk", 1000),
                        'disagio_proz': d.get("disagio_p", 0)/100, 'ek_quote': d.get("ek_quote", 0.2),
                        'hb_share': d.get("hb_share", 0.8), 'hb_zins': d.get("hb_zins", 3.8)/100,
                        'hb_tilg': d.get("hb_tilg", 2.0)/100, 'grace_years': d.get("grace_years", 0),
                        'kfw_amt': d.get("kfw_amt", 0), 'kfw_zins': d.get("kfw_zins", 2.1)/100,
                        'kfw_tilg': d.get("kfw_tilg", 3.0)/100, 'kfw_grant': d.get("kfw_grant", 0),
                        'sondertilg': d.get("sondertilg", 0), 'ist_sqm': d.get("ist_sqm", 0),
                        'target_sqm': d.get("target_sqm", 0), 'adj_year': d.get("adj_year", 3),
                        'park': d.get("park", 0), 'vac_rate': d.get("vac_rate", 0.02),
                        'qm': d.get("qm", 0), 'hausgeld': d.get("hausgeld", 0),
                        'inst_sqm': d.get("inst_sqm", 10), 'mgt_monat': d.get("mgt_monat", 25),
                        'capex_j3': d.get("capex_j3", 0), 'capex_j6': d.get("capex_j6", 0),
                        'tax_rate': d.get("tax_rate", 0.42), 'afa_model': d.get("afa_model", "1_Linear_Standard"),
                        'afa_lin': d.get("afa_lin", 2.0)/100, 'miet_inc': d.get("miet_inc", 1.5)/100,
                        'cost_inc': d.get("cost_inc", 2.0)/100, 'val_inc': d.get("val_inc", 1.5)/100,
                        'wacc': d.get("wacc", 6.0)/100, 'exit_cost': d.get("exit_cost", 2.0)/100,
                        'grund_anteil': d.get("grund_anteil", 0.2)
                    })
                    
                    cf_m = df_c.loc[0, 'CF n. St.'] / 12
                    rendite = df_c.loc[0, 'Bruttomietrendite'] * 100
                    
                    with cols[idx]:
                        st.markdown(f"<div class='valuon-card'><h3>{deal_name}</h3>", unsafe_allow_html=True)
                        st.metric("Kaufpreis", f"{d.get('kaufpreis', 0):,.0f} €")
                        st.metric("Cashflow (netto)", f"{cf_m:,.2f} €/M")
                        st.metric("Bruttomietrendite", f"{rendite:.2f} %")
                        st.metric("10J-IRR", f"{irr*100:.2f} %")
                        st.metric("Eigenkapital", f"{ek_abs:,.0f} €")
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning("Bitte wählen Sie mindestens zwei Projekte für den Vergleich aus.")
        else:
            st.info("Es sind mindestens zwei gespeicherte Projekte erforderlich, um den Deal-Vergleich zu nutzen.")

# =============================================================================
# MODUL 4: MAXIMALER KAUFPREIS
# =============================================================================
elif nav_choice == "Kaufpreis":
    st.markdown("## Maximaler Kaufpreis-Rechner")
    st.markdown("<p style='color:#555759;'>Ermittlung der strategischen Gebots-Obergrenze.</p>", unsafe_allow_html=True)

    st.info("🚀 **Coming Soon:** Dieses Modul befindet sich aktuell in der Entwicklung und wird in Kürze freigeschaltet. Valuon Estate wächst stetig weiter.")

    # VERSTECKER CODE FÜR DEN MAX KAUFPREIS-RECHNER
    if False:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            desired_cf = st.number_input("Ziel-Cashflow (netto, €/Monat)", value=100.0, step=25.0)
            current_kp = st.session_state["kaufpreis"]
            st.info(f"Aktueller Objektpreis: **{current_kp:,.0f} €**")

        with col_g2:
            best_price = current_kp
            if current_kp > 0:
                for test_kp in range(50000, 2000000, 5000):
                    test_data = dict(input_data)
                    test_data['kaufpreis'] = float(test_kp)
                    df_test, _, _, _, _, _ = calc_10y_projection(test_data)
                    test_cf = df_test.loc[0, 'CF n. St.'] / 12
                    if test_cf >= desired_cf:
                        best_price = test_kp
                    else:
                        break
                        
                st.metric("Gebots-Obergrenze", f"{best_price:,.0f} €", delta=f"{best_price - current_kp:,.0f} € zum Angebotspreis")
            else:
                st.warning("Bitte definieren Sie zuerst die Objektdaten im Analyse-Rechner.")

# =============================================================================
# MODUL 5: EINSTELLUNGEN
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
