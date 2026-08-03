import streamlit as st
from constants import STRATEGIES

def render_einstellungen_view():
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
