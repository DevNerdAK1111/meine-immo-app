import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai
from pypdf import PdfReader
import requests
from bs4 import BeautifulSoup
import json
import re

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
    .stMetric { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
    .css-1r6slb0 { background-color: #0f172a; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS & CALCULATIONS
# -----------------------------------------------------------------------------
GRUNDERWERBSTEUER_MAP = {
    "Baden-Württemberg": 0.050, "Bayern": 0.035, "Berlin": 0.060,
    "Brandenburg": 0.065, "Bremen": 0.050, "Hamburg": 0.055,
    "Hessen": 0.060, "Mecklenburg-Vorpommern": 0.060, "Niedersachsen": 0.050,
    "Nordrhein-Westfalen": 0.065, "Rheinland-Pfalz": 0.050, "Saarland": 0.065,
    "Sachsen": 0.055, "Sachsen-Anhalt": 0.050, "Schleswig-Holstein": 0.065, "Thüringen": 0.065
}

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
        
        # Kaskade gängiger Modellnamen zur maximalen Kompatibilität
        candidate_models = [
            'gemini-1.5-flash-latest',
            'gemini-1.5-flash',
            'gemini-1.5-pro-latest',
            'gemini-2.0-flash-exp',
            'gemini-pro'
        ]
        
        response = None
        last_err = None
        
        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    break
            except Exception as e:
                last_err = e
                continue
                
        if not response or not response.text:
            st.error(f"Kein passendes Gemini-Modell erreichbar: {last_err}")
            return None

        cleaned_json = response.text.replace('```json', '').replace('```', '').strip()
        # Sanitize JSON if leading text exists
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
    annu_tot = hb_rate + kfw_rate
    
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
    
    cf_stream = [-ek_abs] + list(df['CF n. St.'][:-1]) + [df['CF n. St.'].iloc[-1] + (df['Objektwert'].iloc[-1] * (1 - data['exit_cost']) - df['Restschuld'].iloc[-1])]
    try:
        irr = npf.irr(cf_stream)
    except:
        irr = 0.0
        
    return df, tot_inv, ek_abs, fk_tot, irr, afa_base

# -----------------------------------------------------------------------------
# SIDEBAR / INPUTS & SESSION-STATE API-KEY
# -----------------------------------------------------------------------------
# Speichert den API Key dauerhaft in der Session
if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = ""

with st.sidebar:
    st.title("🏢 ImmoAnalyse Pro")
    st.caption("Institutional Investment & AI Suite")
    
    st.subheader("🤖 KI-Import & Data Extractor")
    
    api_key_input = st.text_input(
        "Gemini API Key",
        value=st.session_state["gemini_api_key"],
        type="password",
        help="Wird für die gesamte Sitzung im Browser gespeichert!"
    )
    if api_key_input:
        st.session_state["gemini_api_key"] = api_key_input
        
    uploaded_pdf = st.file_uploader("Exposé PDF hochladen", type=["pdf"])
    
    ai_data = None
    if uploaded_pdf and st.session_state["gemini_api_key"]:
        if st.button("✨ Exposé per KI analysieren"):
            with st.spinner("Lese PDF & strukturiere Daten..."):
                ai_data = analyze_pdf_with_gemini(st.session_state["gemini_api_key"], uploaded_pdf)
                if ai_data:
                    st.success("Daten erfolgreich extrahiert!")

    st.divider()
    st.subheader("1. Stammdaten")
    obj_name = st.text_input("Objektname", ai_data.get("objektname", "MFH Musterstraße 12") if ai_data else "MFH Musterstraße 12")
    bundesland = st.selectbox("Bundesland", list(GRUNDERWERBSTEUER_MAP.keys()), index=8)
    kaufpreis = st.number_input("Kaufpreis (€)", value=float(ai_data.get("kaufpreis", 350000)) if ai_data else 350000.0, step=10000.0)
    qm = st.number_input("Wohnfläche (m²)", value=float(ai_data.get("wohnflaeche", 120)) if ai_data else 120.0, step=5.0)
    baujahr = st.number_input("Baujahr", value=int(ai_data.get("baujahr", 1998)) if ai_data else 1998, step=1)
    sanierung = st.number_input("Sanierungskosten J1-3 (€)", value=35000.0, step=5000.0)
    grund_anteil = st.slider("Grundstücksanteil (%)", 0.0, 0.50, 0.20, 0.05)

    st.subheader("2. Kaufnebenkosten")
    notar_p = st.number_input("Notar & Grundbuch (%)", value=1.5) / 100
    makler_p = st.number_input("Makler (%)", value=3.57) / 100
    sonst_nk = st.number_input("Sonstige Nebenkosten (€)", value=1000.0)
    disagio_p = st.number_input("Disagio / Damnum (%)", value=0.0) / 100

    st.subheader("3. Finanzierung")
    ek_quote = st.slider("Eigenkapitalquote (%)", 0.0, 0.50, 0.20, 0.05)
    hb_share = st.slider("Anteil Hausbank (%)", 0.50, 1.0, 0.80, 0.05)
    hb_zins = st.number_input("Hausbank Zins (%)", value=3.8) / 100
    hb_tilg = st.number_input("Hausbank Tilgung (%)", value=2.0) / 100
    grace_years = st.number_input("Tilgungsfreie Jahre", value=0, min_value=0, max_value=5)
    
    kfw_amt = st.number_input("KfW Darlehen (€)", value=50000.0, step=10000.0)
    kfw_zins = st.number_input("KfW Zins (%)", value=2.1) / 100
    kfw_tilg = st.number_input("KfW Tilgung (%)", value=3.0) / 100
    kfw_grant = st.number_input("KfW Tilgungszuschuss (€)", value=5000.0)
    sondertilg = st.number_input("Sondertilgung (€/Jahr)", value=2000.0, step=500.0)

    st.subheader("4. Mieten & Betriebskosten")
    ist_sqm = st.number_input("Ist-Kaltmiete (€/m²)", value=float(ai_data.get("ist_miete_sqm", 9.50)) if ai_data else 9.50)
    target_sqm = st.number_input("Ziel-Kaltmiete (€/m²)", value=12.00)
    adj_year = st.number_input("Jahr der Ziel-Miete", value=3, min_value=1, max_value=10)
    park = st.number_input("Sonstige Miete/Monat (€)", value=50.0)
    vac_rate = st.slider("Leerstandsquote (%)", 0.0, 0.10, 0.02)
    
    hausgeld = st.number_input("Nicht umlegb. Hausgeld (€/Monat)", value=float(ai_data.get("hausgeld_monat", 45.0)) if ai_data else 45.0)
    inst_sqm = st.number_input("Instandhaltung (€/m²/Jahr)", value=10.0)
    mgt_monat = st.number_input("Verwaltung (€/Monat)", value=25.0)
    capex_j3 = st.number_input("CapEx Instandhaltung Jahr 3 (€)", value=5000.0)
    capex_j6 = st.number_input("CapEx Instandhaltung Jahr 6 (€)", value=0.0)

    st.subheader("5. Steuer & Makro")
    tax_rate = st.slider("Persönlicher Grenzsteuersatz (%)", 0.0, 0.50, 0.42, 0.01)
    afa_model = st.selectbox("AfA-Modell", ["1_Linear_Standard", "2_Degressiv_§7_5a", "3_Sonder_AfA_§7b", "4_Denkmal_§7h_7i"])
    afa_lin = st.number_input("Linearer AfA-Satz (%)", value=2.0) / 100
    miet_inc = st.number_input("Mietsteigerung p.a. (%)", value=1.5) / 100
    cost_inc = st.number_input("Cost Inflation p.a. (%)", value=2.0) / 100
    val_inc = st.number_input("Wertsteigerung p.a. (%)", value=1.5) / 100
    wacc = st.number_input("WACC / Diskontierung (%)", value=6.0) / 100
    exit_cost = st.number_input("Verkaufsnebenkosten (%)", value=2.0) / 100

input_data = {
    'kaufpreis': kaufpreis, 'sanierung': sanierung, 'bundesland': bundesland,
    'notar_proz': notar_p, 'makler_proz': makler_p, 'sonst_nk': sonst_nk,
    'disagio_proz': disagio_p, 'ek_quote': ek_quote, 'hb_share': hb_share,
    'hb_zins': hb_zins, 'hb_tilg': hb_tilg, 'grace_years': grace_years,
    'kfw_amt': kfw_amt, 'kfw_zins': kfw_zins, 'kfw_tilg': kfw_tilg,
    'kfw_grant': kfw_grant, 'sondertilg': sondertilg, 'ist_sqm': ist_sqm,
    'target_sqm': target_sqm, 'adj_year': adj_year, 'park': park,
    'vac_rate': vac_rate, 'qm': qm, 'hausgeld': hausgeld, 'inst_sqm': inst_sqm,
    'mgt_monat': mgt_monat, 'capex_j3': capex_j3, 'capex_j6': capex_j6,
    'tax_rate': tax_rate, 'afa_model': afa_model, 'afa_lin': afa_lin,
    'miet_inc': miet_inc, 'cost_inc': cost_inc, 'val_inc': val_inc,
    'wacc': wacc, 'exit_cost': exit_cost, 'grund_anteil': grund_anteil
}

df_proj, tot_inv, ek_abs, fk_tot, irr, afa_base = calc_10y_projection(input_data)

# -----------------------------------------------------------------------------
# MAIN CONTENT DASHBOARD
# -----------------------------------------------------------------------------
st.title(f"🏢 {obj_name}")
st.caption(f"Standort: {bundesland} | Wohnfläche: {qm:.0f} m² | Baujahr: {baujahr}")

col1, col2, col3, col4, col5 = st.columns(5)
cf_m1 = df_proj.loc[0, 'CF n. St.'] / 12
dscr_1 = df_proj.loc[0, 'NOI'] / ((fk_tot * hb_share * (hb_zins + hb_tilg)) + (max(0, kfw_amt - kfw_grant) * (kfw_zins + kfw_tilg)))

col1.metric("Monatlicher Cashflow (n. St.)", f"{cf_m1:,.2f} €", delta="Positiv" if cf_m1 >= 0 else "Negativ", delta_color="normal")
col2.metric("Bruttomietrendite", f"{df_proj.loc[0, 'Bruttomietrendite']*100:.2f} %")
col3.metric("Eigenkapitalrendite (ROE)", f"{(df_proj.loc[0, 'CF n. St.']/ek_abs)*100:.2f} %")
col4.metric("DSCR Schuldendienst", f"{dscr_1:.2f}", delta="Sicher (>1.2)" if dscr_1 >= 1.2 else "Kritisch (<1.1)", delta_color="normal")
col5.metric("10-Jahres IRR", f"{irr*100:.2f} %")

limit_15 = afa_base * 0.15
if sanierung > limit_15:
    st.warning(f"⚠️ **§6 EStG 15%-Hürde überschritten:** Ihre Sanierungskosten ({sanierung:,.0f} €) liegen über der 15%-Grenze ({limit_15:,.0f} €). Diese müssen über 50 Jahre aktiviert werden.")

tab_dash, tab_plan, tab_tax, tab_stress = st.tabs([
    "📊 Executive Dashboard", "📅 10-Jahres Finanzplan", "⚖️ Steuer & VV-GmbH", "💣 Stresstest & Refinanzierung"
])

with tab_dash:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Vermögensaufbau vs. Restschuld")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Objektwert'], name="Objektwert (€)", line=dict(color="#10b981", width=3)))
        fig.add_trace(go.Scatter(x=df_proj['Jahr'], y=df_proj['Restschuld'], name="Restschuld (€)", line=dict(color="#ef4444", width=3)))
        fig.add_trace(go.Bar(x=df_proj['Jahr'], y=df_proj['NAV'], name="Netto-Eigenkapital / NAV (€)", marker_color="#3b82f6", opacity=0.4))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.subheader("Gesamtinvestition & Kapital")
        fig_pie = px.pie(
            names=['Eigenkapital', 'Hausbank Darlehen', 'KfW Darlehen'],
            values=[ek_abs, fk_tot * hb_share, max(0, kfw_amt - kfw_grant)],
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
    tax_privat = tot_taxable * tax_rate
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
        new_rate = (restschuld_10 * (r + hb_tilg)) / 12
        new_dscr = df_proj.loc[9, 'NOI'] / (new_rate * 12)
        refin_data.append({
            "Anschluss-Zinssatz": f"{r*100:.1f} %",
            "Neue Monatliche Rate": f"{new_rate:,.2f} €",
            "Neuer DSCR": f"{new_dscr:.2f}",
            "Status": "✅ Tragfähig" if new_dscr >= 1.15 else "⚠️ Risiko"
        })
    st.table(pd.DataFrame(refin_data))
