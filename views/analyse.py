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
            st.selectbox("AfA-Modell", ["1_Linear_Standard", "2_Degressiv_§7_5a", "3_Sonder_AfA_§7b", "4_Denkmal_§7h_7i"], key="afa_model")
            st.number_input("Mietsteigerung p.a. (%)", key="miet_inc", step=0.1, format="%.2f")
            st.number_input("Wertsteigerung p.a. (%)", key="val_inc", step=0.1, format="%.2f")

        st.divider()
        if st.button("Analyse starten / aktualisieren", type="primary", use_container_width=True):
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

            df_proj, tot_inv, ek_abs, fk_tot, irr, afa_base, ek_quote_calc = calc_projection(input_data, full_repayment=full_rep)

            sanity_warnings = check_input_sanity(input_data)
            if sanity_warnings:
                for w in sanity_warnings:
                    st.warning(f"Plausibilitäts-Hinweis: {w}")

            obj_name = st.session_state['obj_name'] or "Unbenanntes Objekt"
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                st.markdown(f"# {obj_name}")
                st.caption(f"Kaufpreis: {fmt_eur(st.session_state['kaufpreis'])} | EK: {fmt_eur(ek_abs)} ({fmt_pct(ek_quote_calc*100)})")
            with col_t2:
                if st.button("In Cloud / lokal speichern", type="primary", use_container_width=True):
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

                    fig.update_layout(template="plotly_white", height=350, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis=dict(tickformat=",.0f", ticksuffix=" €"))
                    st.plotly_chart(fig, use_container_width=True)
                    
                with col_chart2:
                    st.markdown("### Kapitalstruktur")
                    fig_pie = px.pie(names=['Eigenkapital', 'Hausbank', 'KfW'], values=[ek_abs, hb_loan_val, kfw_amt_val], color_discrete_sequence=['#13381A', '#2B2D2F', '#A37841'], hole=0.5)
                    fig_pie.update_traces(hovertemplate="<b>%{label}</b><br>Anteil: %{value:,.0f} € (%{percent})<extra></extra>")
                    fig_pie.update_layout(height=390, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_pie, use_container_width=True)

            with tab_plan:
                st.dataframe(df_proj.style.format({
                    "Bruttomietrendite": lambda x: fmt_pct(x*100), "Brutto-Kaltmiete": lambda x: fmt_eur(x),
                    "NOI": lambda x: fmt_eur(x), "Zinsen": lambda x: fmt_eur(x), "Tilgung": lambda x: fmt_eur(x),
                    "CF v. St.": lambda x: fmt_eur(x), "AfA": lambda x: fmt_eur(x), "Steuer": lambda x: fmt_eur(x),
                    "CF n. St.": lambda x: fmt_eur(x), "Restschuld": lambda x: fmt_eur(x), "Objektwert": lambda x: fmt_eur(x),
                    "NAV": lambda x: fmt_eur(x), "LTV": lambda x: fmt_pct(x*100, 1)
                }), use_container_width=True)
