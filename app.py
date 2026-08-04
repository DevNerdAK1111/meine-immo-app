import streamlit as st
from core.database import get_supabase_client
from views.analyse import render_analyse_view
from views.pipeline import render_pipeline_view
from views.wissen import render_wissen_view

# 1. Konfiguration der Streamlit-Seite
st.set_page_config(
    page_title="Valuon Estate",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Supabase-Client & Session-State initialisieren
sb_client = get_supabase_client()

if "user_email" not in st.session_state:
    st.session_state["user_email"] = "developer@valuon-estate.de"

if "nav_choice" not in st.session_state:
    st.session_state["nav_choice"] = "Analyse"

# 3. Hauptnavigation in der Seitenleiste
with st.sidebar:
    st.image("https://raw.githubusercontent.com/streamlit/streamlit/main/docs/static/logo.png", width=140) # Optionales Logo / Platzhalter
    st.markdown("## Navigation")
    
    # "Vergleich" und "Kaufpreis" sind vorübergehend deaktiviert, bleiben im Code aber erhalten
    nav_options = [
        "Analyse",
        "Pipeline",
        # "Vergleich",
        # "Kaufpreis",
        "Immobilienwissen"
    ]
    
    # Sicherstellen, dass die aktuelle Auswahl in den verfügbaren Optionen liegt
    current_nav = st.session_state.get("nav_choice", "Analyse")
    if current_nav not in nav_options:
        current_nav = "Analyse"
        st.session_state["nav_choice"] = "Analyse"

    selected_page = st.radio(
        "Bereich wählen:",
        nav_options,
        index=nav_options.index(current_nav),
        key="nav_radio"
    )
    
    # Aktualisieren des Session-States bei Seitenwechsel
    if selected_page != st.session_state["nav_choice"]:
        st.session_state["nav_choice"] = selected_page
        st.rerun()

    st.divider()
    st.caption(f"Eingeloggt als: {st.session_state['user_email']}")

# 4. Seiten-Routing
if st.session_state["nav_choice"] == "Analyse":
    render_analyse_view(sb_client)

elif st.session_state["nav_choice"] == "Pipeline":
    render_pipeline_view(sb_client)

elif st.session_state["nav_choice"] == "Immobilienwissen":
    render_wissen_view()

# Fallback für deaktivierte Seiten (falls noch intern angesteuert)
elif st.session_state["nav_choice"] in ["Vergleich", "Kaufpreis"]:
    st.info("Dieser Bereich ist aktuell ausgeblendet.")
