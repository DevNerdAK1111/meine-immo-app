import streamlit as st
from styles import load_valuon_styles
from constants import STRATEGIES, GRUNDERWERBSTEUER_MAP
from core.database import get_supabase_client
from views.pipeline import render_pipeline_view
from views.analyse import render_analyse_view
from views.vergleich import render_vergleich_view
from views.kaufpreis import render_kaufpreis_view
from views.wissen import render_wissen_view
from views.einstellungen import render_einstellungen_view

# -----------------------------------------------------------------------------
# PAGE CONFIG & DESIGN SYSTEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Valuon Estate",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

load_valuon_styles()

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
default_state = {
    "authenticated": False, "user_email": "", "gemini_api_key": "",
    "selected_strategy_name": "Konservativ / Ausgewogen (Standard)",
    "nav_choice": "Objekt Datenbank", "trigger_analysis": False, "target_auto_sync": True,
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
        if st.button("Als Entwickler einloggen (Permanenter Modus)", type="primary", use_container_width=True):
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
# MAIN APPLICATION HEADER & TOP NAVIGATION
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

# "Vergleich" und "Kaufpreis" ausblenden, ohne den Code dahinter zu löschen
nav_items = ["Objekt Datenbank", "Analyse", "Immobilienwissen", "Einstellungen"]
nav_cols = st.columns(len(nav_items))

for idx, item in enumerate(nav_items):
    is_active = (st.session_state["nav_choice"] == item)
    if nav_cols[idx].button(item, key=f"nav_btn_{idx}", type="primary" if is_active else "secondary", use_container_width=True):
        st.session_state["nav_choice"] = item
        st.rerun()

st.divider()

# -----------------------------------------------------------------------------
# ROUTING TO MODULES
# -----------------------------------------------------------------------------
nav_choice = st.session_state["nav_choice"]

if nav_choice == "Objekt Datenbank":
    render_pipeline_view(sb_client)
elif nav_choice == "Analyse":
    render_analyse_view(sb_client)
# elif nav_choice == "Vergleich":
#     render_vergleich_view()
# elif nav_choice == "Kaufpreis":
#     render_kaufpreis_view()
elif nav_choice == "Immobilienwissen":
    render_wissen_view()
elif nav_choice == "Einstellungen":
    render_einstellungen_view()
