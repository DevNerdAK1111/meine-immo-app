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
# PAGE CONFIG & APPLE DESIGN SYSTEM (CSS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ImmoAnalyse Pro",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Clean Typography & Apple Colors */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        color: #1d1d1f;
        background-color: #fafafa;
    }
    
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    
    /* Hide top default Streamlit padding/header artifacts */
    header[data-testid="stHeader"] {
        background: transparent !important;
        z-index: 1;
    }
    
    /* Apple Clean Cards */
    .apple-card {
        background-color: #ffffff;
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 20px;
        border: 1px solid rgba(0, 0, 0, 0.06);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    
    .apple-placeholder {
        background: linear-gradient(135deg, #f5f5f7 0%, #ffffff 100%);
        border: 2px dashed #d2d2d7;
        border-radius: 20px;
        padding: 50px 30px;
        text-align: center;
        margin: 20px 0;
    }
    
    /* Apple Pill Buttons styling */
    .stButton > button {
        border-radius: 980px !important;
        font-weight: 500 !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease !important;
        border: 1px solid #d2d2d7 !important;
        background-color: #ffffff !important;
        color: #1d1d1f !important;
    }
    
    .stButton > button:hover {
        border-color: #0066cc !important;
        color: #0066cc !important;
        background-color: #f5f5f7 !important;
    }
    
    .stButton > button[kind="primary"] {
        background-color: #0066cc !important;
        color: #ffffff !important;
        border-color: #0066cc !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #0052a3 !important;
        color: #ffffff !important;
    }

    /* KPI Ampel Cards */
    .ampel-card {
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 15px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .ampel-green { background-color: #eefdf4; border-left: 5px solid #22c55e; color: #14532d; }
    .ampel-yellow { background-color: #fefce8; border-left: 5px solid #eab308; color: #713f12; }
    .ampel-red { background-color: #fef2f2; border-left: 5px solid #ef4444; color: #7f1d1d; }
    .ampel-title { font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.7; margin-bottom: 4px; }
    .ampel-value { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.5px; }
    .ampel-status { font-size: 0.8rem; font-weight: 600; margin-top: 4px; }
    
    /* Section Badges */
    .badge-expose {
        background-color: #e8f2ff;
        color: #0066cc;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 10px;
    }
    .badge-investor {
        background-color: #f3e8ff;
        color: #7e22ce;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
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
            st.success(f"Projekt '{project_name}' aktualisiert!")
        else:
            supabase.table("projects").insert({
                "user_id": user_id,
                "project_name": project_name,
                "input_data": payload
            }).execute()
            st.success(f"Projekt '{project_name}' gespeichert!")
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
        st.success("Projekt gelöscht!")
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
            st.warning("🛡️ Die Website schützt sich mit einem Bot-Schutz (z. B. ImmoScout24). Bitte kopieren Sie den Text der Anzeige und nutzen Sie die Option '📝 Text kopieren'.")
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
    """Extrahiert REIN die im Exposé vorhandenen Objekt-Fakten."""
    try:
        genai.configure(api_key=api_key)
        
        prompt = f"""
        Du bist ein Immobilien-Experte. Analysiere den folgenden Immobilien-Anzeigentext und extrahiere NUR die reinen Objekt-Fakten als valides JSON.
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
            st.error("⏳ **API-Limit von Google kurzzeitig erreicht!** Bitte 1 Minute warten.")
        elif "API_KEY" in err_msg.upper() or "INVALID" in err_msg.upper():
            st.error("🔑 **Ungültiger Gemini API-Key:** Bitte unter *⚙️ Einstellungen* prüfen.")
        else:
            st.error(f"⚠️ **Fehler bei der KI-Analyse:** {err_msg}")
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

def get_ampel_status(val, target_green, target_yellow):
    if val >= target_green:
        return "green", "🟢 Ziel erfüllt"
    elif val >= target_yellow:
        return "yellow", "🟡 Toleranzbereich"
    else:
        return "red", "🔴 Kriterium verfehlt"

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
    st.session_state["nav_choice"] = "📁 Meine Projekte"

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
# AUTH GATE (CLEAN LANDING PAGE WITHOUT EXTRA BARS)
# -----------------------------------------------------------------------------
if not st.session_state["authenticated"]:
    st.markdown("""
    <div style="text-align: center; padding: 20px 20px 10px 20px;">
        <h1 style="font-size: 2.8rem; font-weight: 800; letter-spacing: -1px; color: #1d1d1f;">ImmoAnalyse Pro</h1>
        <p style="font-size: 1.15rem; color: #86868b; max-width: 550px; margin: 0 auto 20px auto;">
            Die smarte PropTech-Suite für professionelle Immobilien-Investoren.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_landing1, col_landing2 = st.columns([1.2, 1])

    with col_landing1:
        st.markdown("""
        <div class="apple-card">
            <h3 style="margin-top:0; color:#0066cc;">🤖 KI-Import für Exposés & Links</h3>
            <p style="color:#86868b; margin-bottom:0;">Lade Web-Links oder PDFs hoch – Gemini AI extrahiert die echten Objekt-Fakten ohne Halluzinationen.</p>
        </div>
        <div class="apple-card">
            <h3 style="margin-top:0; color:#0066cc;">📊 Dynamische 10-Jahres-Kalkulation</h3>
            <p style="color:#86868b; margin-bottom:0;">Trennung zwischen Objekt-Fakten und deinen individuellen Bank- & Finanzierungskonditionen.</p>
        </div>
        <div class="apple-card">
            <h3 style="margin-top:0; color:#0066cc;">☁️ Multi-Projekt Cloud</h3>
            <p style="color:#86868b; margin-bottom:0;">Speichere all deine Objekte in der Cloud und vergleiche sie Side-by-Side.</p>
        </div>
        """, unsafe_allow_html=True)

    with col_landing2:
        st.markdown("<div class='apple-card'>", unsafe_allow_html=True)
        st.markdown("### 🔐 Anmelden")
        auth_tab1, auth_tab2 = st.tabs(["Login", "Registrieren"])
        
        with auth_tab1:
            email_in = st.text_input("E-Mail Adresse", key="login_email")
            pass_in = st.text_input("Passwort", type="password", key="login_pass")
            
            if st.button("🔑 Anmelden", type="primary", use_container_width=True):
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
                        st.error("Bitte E-Mail und Passwort eingeben.")

        with auth_tab2:
            reg_email = st.text_input("E-Mail Adresse", key="reg_email")
            reg_pass = st.text_input("Passwort erstellen", type="password", key="reg_pass")
            if st.button("✨ Account erstellen", use_container_width=True):
                if sb_client:
                    try:
                        res = sb_client.auth.sign_up({"email": reg_email, "password": reg_pass})
                        st.success("Profil erstellt! Sie können sich jetzt anmelden.")
                    except Exception as e:
                        st.error(f"Registrierung fehlgeschlagen: {e}")
                else:
                    st.success("Demo-Profil angelegt! Nutzen Sie den Login-Tab.")

        st.divider()
        if st.button("👤 Gast / Demo-Zugang", use_container_width=True):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "gast_investor@immo.de"
            st.session_state["kaufpreis"] = 350000.0
            st.session_state["qm"] = 120.0
            st.session_state["obj_name"] = "Muster-Objekt Hanover"
            st.session_state["ist_sqm"] = 9.50
            st.session_state["target_sqm"] = 12.00
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# -----------------------------------------------------------------------------
# MAIN APPLICATION HEADER & TOP NAVIGATION
# -----------------------------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("""
    <div style="font-size: 1.8rem; font-weight: 800; letter-spacing: -0.5px; color: #1d1d1f;">
        ImmoAnalyse Pro
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<div style='text-align: right; font-size: 0.85rem; color: #86868b;'>👤 {st.session_state['user_email']}</div>", unsafe_allow_html=True)
    if st.button("🚪 Abmelden", key="btn_logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user_email"] = ""
        st.rerun()

nav_items = ["📁 Meine Projekte", "➕ Analyse & Rechner", "⚖️ Deal-Vergleich", "🧮 Max. Kaufpreis", "⚙️ Einstellungen"]
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
# MODUL 1: 📁 MEINE PROJEKTE
# =============================================================================
if nav_choice == "📁 Meine Projekte":
    st.markdown("## 📁 Meine Immobilien-Pipeline")
    st.markdown("<p style='color:#86868b;'>Verwalten Sie all Ihre analysierten Objekte auf einen Blick.</p>", unsafe_allow_html=True)

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
                "Wohnfläche": f"{d.get('qm',0):.0f} m²",
                "Cashflow (n. St.)": f"{cf_m:,.2f} €/M",
                "Bruttomietrendite": f"{rendite:.2f} %",
                "10-Jahres IRR": f"{irr_p*100:.2f} %"
            })
            
        df_summary = pd.DataFrame(table_rows)
        st.dataframe(df_summary, use_container_width=True)
        
        st.divider()
        st.markdown("### ⚡ Schnell-Aktionen")
        col_act1, col_act2 = st.columns(2)
        
        selected_project_name = col_act1.selectbox("Projekt auswählen", [p["project_name"] for p in projects])
        
        if col_act1.button("📥 Projekt in Analyse-Tool laden", type="primary", use_container_width=True):
            p_target = next(p for p in projects if p["project_name"] == selected_project_name)
            for k, v in p_target["input_data"].items():
                st.session_state[k] = v
            st.session_state["nav_choice"] = "➕ Analyse & Rechner"
            st.rerun()

        if col_act2.button("🗑️ Projekt unwiderruflich löschen", use_container_width=True):
            p_target = next(p for p in projects if p["project_name"] == selected_project_name)
            db_delete_project(sb_client, p_target["id"])
            st.rerun()

    else:
        st.info("💡 Noch keine Objekte in der Datenbank gespeichert. Wechseln Sie zum Reiter **'➕ Analyse & Rechner'**, um Ihr erstes Objekt einzugeben!")

# =============================================================================
# MODUL 2: ➕ ANALYSE & RECHNER (Gliederung in Objekt- & Investor-Daten)
# =============================================================================
elif nav_choice == "➕ Analyse & Rechner":
    
    with st.sidebar:
        st.markdown("<span class='badge-expose'>1. Objektdaten (Exposé)</span>", unsafe_allow_html=True)
        st.subheader("🤖 KI-Import")
        active_api_key = get_gemini_api_key()
        
        import_type = st.radio("Quelle wählen:", ["🔗 Web-Link (URL)", "📄 PDF Exposé", "📝 Text kopieren"])
        
        extracted_text_to_analyze = ""
        
        if import_type == "📄 PDF Exposé":
            uploaded_pdf = st.file_uploader("Exposé PDF hochladen", type=["pdf"])
            if uploaded_pdf:
                reader = PdfReader(uploaded_pdf)
                for page in reader.pages:
                    extracted_text_to_analyze += page.extract_text() or ""

        elif import_type == "🔗 Web-Link (URL)":
            input_url = st.text_input("Anzeigen-Link (Kleinanzeigen etc.):")
            if input_url:
                with st.spinner("Lade Website-Inhalt..."):
                    extracted_text_to_analyze = fetch_text_from_url(input_url)

        elif import_type == "📝 Text kopieren":
            extracted_text_to_analyze = st.text_area("Anzeigen-Text kopieren:", height=120)

        if extracted_text_to_analyze and active_api_key:
            if st.button("✨ Objektdaten per KI auslesen", use_container_width=True, type="primary"):
                with st.spinner("Gemini AI liest Objekt-Fakten..."):
                    ai_data = analyze_text_with_gemini(active_api_key, extracted_text_to_analyze)
                    if ai_data:
                        if ai_data.get("kaufpreis"): st.session_state["kaufpreis"] = float(ai_data["kaufpreis"])
                        if ai_data.get("wohnflaeche"): st.session_state["qm"] = float(ai_data["wohnflaeche"])
                        if ai_data.get("baujahr"): st.session_state["baujahr"] = int(ai_data["baujahr"])
                        if ai_data.get("ist_miete_sqm"): st.session_state["ist_sqm"] = float(ai_data["ist_miete_sqm"])
                        if ai_data.get("hausgeld_monat"): st.session_state["hausgeld"] = float(ai_data["hausgeld_monat"])
                        if ai_data.get("objektname") and str(ai_data["objektname"]) != "Unbekannt": 
                            st.session_state["obj_name"] = str(ai_data["objektname"])
                        st.success("Objektdaten übernommen!")
                        st.rerun()

        st.divider()
        
        # STRUCTURING INPUT FIELDS IN EXPANDABLE ACCORDIONS (PREVENTS OVERWHELMING)
        st.markdown("### 📋 Daten-Eingabe")
        
        with st.expander("🏢 1. Objektdaten (Exposé)", expanded=True):
            st.text_input("Objektname", key="obj_name", placeholder="z. B. ETW Berlin-Mitte")
            st.selectbox("Bundesland", list(GRUNDERWERBSTEUER_MAP.keys()), key="bundesland")
            st.number_input("Kaufpreis (€)", key="kaufpreis", step=5000.0)
            st.number_input("Wohnfläche (m²)", key="qm", step=5.0)
            st.number_input("Baujahr", key="baujahr", step=1)
            st.number_input("Ist-Kaltmiete (€/m²)", key="ist_sqm")
            st.number_input("Hausgeld (€/Monat)", key="hausgeld")
            st.number_input("Geschätzte Sanierung (€)", key="sanierung", step=2500.0)

        with st.expander("🏦 2. Deine Finanzierung & NK", expanded=False):
            st.markdown("<span class='badge-investor'>Persönliche Konditionen</span>", unsafe_allow_html=True)
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

        with st.expander("📈 3. Ziel-Miete & Betriebskosten", expanded=False):
            st.number_input("Ziel-Kaltmiete (€/m²)", key="target_sqm")
            st.number_input("Erreicht in Jahr", key="adj_year", min_value=1, max_value=10)
            st.number_input("Instandhaltung (€/m²/Jahr)", key="inst_sqm")
            st.number_input("Verwaltung (€/Monat)", key="mgt_monat")
            st.slider("Leerstandsrisiko (%)", 0.0, 0.10, key="vac_rate")

        with st.expander("⚖️ 4. Steuer & Annahmen", expanded=False):
            st.slider("Grenzsteuersatz (%)", 0.0, 0.50, key="tax_rate", step=0.01)
            st.selectbox("AfA-Modell", ["1_Linear_Standard", "2_Degressiv_§7_5a", "3_Sonder_AfA_§7b", "4_Denkmal_§7h_7i"], key="afa_model")
            st.number_input("Mietsteigerung p.a. (%)", key="miet_inc")
            st.number_input("Wertsteigerung p.a. (%)", key="val_inc")

    # PREPARE INPUT PAYLOAD
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

    # CHECK MINIMUM REQUIRED DATA (KAUFPREIS & QM MUST BE > 0)
    has_minimum_data = (st.session_state["kaufpreis"] > 0) and (st.session_state["qm"] > 0)

    if not has_minimum_data:
        # PLACEHOLDER SCREEN BEFORE DATA ENTRY
        st.markdown("""
        <div class="apple-placeholder">
            <h2 style="font-size: 2rem; font-weight: 700; color: #1d1d1f; margin-bottom: 10px;">🏢 Bereit für Ihre Immobilien-Analyse</h2>
            <p style="font-size: 1.1rem; color: #86868b; max-width: 600px; margin: 0 auto 25px auto;">
                Bitte tragen Sie in der linken Seitenleiste mindestens den <b>Kaufpreis</b> und die <b>Wohnfläche</b> ein oder nutzen Sie den <b>KI-Import</b>.
            </p>
            <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
                <span style="background:#ffffff; padding:10px 18px; border-radius:12px; border:1px solid #d2d2d7; font-weight:500;">✨ KI Link-/PDF-Import nutzen</span>
                <span style="background:#ffffff; padding:10px 18px; border-radius:12px; border:1px solid #d2d2d7; font-weight:500;">📝 Oder Objektdaten manuell eingeben</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # CALCULATE PROJECTION
        df_proj, tot_inv, ek_abs, fk_tot, irr, afa_base = calc_10y_projection(input_data)

        # HEADER TITLE & SAVE BUTTON
        obj_display_name = st.session_state['obj_name'] if st.session_state['obj_name'] else "Neues Objekt"
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.markdown(f"# 🏢 {obj_display_name}")
            st.caption(f"Standort: {st.session_state['bundesland']} | Fläche: {st.session_state['qm']:.0f} m² | Kaufpreis: {st.session_state['kaufpreis']:,.0f} €")
        with col_t2:
            current_payload = {k: st.session_state[k] for k in default_state.keys()}
            if sb_client and st.button("💾 In Cloud Speichern", type="primary", use_container_width=True):
                db_save_project(sb_client, st.session_state["user_email"], obj_display_name, current_payload)

        # STRATEGY & AMPEL SYSTEM
        strat_name = st.session_state.get("selected_strategy_name", "Konservativ / Ausgewogen (Standard)")
        strat = STRATEGIES.get(strat_name, STRATEGIES["Konservativ / Ausgewogen (Standard)"])
        
        val_cf = df_proj.loc[0, 'CF n. St.'] / 12
        val_rendite = df_proj.loc[0, 'Bruttomietrendite'] * 100
        val_roe = (df_proj.loc[0, 'CF n. St.'] / ek_abs) * 100 if ek_abs > 0 else 0.0
        hb_annu = fk_tot * (st.session_state["hb_share"]) * ((st.session_state["hb_zins"] + st.session_state["hb_tilg"]) / 100)
        kfw_annu = max(0, st.session_state["kfw_amt"] - st.session_state["kfw_grant"]) * ((st.session_state["kfw_zins"] + st.session_state["kfw_tilg"]) / 100)
        val_dscr = df_proj.loc[0, 'NOI'] / (hb_annu + kfw_annu) if (hb_annu + kfw_annu) > 0 else 1.0

        status_cf, label_cf = get_ampel_status(val_cf, strat["target_cf"], strat["tol_cf"])
        status_rendite, label_rendite = get_ampel_status(val_rendite, strat["target_rendite"], strat["tol_rendite"])
        status_roe, label_roe = get_ampel_status(val_roe, strat["target_roe"], strat["tol_roe"])
        status_dscr, label_dscr = get_ampel_status(val_dscr, strat["target_dscr"], strat["tol_dscr"])

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="ampel-card ampel-{status_cf}"><div class="ampel-title">Cashflow n. St.</div><div class="ampel-value">{val_cf:,.2f} €/M</div><div class="ampel-status">{label_cf}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="ampel-card ampel-{status_rendite}"><div class="ampel-title">Bruttomietrendite</div><div class="ampel-value">{val_rendite:.2f} %</div><div class="ampel-status">{label_rendite}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="ampel-card ampel-{status_roe}"><div class="ampel-title">EK-Rendite (ROE)</div><div class="ampel-value">{val_roe:.2f} %</div><div class="ampel-status">{label_roe}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="ampel-card ampel-{status_dscr}"><div class="ampel-title">DSCR Schuldendienst</div><div class="ampel-value">{val_dscr:.2f}</div><div class="ampel-status">{label_dscr}</div></div>', unsafe_allow_html=True)

        tab_dash, tab_plan, tab_tax, tab_stress = st.tabs(["📊 Executive Dashboard", "📅 10-Jahres Finanzplan", "⚖️ Steuer & VV-GmbH", "💣 Stresstest"])

        with tab_dash:
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                st.markdown("### Vermögensaufbau vs. Restschuld")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Objektwert'], name="Objektwert (€)", line=dict(color="#10b981", width=3)))
                fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Restschuld'], name="Restschuld (€)", line=dict(color="#ef4444", width=3)))
                fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['NAV'], name="Netto-Eigenkapital / NAV (€)", marker_color="#0066cc", opacity=0.3))
                fig.update_layout(template="plotly_white", height=380, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
                
            with col_chart2:
                st.markdown("### Kapitalstruktur")
                fig_pie = px.pie(
                    names=['Eigenkapital', 'Hausbank', 'KfW'],
                    values=[ek_abs, fk_tot * st.session_state["hb_share"], max(0, st.session_state["kfw_amt"] - st.session_state["kfw_grant"])],
                    color_discrete_sequence=['#0066cc', '#1d1d1f', '#86868b'],
                    hole=0.5
                )
                fig_pie.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_pie, use_container_width=True)

        with tab_plan:
            st.markdown("### 10-Jahres Liquiditätsverlauf")
            st.dataframe(df_proj.style.format({
                "Bruttomietrendite": "{:.2%}", "Brutto-Kaltmiete": "{:,.0f} €", "NOI": "{:,.0f} €",
                "Zinsen": "{:,.0f} €", "Tilgung": "{:,.0f} €", "CF v. St.": "{:,.0f} €",
                "AfA": "{:,.0f} €", "Steuer": "{:,.0f} €", "CF n. St.": "{:,.0f} €",
                "Restschuld": "{:,.0f} €", "Objektwert": "{:,.0f} €", "NAV": "{:,.0f} €", "LTV": "{:.1%}"
            }), use_container_width=True)

        with tab_tax:
            st.markdown("### Privatbesitz vs. VV-GmbH")
            tot_taxable = df_proj['NOI'].sum() - df_proj['Zinsen'].sum() - df_proj['AfA'].sum()
            tax_privat = tot_taxable * st.session_state["tax_rate"]
            tax_gmbh = tot_taxable * 0.15825
            c_t1, c_t2, c_t3 = st.columns(3)
            c_t1.metric("Steuer Haltephase (Privat)", f"{tax_privat:,.0f} €")
            c_t2.metric("Steuer Haltephase (VV-GmbH)", f"{tax_gmbh:,.0f} €")
            c_t3.metric("Ersparnis Haltephase GmbH", f"{tax_privat - tax_gmbh:,.0f} €")

        with tab_stress:
            st.markdown("### Refinanzierungs-Shock (Jahr 11)")
            restschuld_10 = df_proj.loc[9, 'Restschuld']
            rates = [0.035, 0.045, 0.055, 0.065, 0.075]
            refin_data = []
            for r in rates:
                new_rate = (restschuld_10 * (r + (st.session_state["hb_tilg"] / 100))) / 12
                new_dscr = df_proj.loc[9, 'NOI'] / (new_rate * 12) if new_rate > 0 else 0
                refin_data.append({"Anschluss-Zins": f"{r*100:.1f} %", "Monatliche Rate": f"{new_rate:,.2f} €", "Neuer DSCR": f"{new_dscr:.2f}"})
            st.table(pd.DataFrame(refin_data))

# =============================================================================
# MODUL 3: ⚖️ DEAL-VERGLEICH
# =============================================================================
elif nav_choice == "⚖️ Deal-Vergleich":
    st.markdown("## ⚖️ Multi-Deal Vergleich")
    st.markdown("<p style='color:#86868b;'>Vergleichen Sie bis zu 3 Objekte direkt nebeneinander.</p>", unsafe_allow_html=True)
    
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
                    st.markdown(f"<div class='apple-card'><h3>🏢 {deal_name}</h3>", unsafe_allow_html=True)
                    st.metric("Kaufpreis", f"{d.get('kaufpreis', 0):,.0f} €")
                    st.metric("Cashflow n. St.", f"{cf_m:,.2f} €/M")
                    st.metric("Bruttomietrendite", f"{rendite:.2f} %")
                    st.metric("10-Jahres IRR", f"{irr*100:.2f} %")
                    st.metric("Eigenkapital", f"{ek_abs:,.0f} €")
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("Bitte wählen Sie mindestens 2 Objekte aus.")
    else:
        st.info("💡 Sie benötigen mindestens 2 gespeicherte Objekte in der Cloud-Datenbank, um den Deal-Vergleich zu nutzen.")

# =============================================================================
# MODUL 4: 🧮 MAX. KAUFPREIS RECHNER
# =============================================================================
elif nav_choice == "🧮 Max. Kaufpreis":
    st.markdown("## 🧮 Maximaler Kaufpreis Rechner")
    st.markdown("<p style='color:#86868b;'>Ermitteln Sie Ihre Gebots-Obergrenze für Preisverhandlungen.</p>", unsafe_allow_html=True)

    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        desired_cf = st.number_input("Wunsch-Cashflow n. St. (€/Monat)", value=100.0, step=25.0)
        current_kp = st.session_state["kaufpreis"]
        st.info(f"Aktuell angesetzter Kaufpreis: **{current_kp:,.0f} €**")

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
                    
            st.metric("Maximaler Kaufpreis (Gebots-Obergrenze)", f"{best_price:,.0f} €", delta=f"{best_price - current_kp:,.0f} € zum Verkäuferpreis")
        else:
            st.warning("Bitte geben Sie zuerst Objektdaten im Analyse-Rechner ein.")

# =============================================================================
# MODUL 5: ⚙️ EINSTELLUNGEN
# =============================================================================
elif nav_choice == "⚙️ Einstellungen":
    st.markdown("## ⚙️ Einstellungen & Zugänge")
    st.markdown("<p style='color:#86868b;'>Verwalten Sie Schlüssel und Investment-Strategien.</p>", unsafe_allow_html=True)

    tab_s1, tab_s2 = st.tabs(["🔑 API-Keys & DB", "🎯 Strategien"])

    with tab_s1:
        st.markdown("### Google Gemini API Key")
        gem_secrets = st.secrets.get("GEMINI_API_KEY", "")
        if gem_secrets:
            masked_key = gem_secrets[:6] + "..." + gem_secrets[-4:] if len(gem_secrets) > 10 else "Aktiv"
            st.success(f"🟢 API-Key aktiv geladen aus Streamlit Secrets! (`{masked_key}`)")
        else:
            st.warning("⚠️ Kein Key in den Streamlit Secrets hinterlegt.")
        
        gemini_key = st.text_input("Manuell in Session überschreiben", value=st.session_state.get("gemini_api_key", ""), type="password", help="Wird nur genutzt, falls kein Key in den Secrets steht.")
        if gemini_key:
            st.session_state["gemini_api_key"] = gemini_key
            st.success("Manueller Gemini Key gespeichert!")

        st.divider()
        st.markdown("### Supabase Datenbank")
        sb_u_secrets = st.secrets.get("SUPABASE_URL", "")
        if sb_u_secrets:
            st.success("🟢 Supabase-Datenbank ist automatisch aus den Streamlit Secrets verbunden!")
            
        sb_u = st.text_input("Supabase URL (Manuell)", value=st.session_state.get("supabase_url", ""), type="password")
        sb_k = st.text_input("Supabase Anon Key (Manuell)", value=st.session_state.get("supabase_key", ""), type="password")
        if sb_u and sb_k:
            st.session_state["supabase_url"] = sb_u
            st.session_state["supabase_key"] = sb_k
            st.success("Manuelle Supabase-Verbindung gespeichert!")

    with tab_s2:
        st.markdown("### Investment-Strategie")
        chosen_strat = st.selectbox("Aktive Strategie", list(STRATEGIES.keys()), index=0)
        st.session_state["selected_strategy_name"] = chosen_strat
        
        st.json(STRATEGIES[chosen_strat])
