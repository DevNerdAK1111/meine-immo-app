import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pypdf import PdfReader

from constants import GRUNDERWERBSTEUER_MAP, OBJEKTARTEN, STRATEGIES
from core.helpers import (
    fmt_eur, fmt_sqm, fmt_de, fmt_pct, 
    get_smart_defaults, update_smart_defaults, update_grwt_from_bundesland,
    update_ist_from_monat, update_ist_from_sqm, update_target_from_monat,
    update_target_from_sqm, update_qm_callback, check_input_sanity
)
from core.ai_service import get_gemini_api_key, fetch_text_from_url, analyze_text_with_gemini
from core.calculations import calc_projection, get_metric_status
from core.database import db_save_project

def render_analyse_view(sb_client):
    with st.sidebar:
        st.markdown("<span class='badge-expose'>1. Objektdaten (Exposé)</span>", unsafe_allow_html=True)
        with st.expander("KI-gestützter Import (Beta)", expanded=False):
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
            with st.expander("Hausgeld-Aufteilung", expanded=False):
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
            
            with st.expander("KfW-Darlehen (Optional)", expanded=False):
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
            
            afa_options = [
                "Linear Standard", 
                "Degressiv (Paragraph 7 Abs. 5a EStG)", 
                "Sonder-AfA (Paragraph 7b EStG)", 
                "Denkmal-AfA (Paragraph 7h/7i EStG)"
            ]
            afa_map_to_internal = {
                "Linear Standard": "1_Linear_Standard",
                "Degressiv (Paragraph 7 Abs. 5a EStG)": "2_Degressiv_§7_5a",
                "Sonder-AfA (Paragraph 7b EStG)": "3_Sonder_AfA_§7b",
                "Denkmal-AfA (Paragraph 7h/7i EStG)": "4_Denkmal_§7h_7i"
            }
            afa_map_to_display = {v: k for k, v in afa_map_to_internal.items()}
            
            current_afa = st.session_state.get("afa_model", "1_Linear_Standard")
            current_display = afa_map_to_display.get(current_afa, "Linear Standard")
            
            selected_display = st.selectbox("AfA-Modell", afa_options, index=afa_options.index(current_display) if current_display in afa_options else 0)
            internal_afa_model = afa_map_to_internal[selected_display]
            st.session_state["afa_model"] = internal_afa_model
            
            if internal_afa_model == "1_Linear_Standard":
                st.number_input("AfA linear (%)", key="afa_lin", step=0.1, format="%.2f", value=st.session_state.get("afa_lin", 2.0))
            
            st.number_input("Mietsteigerung p.a. (%)", key="miet_inc", step=0.1, format="%.2f")
            st.number_input("Wertsteigerung p.a. (%)", key="val_inc", step=0.1, format="%.2f")

        st.divider()
        if st.button("Analyse starten / aktualisieren", type="primary", use_container_width=True):
            st.session_state["trigger_analysis"] = True
            st.rerun()

    target_sqm_resolved = st.session_state["target_sqm"] if st.session_state["target_sqm"] > 0 else st.session_state["ist_sqm"]
    
    input_data = {
        'obj_name': st.session_state.get("obj_name", ""),
        'objektart': st.session_state.get("objektart", "Eigentumswohnung"),
        'bundesland': st.session_state.get("bundesland", "Niedersachsen"),
        'stadt': st.session_state.get("stadt", ""),
        'stadtteil': st.session_state.get("stadtteil", ""),
        'kaufpreis': st.session_state.get("kaufpreis", 0.0),
        'qm': st.session_state.get("qm", 0.0),
        'baujahr': st.session_state.get("baujahr", 2000),
        'sanierung': st.session_state.get("sanierung", 0.0),
        'ist_miete_monat': st.session_state.get("ist_miete_monat", 0.0),
        'ist_sqm': st.session_state.get("ist_sqm", 0.0),
        'hausgeld': st.session_state.get("hausgeld", 0.0),
        'hausgeld_nicht_umlegbar': st.session_state.get("hausgeld_nicht_umlegbar", 0.0),
        'grwt_p': st.session_state.get("grwt_p", 5.0),
        'notar_p': st.session_state.get("notar_p", 2.0),
        'makler_p': st.session_state.get("makler_p", 3.57),
        'sonst_nk': st.session_state.get("sonst_nk", 0.0),
        'disagio_p': st.session_state.get("disagio_p", 0.0),
        'ek_euro': st.session_state.get("ek_euro", 0.0),
        'ek_quote': st.session_state.get("ek_quote", 0.20),
        'loan_type': st.session_state.get("loan_type", "Annuitätendarlehen"),
        'hb_zins': st.session_state.get("hb_zins", 3.8),
        'hb_tilg': st.session_state.get("hb_tilg", 2.0),
        'grace_years': st.session_state.get("grace_years", 0),
        'kfw_amt': st.session_state.get("kfw_amt", 0.0),
        'kfw_zins': st.session_state.get("kfw_zins", 2.1),
        'kfw_tilg': st.session_state.get("kfw_tilg", 3.0),
        'kfw_grace_years': st.session_state.get("kfw_grace_years", 0),
        'kfw_grant': st.session_state.get("kfw_grant", 0.0),
        'sondertilg': st.session_state.get("sondertilg", 0.0),
        'target_miete_monat': st.session_state.get("target_miete_monat", 0.0),
        'target_sqm': target_sqm_resolved,
        'adj_year': st.session_state.get("adj_year", 3),
        'park': st.session_state.get("park", 0.0),
        'vac_rate_pct': st.session_state.get("vac_rate_pct", 2.0),
        'inst_sqm': st.session_state.get("inst_sqm", 12.0),
        'mgt_monat': st.session_state.get("mgt_monat", 30.0),
        'capex_j3': st.session_state.get("capex_j3", 0.0),
        'capex_j6': st.session_state.get("capex_j6", 0.0),
        'tax_rate_pct': st.session_state.get("tax_rate_pct", 42.0),
        'afa_model': st.session_state.get("afa_model", "1_Linear_Standard"),
        'afa_lin': st.session_state.get("afa_lin", 2.0),
        'miet_inc': st.session_state.get("miet_inc", 1.5),
        'cost_inc': st.session_state.get("cost_inc", 2.0),
        'val_inc': st.session_state.get("val_inc", 1.5),
        'wacc': st.session_state.get("wacc", 6.0),
        'exit_cost': st.session_state.get("exit_cost", 2.0),
        'grund_anteil': st.session_state.get("grund_anteil", 0.20)
    }

    calc_data = {
        'kaufpreis': input_data['kaufpreis'], 'sanierung': input_data['sanierung'],
        'bundesland': input_data['bundesland'], 'stadt': input_data['stadt'], 'stadtteil': input_data['stadtteil'],
        'objektart': input_data['objektart'], 'grwt_proz': input_data['grwt_p'] / 100,
        'notar_proz': input_data['notar_p'] / 100, 'makler_proz': input_data['makler_p'] / 100,
        'sonst_nk': input_data['sonst_nk'], 'disagio_proz': input_data['disagio_p'] / 100,
        'ek_euro': input_data['ek_euro'], 'ek_quote': input_data['ek_quote'],
        'loan_type': input_data['loan_type'], 'hb_zins': input_data['hb_zins'] / 100,
        'hb_tilg': input_data['hb_tilg'] / 100, 'grace_years': input_data['grace_years'],
        'kfw_amt': input_data['kfw_amt'], 'kfw_zins': input_data['kfw_zins'] / 100,
        'kfw_tilg': input_data['kfw_tilg'] / 100, 'kfw_grace_years': input_data['kfw_grace_years'],
        'kfw_grant': input_data['kfw_grant'], 'sondertilg': input_data['sondertilg'],
        'ist_sqm': input_data['ist_sqm'], 'target_sqm': input_data['target_sqm'],
        'adj_year': input_data['adj_year'], 'park': input_data['park'],
        'vac_rate': input_data['vac_rate_pct'] / 100, 'qm': input_data['qm'],
        'hausgeld': input_data['hausgeld'], 'hausgeld_nicht_umlegbar': input_data['hausgeld_nicht_umlegbar'],
        'inst_sqm': input_data['inst_sqm'], 'mgt_monat': input_data['mgt_monat'],
        'capex_j3': input_data['capex_j3'], 'capex_j6': input_data['capex_j6'],
        'tax_rate': input_data['tax_rate_pct'] / 100, 'afa_model': input_data['afa_model'],
        'afa_lin': input_data['afa_lin'] / 100, 'miet_inc': input_data['miet_inc'] / 100,
        'cost_inc': input_data['cost_inc'] / 100, 'val_inc': input_data['val_inc'] / 100,
        'wacc': input_data['wacc'] / 100, 'exit_cost': input_data['exit_cost'] / 100,
        'grund_anteil': input_data['grund_anteil']
    }

    if not st.session_state.get("trigger_analysis", False):
        st.markdown("""
        <div class="valuon-placeholder">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #13381A; margin-bottom: 10px;">Berechnung ausführen</h2>
            <p style="font-size: 1.05rem; color: #555759; max-width: 620px; margin: 0 auto 15px auto;">
                Tragen Sie Ihre Objektdaten ein und klicken Sie in der Seitenleiste auf <b>"Analyse starten"</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        if st.session_state["kaufpreis"] <= 0 or st.session_state["qm"] <= 0 or st.session_state["ist_sqm"] <= 0:
            st.error("Bitte füllen Sie Kaufpreis, Wohnfläche und Miete aus.")
        else:
            col_hor1, _ = st.columns([2, 2])
            horizon_choice = col_hor1.selectbox("Projektionshorizont:", ["10 Jahre (Standard)", "Bis zur vollen Abzahlung des Darlehens (Volltilgung)"])
            full_rep = ("Volltilgung" in horizon_choice)

            df_proj, tot_inv, ek_abs, fk_tot, irr, afa_base, ek_quote_calc = calc_projection(calc_data, full_repayment=full_rep)

            sanity_warnings = check_input_sanity(calc_data)
            if sanity_warnings:
                for w in sanity_warnings:
                    st.warning(f"Plausibilitäts-Hinweis: {w}")

            obj_name = st.session_state['obj_name'] or "Unbenanntes Objekt"
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                st.markdown(f"# {obj_name}")
                st.caption(f"Kaufpreis: {fmt_eur(st.session_state['kaufpreis'])} | EK: {fmt_eur(ek_abs)} ({fmt_pct(ek_quote_calc*100)})")
            with col_t2:
                if st.button("In Datenbank speichern", type="primary", use_container_width=True):
                    success, msg = db_save_project(sb_client, st.session_state["user_email"], obj_name, input_data)
                    st.session_state["db_save_status"] = (success, msg)
                    st.rerun()

            if "db_save_status" in st.session_state:
                success, msg = st.session_state["db_save_status"]
                bg_color = "#EBF2EC" if success else "#FDF3F2"
                border_color = "#13381A" if success else "#8b3a2b"
                text_color = "#13381A" if success else "#6b2e22"
                st.markdown(f"""
                <div style="background-color: {bg_color}; border: 1px solid {border_color}; color: {text_color}; padding: 12px 16px; border-radius: 10px; font-weight: 500; margin-bottom: 20px; font-size: 0.9rem;">
                    {msg}
                </div>
                """, unsafe_allow_html=True)

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
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.markdown("### Projektion & Wertentwicklung")
                    chart_mode = st.selectbox("Grafik-Ansicht wählen:", [
                        "1. Vermögensstruktur & NAV (Netto-Eigenkapital)",
                        "2. Cashflow-Entwicklung (Vor & Nach Steuern)",
                        "3. Kapitaldienst (Zins- & Tilgungsverlauf)"
                    ], key="chart_mode_select")
                    
                    fig = go.Figure()
                    if "1." in chart_mode:
                        fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Objektwert'], name="Objektwert", line=dict(color="#13381A", width=3), hovertemplate="<b>Jahr %{x}</b><br>Objektwert: %{y:,.0f} €<extra></extra>"))
                        fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Restschuld'], name="Restschuld", line=dict(color="#8b3a2b", width=3), hovertemplate="<b>Jahr %{x}</b><br>Restschuld: %{y:,.0f} €<extra></extra>"))
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['NAV'], name="Netto-Eigenkapital (NAV)", marker_color="#A37841", opacity=0.85, hovertemplate="<b>Jahr %{x}</b><br>NAV: %{y:,.0f} €<extra></extra>"))
                        fig.update_layout(barmode='group')
                    elif "2." in chart_mode:
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['CF v. St.'], name="CF vor Steuern", marker_color="#13381A", hovertemplate="<b>Jahr %{x}</b><br>CF vor Steuern: %{y:,.0f} €<extra></extra>"))
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['CF n. St.'], name="CF nach Steuern", marker_color="#A37841", hovertemplate="<b>Jahr %{x}</b><br>CF nach Steuern: %{y:,.0f} €<extra></extra>"))
                        fig.update_layout(barmode='group')
                    else:
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['Zinsen'], name="Zinsaufwand", marker_color="#8b3a2b", hovertemplate="<b>Jahr %{x}</b><br>Zinsen: %{y:,.0f} €<extra></extra>"))
                        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['Tilgung'], name="Tilgungsleistung", marker_color="#13381A", hovertemplate="<b>Jahr %{x}</b><br>Tilgung: %{y:,.0f} €<extra></extra>"))
                        fig.update_layout(barmode='stack')

                    fig.update_layout(
                        template="plotly_white", 
                        height=380, 
                        margin=dict(l=20, r=20, t=20, b=40), 
                        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5), 
                        yaxis=dict(tickformat=",.0f", ticksuffix=" €")
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                with col_chart2:
                    st.markdown("### Kapitalstruktur (Initial)")
                    st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)
                    
                    fig_pie = px.pie(
                        names=['Eigenkapital', 'Hausbank-Darlehen', 'KfW-Darlehen'], 
                        values=[ek_abs, hb_loan_val, kfw_amt_val], 
                        color_discrete_sequence=['#13381A', '#2B2D2F', '#A37841'], 
                        hole=0.6
                    )
                    fig_pie.update_traces(
                        hovertemplate="<b>%{label}</b><br>Anteil: %{value:,.0f} € (%{percent})<extra></extra>"
                    )
                    fig_pie.update_layout(
                        template="plotly_white",
                        height=380, 
                        margin=dict(l=20, r=20, t=20, b=40),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

            with tab_plan:
                st.markdown("### Liquiditätsverlauf, steuerliche Abschreibung & Kapitalentwicklung")
                st.markdown("<p style='color:#555759; font-size: 0.9rem; margin-bottom: 15px;'>Wählen Sie einen Themenbereich, um alle Kennzahlen übersichtlich und vollständig ohne Scrollen zu betrachten.</p>", unsafe_allow_html=True)
                
                df_display = df_proj.rename(columns={
                    "Bruttomietrendite": "Mietrendite (brutto)",
                    "Brutto-Kaltmiete": "Kaltmiete (brutto)",
                    "NOI": "Reinertrag (NOI)",
                    "Zinsen": "Zinsaufwand",
                    "Tilgung": "Tilgungsleistung",
                    "CF v. St.": "Cashflow (vor St.)",
                    "AfA": "Abschreibung (AfA)",
                    "Steuer": "Einkommensteuer",
                    "CF n. St.": "Cashflow (nach St.)",
                    "Restschuld": "Restschuld",
                    "Objektwert": "Objektwert",
                    "NAV": "Netto-EK (NAV)",
                    "LTV": "Beleihungsauslauf (LTV)"
                })
                
                table_height = (len(df_display) + 2) * 35 + 38
                
                sub_t1, sub_t2, sub_t3 = st.tabs(["Mieten & Cashflow", "Kapitaldienst & Steuern", "Vermögen & Bilanz"])
                
                with sub_t1:
                    cols_1 = ["Jahr", "Mietrendite (brutto)", "Kaltmiete (brutto)", "Reinertrag (NOI)", "Cashflow (vor St.)", "Cashflow (nach St.)"]
                    df_s1 = df_display[cols_1].set_index("Jahr").copy()
                    df_s1.index.name = None
                    
                    tot_s1 = {
                        "Mietrendite (brutto)": df_s1["Mietrendite (brutto)"].mean(),
                        "Kaltmiete (brutto)": df_s1["Kaltmiete (brutto)"].sum(),
                        "Reinertrag (NOI)": df_s1["Reinertrag (NOI)"].sum(),
                        "Cashflow (vor St.)": df_s1["Cashflow (vor St.)"].sum(),
                        "Cashflow (nach St.)": df_s1["Cashflow (nach St.)"].sum()
                    }
                    df_s1.loc["Summe / Ø"] = tot_s1
                    
                    st.dataframe(df_s1.style.format({
                        "Mietrendite (brutto)": lambda x: fmt_pct(x*100), 
                        "Kaltmiete (brutto)": lambda x: fmt_eur(x),
                        "Reinertrag (NOI)": lambda x: fmt_eur(x), 
                        "Cashflow (vor St.)": lambda x: fmt_eur(x), 
                        "Cashflow (nach St.)": lambda x: fmt_eur(x)
                    }), use_container_width=True, height=table_height)
                    
                with sub_t2:
                    cols_2 = ["Jahr", "Zinsaufwand", "Tilgungsleistung", "Abschreibung (AfA)", "Einkommensteuer", "Cashflow (nach St.)"]
                    df_s2 = df_display[cols_2].set_index("Jahr").copy()
                    df_s2.index.name = None
                    
                    tot_s2 = {
                        "Zinsaufwand": df_s2["Zinsaufwand"].sum(),
                        "Tilgungsleistung": df_s2["Tilgungsleistung"].sum(),
                        "Abschreibung (AfA)": df_s2["Abschreibung (AfA)"].sum(),
                        "Einkommensteuer": df_s2["Einkommensteuer"].sum(),
                        "Cashflow (nach St.)": df_s2["Cashflow (nach St.)"].sum()
                    }
                    df_s2.loc["Summe"] = tot_s2
                    
                    st.dataframe(df_s2.style.format({
                        "Zinsaufwand": lambda x: fmt_eur(x), 
                        "Tilgungsleistung": lambda x: fmt_eur(x),
                        "Abschreibung (AfA)": lambda x: fmt_eur(x), 
                        "Einkommensteuer": lambda x: fmt_eur(x),
                        "Cashflow (nach St.)": lambda x: fmt_eur(x)
                    }), use_container_width=True, height=table_height)
                    
                with sub_t3:
                    cols_3 = ["Jahr", "Restschuld", "Objektwert", "Netto-EK (NAV)", "Beleihungsauslauf (LTV)"]
                    df_s3 = df_display[cols_3].set_index("Jahr").copy()
                    df_s3.index.name = None
                    
                    st.dataframe(df_s3.style.format({
                        "Restschuld": lambda x: fmt_eur(x), 
                        "Objektwert": lambda x: fmt_eur(x),
                        "Netto-EK (NAV)": lambda x: fmt_eur(x), 
                        "Beleihungsauslauf (LTV)": lambda x: fmt_pct(x*100, 1)
                    }), use_container_width=True, height=table_height)
                
                st.markdown("""
                <div style="background-color: #faf8f5; border: 1px solid #e0dbd0; padding: 20px; border-radius: 8px; margin-top: 25px;">
                    <div style="font-weight: 700; color: #13381A; margin-bottom: 10px; font-size: 0.95rem;">Erläuterung der Kennzahlen & Fachbegriffe</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 0.85rem; color: #555759;">
                        <div><b>Reinertrag (NOI - Net Operating Income):</b> Mietertrag nach Abzug aller Bewirtschaftungskosten und Leerstände, vor Zinsen und Steuern.</div>
                        <div><b>Cashflow (vor/nach St.):</b> Liquiditätsüberschuss auf dem Konto vor bzw. nach Berücksichtigung der persönlichen Einkommensteuer.</div>
                        <div><b>Abschreibung (AfA):</b> Steuerliche Abschreibung des Gebäude- und Sanierungswerts zur Senkung der Einkommensteuerlast.</div>
                        <div><b>Netto-EK (NAV - Net Asset Value):</b> Tatsächlicher Netto-Eigenkapitalwert des Objekts (aktueller Marktwert minus verbleibende Restschuld).</div>
                        <div><b>Beleihungsauslauf (LTV - Loan-to-Value):</b> Verhältnis der verbleibenden Restschuld zum aktuellen Marktwert des Objekts in Prozent.</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
