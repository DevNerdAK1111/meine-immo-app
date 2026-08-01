import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai
from pypdf import PdfReader
import json
from supabase import create_client, Client

# -----------------------------------------------------------------------------
# PAGE CONFIG & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ImmoAnalyse Pro | PropTech AI Suite",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    
    .ampel-card {
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 6px solid;
    }
    .ampel-green { background-color: #f0fdf4; border-left-color: #22c55e; color: #14532d; }
    .ampel-yellow { background-color: #fefce8; border-left-color: #eab308; color: #713f12; }
    .ampel-red { background-color: #fef2f2; border-left-color: #ef4444; color: #7f1d1d; }
    .ampel-title { font-size: 0.85rem; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; opacity: 0.8; }
    .ampel-value { font-size: 1.5rem; font-weight: 700; }
    .ampel-status { font-size: 0.8rem; font-weight: 600; margin-top: 4px; }
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
# SUPABASE HELPERS
# -----------------------------------------------------------------------------
def get_supabase_client(url: str, key: str) -> Client:
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase Verbindungsfehler: {e}")
        return None

def db_save_project(supabase: Client, user_id: str, project_name: str, payload: dict):
    try:
        # Check if project exists for user
        res = supabase.table("projects").select("id").eq("user_id", user_id).eq("project_name", project_name).execute()
        if res.data and len(res.data) > 0:
            pid = res.data[0]["id"]
            supabase.table("projects").update({"input_data": payload}).eq("id", pid).execute()
            st.success(f"Projekt '{project_name}' erfolgreich aktualisiert!")
        else:
            supabase.table("projects").insert({
                "user_id": user_id,
                "project_name": project_name,
                "input_data": payload
            }).execute()
            st.success(f"Projekt '{project_name}' neu in Datenbank gespeichert!")
    except Exception as e:
        st.error(f"Fehler beim Speichern in DB: {e}")

def db_get_projects(supabase: Client, user_id: str):
    try:
        res = supabase.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der DB-Projekte: {e}")
        return []

def db_delete_project(supabase: Client, project_id: int):
    try:
        supabase.table("projects").delete().eq("id", project_id).execute()
        st.success("Projekt aus Datenbank gelöscht!")
    except Exception as e:
        st.error(f"Fehler beim Löschen: {e}")

# -----------------------------------------------------------------------------
# CALCULATION & AI FUNCTIONS
# -----------------------------------------------------------------------------
def get_ampel_status(val, target_green, target_yellow):
    if val >= target_green:
        return "green", "🟢 Ziel erfüllt"
    elif val >= target_yellow:
        return "yellow", "🟡 Toleranzbereich"
    else:
        return "red", "🔴 Kriterium verfehlt"

def analyze_pdf_with_gemini(api_key, pdf_file):
    try:
        genai.configure(api_key=api_key)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        prompt = f"""
        Du bist ein Immobilien-Experte. Analysiere den folgenden Exposé-Text und extrahiere die Daten als valides JSON.
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

        Exposé-Text:
        {text[:6000]}
        """
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
                
        if not response or not response.text:
            st.error("Keine Antwort von der KI erhalten.")
            return None

        cleaned_json = response.text.replace('```json', '').replace('```', '').strip()
        start_idx = cleaned_json.find('{')
        end_idx = cleaned_json.rfind('}')
        if start_idx != -1 and end_idx != -1:
            cleaned_json = cleaned_json[start_idx:end_idx+1]
            
        return json.loads(cleaned_json)
    except Exception as e:
        st.error(f"Fehler bei der KI-Analyse: {str(e)}")
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
    
    hb_rate = hb_loan * (data['hb_zins'] + data['hb_tilg'])
    kfw_rate = kfw_loan * (data['kfw_zins'] + data['kfw_tilg']) if kfw_loan > 0 else 0
    
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
        restschuld_kfw = max(0, restschuld_kfw - tilg_kfw)
        restschuld_tot = restschuld_hb + restschuld_kfw
        
        obj_val *= (1 + data['val_inc'])
        nav = obj_val - restschuld_tot
        ltv = restschuld_tot / obj_val if obj_val > 0 else 0
        
        rows.append({
            "Jahr": yr,
            "Bruttomietrendite": gross_rent / kp,
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

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION FOR FORM FIELDS
# -----------------------------------------------------------------------------
if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = ""

# Default Input State
default_state = {
    "obj_name": "MFH Musterstraße 12", "bundesland": "Niedersachsen", "kaufpreis": 350000.0,
    "qm": 120.0, "baujahr": 1998, "sanierung": 35000.0, "grund_anteil": 0.20,
    "notar_p": 1.5, "makler_p": 3.57, "sonst_nk": 1000.0, "disagio_p": 0.0,
    "ek_quote": 0.20, "hb_share": 0.80, "hb_zins": 3.8, "hb_tilg": 2.0, "grace_years": 0,
    "kfw_amt": 50000.0, "kfw_zins": 2.1, "kfw_tilg": 3.0, "kfw_grant": 5000.0, "sondertilg": 2000.0,
    "ist_sqm": 9.50, "target_sqm": 12.00, "adj_year": 3, "park": 50.0, "vac_rate": 0.02,
    "hausgeld": 45.0, "inst_sqm": 10.0, "mgt_monat": 25.0, "capex_j3": 5000.0, "capex_j6": 0.0,
    "tax_rate": 0.42, "afa_model": "1_Linear_Standard", "afa_lin": 2.0, "miet_inc": 1.5,
    "cost_inc": 2.0, "val_inc": 1.5, "wacc": 6.0, "exit_cost": 2.0
}

for k, v in default_state.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -----------------------------------------------------------------------------
# SIDEBAR / NAVIGATION & DATABASE
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🏢 ImmoAnalyse Pro")
    st.caption("Institutional Investment & AI Suite")

    # EXPANDER: DATENBANK & PROJEKT-VERWALTUNG
    with st.expander("☁️ **Datenbank & Projekte**", expanded=False):
        user_id = st.text_input("Nutzer ID / Email", value="demo_user", help="Eindeutige Kennung für Ihre Projekte")
        
        # Check Streamlit Secrets or manual input for Supabase
        sb_url = st.secrets.get("SUPABASE_URL", "") if "SUPABASE_URL" in st.secrets else st.text_input("Supabase URL", type="password")
        sb_key = st.secrets.get("SUPABASE_KEY", "") if "SUPABASE_KEY" in st.secrets else st.text_input("Supabase Anon Key", type="password")
        
        sb_client = None
        if sb_url and sb_key:
            sb_client = get_supabase_client(sb_url, sb_key)
            if sb_client:
                st.caption("🟢 Supabase Cloud verbunden")

        st.divider()
        st.markdown("**📂 Gespeicherte Projekte:**")
        
        if sb_client:
            projects = db_get_projects(sb_client, user_id)
            if projects:
                proj_names = [p["project_name"] for p in projects]
                selected_p = st.selectbox("Projekt auswählen", proj_names)
                
                col_p1, col_p2 = st.columns(2)
                if col_p1.button("📥 Laden"):
                    p_obj = next(p for p in projects if p["project_name"] == selected_p)
                    for k, v in p_obj["input_data"].items():
                        st.session_state[k] = v
                    st.success(f"'{selected_p}' geladen!")
                    st.rerun()
                    
                if col_p2.button("🗑️ Löschen"):
                    p_obj = next(p for p in projects if p["project_name"] == selected_p)
                    db_delete_project(sb_client, p_obj["id"])
                    st.rerun()
            else:
                st.info("Noch keine Projekte in DB.")
        else:
            st.info("Geben Sie Supabase-Keys ein, um Projekte in der Cloud zu speichern.")

        st.divider()
        st.markdown("**📤 JSON Backup (Ohne DB):**")
        
        # Current input dictionary for saving
        current_payload = {k: st.session_state[k] for k in default_state.keys()}
        
        if sb_client and st.button("💾 In Cloud-DB Speichern"):
            db_save_project(sb_client, user_id, st.session_state["obj_name"], current_payload)

        # JSON Download Button
        st.download_button(
            label="💾 JSON Herunterladen",
            data=json.dumps(current_payload, indent=2),
            file_name=f"{st.session_state['obj_name'].replace(' ', '_')}.json",
            mime="application/json"
        )
        
        uploaded_json = st.file_uploader("📂 JSON Datei laden", type=["json"])
        if uploaded_json:
            try:
                loaded_dict = json.load(uploaded_json)
                for k, v in loaded_dict.items():
                    if k in st.session_state:
                        st.session_state[k] = v
                st.success("JSON erfolgreich importiert!")
                st.rerun()
            except Exception as e:
                st.error("Fehler beim JSON Import.")

    # EXPANDER: STRATEGIE & ZIEL-KPIS
    with st.expander("🎯 **Strategie & Ziel-KPIs (Ampelsystem)**", expanded=False):
        selected_strategy = st.selectbox("Investment-Strategie", list(STRATEGIES.keys()) + ["Benutzerdefiniert"])
        
        if selected_strategy != "Benutzerdefiniert":
            strat = STRATEGIES[selected_strategy]
            target_cf, tol_cf = strat["target_cf"], strat["tol_cf"]
            target_rendite, tol_rendite = strat["target_rendite"], strat["tol_rendite"]
            target_roe, tol_roe = strat["target_roe"], strat["tol_roe"]
            target_dscr, tol_dscr = strat["target_dscr"], strat["tol_dscr"]
        else:
            target_cf = st.number_input("Ziel Cashflow (€/M)", value=50.0)
            tol_cf = st.number_input("Toleranz Cashflow (€/M)", value=0.0)
            target_rendite = st.number_input("Ziel Rendite (%)", value=4.5)
            tol_rendite = st.number_input("Toleranz Rendite (%)", value=3.8)
            target_roe = st.number_input("Ziel ROE (%)", value=8.0)
            tol_roe = st.number_input("Toleranz ROE (%)", value=4.0)
            target_dscr = st.number_input("Ziel DSCR", value=1.20)
            tol_dscr = st.number_input("Toleranz DSCR", value=1.05)

    st.subheader("🤖 KI-Import")
    api_key_input = st.text_input("Gemini API Key", value=st.session_state["gemini_api_key"], type="password")
    if api_key_input:
        st.session_state["gemini_api_key"] = api_key_input
        
    uploaded_pdf = st.file_uploader("Exposé PDF hochladen", type=["pdf"])
    
    if uploaded_pdf and st.session_state["gemini_api_key"]:
        if st.button("✨ Exposé per KI analysieren"):
            with st.spinner("Lese PDF..."):
                ai_data = analyze_pdf_with_gemini(st.session_state["gemini_api_key"], uploaded_pdf)
                if ai_data:
                    if ai_data.get("kaufpreis"): st.session_state["kaufpreis"] = float(ai_data["kaufpreis"])
                    if ai_data.get("wohnflaeche"): st.session_state["qm"] = float(ai_data["wohnflaeche"])
                    if ai_data.get("baujahr"): st.session_state["baujahr"] = int(ai_data["baujahr"])
                    if ai_data.get("ist_miete_sqm"): st.session_state["ist_sqm"] = float(ai_data["ist_miete_sqm"])
                    if ai_data.get("hausgeld_monat"): st.session_state["hausgeld"] = float(ai_data["hausgeld_monat"])
                    if ai_data.get("objektname"): st.session_state["obj_name"] = str(ai_data["objektname"])
                    st.success("KI-Daten in Formular übernommen!")
                    st.rerun()

    st.divider()
    st.subheader("1. Stammdaten")
    st.text_input("Objektname", key="obj_name")
    st.selectbox("Bundesland", list(GRUNDERWERBSTEUER_MAP.keys()), key="bundesland")
    st.number_input("Kaufpreis (€)", key="kaufpreis", step=10000.0)
    st.number_input("Wohnfläche (m²)", key="qm", step=5.0)
    st.number_input("Baujahr", key="baujahr", step=1)
    st.number_input("Sanierungskosten J1-3 (€)", key="sanierung", step=5000.0)
    st.slider("Grundstücksanteil (%)", 0.0, 0.50, key="grund_anteil", step=0.05)

    st.subheader("2. Kaufnebenkosten")
    st.number_input("Notar & Grundbuch (%)", key="notar_p")
    st.number_input("Makler (%)", key="makler_p")
    st.number_input("Sonstige Nebenkosten (€)", key="sonst_nk")
    st.number_input("Disagio (%)", key="disagio_p")

    st.subheader("3. Finanzierung")
    st.slider("Eigenkapitalquote (%)", 0.0, 0.50, key="ek_quote", step=0.05)
    st.slider("Anteil Hausbank (%)", 0.50, 1.0, key="hb_share", step=0.05)
    st.number_input("Hausbank Zins (%)", key="hb_zins")
    st.number_input("Hausbank Tilgung (%)", key="hb_tilg")
    st.number_input("Tilgungsfreie Jahre", key="grace_years", min_value=0, max_value=5)
    
    st.number_input("KfW Darlehen (€)", key="kfw_amt", step=10000.0)
    st.number_input("KfW Zins (%)", key="kfw_zins")
    st.number_input("KfW Tilgung (%)", key="kfw_tilg")
    st.number_input("KfW Tilgungszuschuss (€)", key="kfw_grant")
    st.number_input("Sondertilgung (€/Jahr)", key="sondertilg", step=500.0)

    st.subheader("4. Mieten & Betriebskosten")
    st.number_input("Ist-Kaltmiete (€/m²)", key="ist_sqm")
    st.number_input("Ziel-Kaltmiete (€/m²)", key="target_sqm")
    st.number_input("Jahr der Ziel-Miete", key="adj_year", min_value=1, max_value=10)
    st.number_input("Sonstige Miete/Monat (€)", key="park")
    st.slider("Leerstandsquote (%)", 0.0, 0.10, key="vac_rate")
    
    st.number_input("Nicht umlegb. Hausgeld (€/Monat)", key="hausgeld")
    st.number_input("Instandhaltung (€/m²/Jahr)", key="inst_sqm")
    st.number_input("Verwaltung (€/Monat)", key="mgt_monat")
    st.number_input("CapEx Instandhaltung Jahr 3 (€)", key="capex_j3")
    st.number_input("CapEx Instandhaltung Jahr 6 (€)", key="capex_j6")

    st.subheader("5. Steuer & Makro")
    st.slider("Persönlicher Grenzsteuersatz (%)", 0.0, 0.50, key="tax_rate", step=0.01)
    st.selectbox("AfA-Modell", ["1_Linear_Standard", "2_Degressiv_§7_5a", "3_Sonder_AfA_§7b", "4_Denkmal_§7h_7i"], key="afa_model")
    st.number_input("Linearer AfA-Satz (%)", key="afa_lin")
    st.number_input("Mietsteigerung p.a. (%)", key="miet_inc")
    st.number_input("Cost Inflation p.a. (%)", key="cost_inc")
    st.number_input("Wertsteigerung p.a. (%)", key="val_inc")
    st.number_input("WACC / Diskontierung (%)", key="wacc")
    st.number_input("Verkaufsnebenkosten (%)", key="exit_cost")

# Pack inputs into dict for calculation
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
    'target_sqm': st.session_state["target_sqm"], 'adj_year': st.session_state["adj_year"],
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

df_proj, tot_inv, ek_abs, fk_tot, irr, afa_base = calc_10y_projection(input_data)

# -----------------------------------------------------------------------------
# MAIN CONTENT DASHBOARD
# -----------------------------------------------------------------------------
st.title(f"🏢 {st.session_state['obj_name']}")
st.caption(f"Standort: {st.session_state['bundesland']} | Wohnfläche: {st.session_state['qm']:.0f} m² | Baujahr: {st.session_state['baujahr']} | Strategie: **{selected_strategy}**")

# KERN-KPIS & AMPEL
val_cf = df_proj.loc[0, 'CF n. St.'] / 12
val_rendite = df_proj.loc[0, 'Bruttomietrendite'] * 100
val_roe = (df_proj.loc[0, 'CF n. St.'] / ek_abs) * 100
hb_annu = fk_tot * (st.session_state["hb_share"] * 100 / 100) * ((st.session_state["hb_zins"] + st.session_state["hb_tilg"]) / 100)
kfw_annu = max(0, st.session_state["kfw_amt"] - st.session_state["kfw_grant"]) * ((st.session_state["kfw_zins"] + st.session_state["kfw_tilg"]) / 100)
val_dscr = df_proj.loc[0, 'NOI'] / (hb_annu + kfw_annu) if (hb_annu + kfw_annu) > 0 else 1.0

status_cf, label_cf = get_ampel_status(val_cf, target_cf, tol_cf)
status_rendite, label_rendite = get_ampel_status(val_rendite, target_rendite, tol_rendite)
status_roe, label_roe = get_ampel_status(val_roe, target_roe, tol_roe)
status_dscr, label_dscr = get_ampel_status(val_dscr, target_dscr, tol_dscr)

statuses = [status_cf, status_rendite, status_roe, status_dscr]

if statuses.count("green") == 4:
    st.success("🟢 **TOP DEAL:** Dieses Objekt erfüllt exakt alle Kriterien deiner gewählten Strategie!")
elif "red" in statuses:
    red_count = statuses.count("red")
    st.error(f"🔴 **DEAL-BREAKER / PRÜFBEDARF:** Das Objekt verfehlt {red_count} wichtige(s) Ziel-Kriterium/Kriterien deiner Strategie.")
else:
    st.warning("🟡 **AKZEPTABEL / TOLERANZ:** Das Objekt liegt in allen Punkten im Toleranzbereich.")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="ampel-card ampel-{status_cf}">
        <div class="ampel-title">Cashflow n. St.</div>
        <div class="ampel-value">{val_cf:,.2f} €/M</div>
        <div class="ampel-status">{label_cf} (Ziel: ≥ {target_cf:,.0f} €)</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="ampel-card ampel-{status_rendite}">
        <div class="ampel-title">Bruttomietrendite</div>
        <div class="ampel-value">{val_rendite:.2f} %</div>
        <div class="ampel-status">{label_rendite} (Ziel: ≥ {target_rendite:.1f} %)</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="ampel-card ampel-{status_roe}">
        <div class="ampel-title">EK-Rendite (ROE)</div>
        <div class="ampel-value">{val_roe:.2f} %</div>
        <div class="ampel-status">{label_roe} (Ziel: ≥ {target_roe:.1f} %)</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="ampel-card ampel-{status_dscr}">
        <div class="ampel-title">DSCR Schuldendienst</div>
        <div class="ampel-value">{val_dscr:.2f}</div>
        <div class="ampel-status">{label_dscr} (Ziel: ≥ {target_dscr:.2f})</div>
    </div>
    """, unsafe_allow_html=True)

limit_15 = afa_base * 0.15
if st.session_state["sanierung"] > limit_15:
    st.warning(f"⚠️ **§6 EStG 15%-Hürde überschritten:** Ihre Sanierungskosten ({st.session_state['sanierung']:,.0f} €) liegen über der 15%-Grenze ({limit_15:,.0f} €). Diese müssen über 50 Jahre aktiviert werden.")

tab_dash, tab_plan, tab_tax, tab_stress = st.tabs([
    "📊 Executive Dashboard", "📅 10-Jahres Finanzplan", "⚖️ Steuer & VV-GmbH", "💣 Stresstest & Refinanzierung"
])

with tab_dash:
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        st.subheader("Vermögensaufbau vs. Restschuld")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Objektwert'], name="Objektwert (€)", line=dict(color="#10b981", width=3)))
        fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Restschuld'], name="Restschuld (€)", line=dict(color="#ef4444", width=3)))
        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['NAV'], name="Netto-Eigenkapital / NAV (€)", marker_color="#3b82f6", opacity=0.4))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
    with col_chart2:
        st.subheader("Gesamtinvestition & Kapital")
        fig_pie = px.pie(
            names=['Eigenkapital', 'Hausbank Darlehen', 'KfW Darlehen'],
            values=[ek_abs, fk_tot * (st.session_state["hb_share"]), max(0, st.session_state["kfw_amt"] - st.session_state["kfw_grant"])],
            color_discrete_sequence=['#3b82f6', '#0f172a', '#06b6d4'],
            hole=0.4
        )
        fig_pie.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

with tab_plan:
    st.subheader("Dynamischer 10-Jahres Liquiditätsverlauf")
    st.dataframe(df_proj.style.format({
        "Bruttomietrendite": "{:.2%}", "Brutto-Kaltmiete": "{:,.0f} €", "NOI": "{:,.0f} €",
        "Zinsen": "{:,.0f} €", "Tilgung": "{:,.0f} €", "CF v. St.": "{:,.0f} €",
        "AfA": "{:,.0f} €", "Steuer": "{:,.0f} €", "CF n. St.": "{:,.0f} €",
        "Restschuld": "{:,.0f} €", "Objektwert": "{:,.0f} €", "NAV": "{:,.0f} €", "LTV": "{:.1%}"
    }), use_container_width=True)

with tab_tax:
    st.subheader("Rechtsform-Vergleich: Privatbesitz vs. VV-GmbH")
    tot_taxable = df_proj['NOI'].sum() - df_proj['Zinsen'].sum() - df_proj['AfA'].sum()
    tax_privat = tot_taxable * (st.session_state["tax_rate"])
    tax_gmbh = tot_taxable * 0.15825
    
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Steuer Haltephase (Privat)", f"{tax_privat:,.0f} €")
    col_t2.metric("Steuer Haltephase (VV-GmbH)", f"{tax_gmbh:,.0f} €")
    col_t3.metric("Ersparnis Haltephase GmbH", f"{tax_privat - tax_gmbh:,.0f} €", delta_color="normal")
    
    st.info("💡 **GmbH-Fazit:** Eine VV-GmbH spart in der Haltephase erhebliche Ertragsteuern. Beachten Sie jedoch den steuerfreien Verkauf nach 10 Jahren im Privatbesitz (§23 EStG).")

with tab_stress:
    st.subheader("Refinanzierungs-Shock (Zinsbindungsszenario Jahr 11)")
    restschuld_10 = df_proj.loc[9, 'Restschuld']
    st.write(f"Verbleibende Restschuld nach 10 Jahren: **{restschuld_10:,.2f} €**")
    
    rates = [0.035, 0.045, 0.055, 0.065, 0.075]
    refin_data = []
    for r in rates:
        new_rate = (restschuld_10 * (r + (st.session_state["hb_tilg"] / 100))) / 12
        new_dscr = df_proj.loc[9, 'NOI'] / (new_rate * 12) if new_rate > 0 else 0
        refin_data.append({
            "Anschluss-Zinssatz": f"{r*100:.1f} %",
            "Neue Monatliche Rate": f"{new_rate:,.2f} €",
            "Neuer DSCR": f"{new_dscr:.2f}",
            "Status": "✅ Tragfähig" if new_dscr >= 1.15 else "⚠️ Risiko"
        })
    st.table(pd.DataFrame(refin_data))
