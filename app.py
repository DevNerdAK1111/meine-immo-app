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

st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stMetric { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
    .css-1r6slb0 { background-color: #0f172a; }
</style>
""", unsafe_allow_keywords=True)

# -----------------------------------------------------------------------------
# HELPER DATA & TAX TABLES
# -----------------------------------------------------------------------------
BUNDESLAND_TAX = {
    "Baden-Württemberg": 0.050, "Bayern": 0.035, "Berlin": 0.060, "Brandenburg": 0.065,
    "Bremen": 0.050, "Hamburg": 0.055, "Hessen": 0.060, "Mecklenburg-Vorpommern": 0.060,
    "Niedersachsen": 0.050, "Nordrhein-Westfalen": 0.065, "Rheinland-Pfalz": 0.050,
    "Saarland": 0.065, "Sachsen": 0.055, "Sachsen-Anhalt": 0.050,
    "Schleswig-Holstein": 0.065, "Thüringen": 0.065
}

# -----------------------------------------------------------------------------
# AI EXTRACTION ENGINE (GEMINI FREE TIER)
# -----------------------------------------------------------------------------
def extract_data_with_gemini(api_key: str, raw_text: str) -> dict:
    """Extrahiert Immobiliendaten aus Fliesstext/PDF via Google Gemini AI."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Du bist ein Experte für Immobilien-Exposés. Analysiere den folgenden Text und extrahiere alle relevanten Daten.
    Antworte AUSSCHLIESSLICH mit einem validen JSON-Objekt ohne Markdown-Codeblöcke (kein ```json).
    
    Erforderliche JSON-Struktur:
    {{
        "titel": "String (Objektname)",
        "kaufpreis": float oder null (in Euro),
        "wohnflaeche": float oder null (in qm),
        "baujahr": int oder null,
        "bundesland": "String (z.B. Niedersachsen, Bayern etc. oder null)",
        "kaltmiete_monat": float oder null (Kaltmiete pro Monat in Euro),
        "hausgeld_monat": float oder null (Nicht umlegbares Hausgeld pro Monat in Euro),
        "sanierungskosten": float oder null (geschätzte/erwähnte Kosten in Euro),
        "zustand_notizen": "String (Kurze Zusammenfassung des Zustands)"
    }}
    
    Text zum Analysieren:
    {raw_text[:8000]}
    """
    
    response = model.generate_content(prompt)
    clean_json = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(clean_json)

def scrape_url_text(url: str) -> str:
    """Holt Fliesstext aus einer Inserat-URL."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(resp.text, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    return soup.get_text(separator=' ', strip=True)

# -----------------------------------------------------------------------------
# SIDEBAR: KI-IMPORT & BENUTZEREINGABEN
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 ImmoAnalyse Pro")

# --- KI Import Section ---
with st.sidebar.expander("🤖 KI-Import (PDF / Link)", expanded=True):
    gemini_key = st.text_input("Google Gemini API-Key (Kostenlos)", type="password", help="Kostenlosen Key auf aistudio.google.com holen")
    
    import_option = st.radio("Quelle wählen", ["PDF-Exposé", "Web-Link (URL)"])
    
    extracted_data = {}
    if import_option == "PDF-Exposé":
        uploaded_file = st.file_uploader("Exposé (PDF) hochladen", type=["pdf"])
        if uploaded_file and gemini_key:
            if st.button("✨ PDF mit KI analysieren"):
                with st.spinner("Lese PDF und analysiere Kennzahlen..."):
                    reader = PdfReader(uploaded_file)
                    pdf_text = "".join([page.extract_text() or "" for page in reader.pages])
                    try:
                        extracted_data = extract_data_with_gemini(gemini_key, pdf_text)
                        st.success("Daten erfolgreich extrahiert!")
                    except Exception as e:
                        st.error(f"Fehler bei KI-Analyse: {e}")
    else:
        url_input = st.text_input("Immobilien-Link einfügen")
        if url_input and gemini_key:
            if st.button("✨ Link mit KI analysieren"):
                with st.spinner("Crawle Webseite und analysiere Inserat..."):
                    try:
                        scraped_text = scrape_url_text(url_input)
                        extracted_data = extract_data_with_gemini(gemini_key, scraped_text)
                        st.success("Daten erfolgreich extrahiert!")
                    except Exception as e:
                        st.error(f"Fehler beim Crawlen: {e}")

st.sidebar.markdown("---")

# --- Default Fallback & KI Override Values ---
def_titel = extracted_data.get("titel") or "MFH Musterstraße 12, Hannover"
def_kp = float(extracted_data.get("kaufpreis") or 350000)
def_wf = float(extracted_data.get("wohnflaeche") or 120)
def_bj = int(extracted_data.get("baujahr") or 1998)
def_bl = extracted_data.get("bundesland") if extracted_data.get("bundesland") in BUNDESLAND_TAX else "Niedersachsen"
def_km = float(extracted_data.get("kaltmiete_monat") or (9.50 * def_wf))
def_san = float(extracted_data.get("sanierungskosten") or 35000)
def_hg = float(extracted_data.get("hausgeld_monat") or 45)

# --- Dynamic Input Fields ---
st.sidebar.subheader("1. Objekt- & Kaufdaten")
obj_titel = st.sidebar.text_input("Objektname", value=def_titel)
bundesland = st.sidebar.selectbox("Bundesland", list(BUNDESLAND_TAX.keys()), index=list(BUNDESLAND_TAX.keys()).index(def_bl))
kaufpreis = st.sidebar.number_input("Kaufpreis (€)", value=def_kp, step=5000.0)
wohnflaeche = st.sidebar.number_input("Wohnfläche (qm)", value=def_wf, step=5.0)
baujahr = st.sidebar.number_input("Baujahr", value=def_bj, step=1)
sanierung = st.sidebar.number_input("Sanierungskosten (Jahr 1-3) (€)", value=def_san, step=1000.0)
grundstück_anteil = st.sidebar.slider("Grundstücksanteil (%)", 0.0, 50.0, 20.0) / 100

st.sidebar.subheader("2. Kaufnebenkosten & Finanzierung")
notar_pct = st.sidebar.number_input("Notar & Grundbuch (%)", value=1.5) / 100
makler_pct = st.sidebar.number_input("Maklerprovision (%)", value=3.57) / 100
sonst_nk = st.sidebar.number_input("Sonstige Neben-Kosten (€)", value=1000.0)
disagio_pct = st.sidebar.number_input("Disagio / Damnum (%)", value=0.0) / 100

ek_quote = st.sidebar.slider("Eigenkapital-Quote (%)", 0.0, 50.0, 20.0) / 100
hb_share = st.sidebar.slider("Anteil Hausbank (%)", 50.0, 100.0, 80.0) / 100
hb_zins = st.sidebar.number_input("Hausbank Zins p.a. (%)", value=3.8) / 100
hb_tilgung = st.sidebar.number_input("Hausbank Tilgung p.a. (%)", value=2.0) / 100

st.sidebar.subheader("3. Miete & Operative Kosten")
ist_kaltmiete_m = st.sidebar.number_input("Aktuelle Kaltmiete monatlich (€)", value=def_km)
target_sqm_m = st.sidebar.number_input("Ziel-Kaltmiete (€/qm/Monat)", value=12.0)
adj_year = st.sidebar.number_input("Jahr der Zielmiet-Anpassung", value=3)
stellplatz_m = st.sidebar.number_input("Stellplatz / Sonstiges monatlich (€)", value=50.0)
mietausfall_pct = st.sidebar.slider("Leerstandsrisiko (%)", 0.0, 10.0, 2.0) / 100

hausgeld_m = st.sidebar.number_input("Nicht umlegbares Hausgeld (€/Monat)", value=def_hg)
instand_sqm_y = st.sidebar.number_input("Instandhaltung (€/qm/Jahr)", value=10.0)
mgt_m = st.sidebar.number_input("Sonderkosten / Verwaltung (€/Monat)", value=25.0)

st.sidebar.subheader("4. Steuern & Makro")
steuersatz_privat = st.sidebar.slider("Persönlicher Grenzsteuersatz (%)", 0.0, 50.0, 42.0) / 100
afa_modell = st.sidebar.selectbox("AfA-Modell", ["1_Linear_Standard (2%)", "2_Degressiv_§7_5a (5%)", "3_Sonder_AfA_§7b", "4_Denkmal_§7h_7i (9%)"])
miet_steigerung_pa = st.sidebar.number_input("Mietsteigerung p.a. ab Zieljahr (%)", value=1.5) / 100
wert_steigerung_pa = st.sidebar.number_input("Wertsteigerung p.a. (%)", value=1.5) / 100
wacc_discount = st.sidebar.number_input("WACC Diskontierung für NPV (%)", value=6.0) / 100

# -----------------------------------------------------------------------------
# CORE FINANCIAL ENGINE (NO CIRCULAR REFERENCES)
# -----------------------------------------------------------------------------
grunderwerb_pct = BUNDESLAND_TAX[bundesland]
summe_nk = kaufpreis * (grunderwerb_pct + notar_pct + makler_pct) + sonst_nk

# Linear formula without circular dependency:
disagio_betrag = (kaufpreis + sanierung + summe_nk) * (1 - ek_quote) * hb_share * disagio_pct
gesamtinvestition = kaufpreis + sanierung + summe_nk + disagio_betrag

eigenkapital = gesamtinvestition * ek_quote
fremdkapital = gesamtinvestition - eigenkapital
hb_darlehen = fremdkapital * hb_share

hb_monatsrate = hb_darlehen * (hb_zins + hb_tilgung) / 12
annuitaet_pa = hb_monatsrate * 12

kaltmiete_j1 = (ist_kaltmiete_m + stellplatz_m) * 12
nettokaltmiete_j1 = kaltmiete_j1 * (1 - mietausfall_pct)
op_kosten_j1 = (hausgeld_m * 12) + (instand_sqm_y * wohnflaeche) + (mgt_m * 12)
noi_j1 = nettokaltmiete_j1 - op_kosten_j1

gebaeudeanteil = 1.0 - grundstück_anteil
afa_basis = (kaufpreis + summe_nk) * gebaeudeanteil

# 10-Year Projection Matrix Construction
projection = []
restschuld = hb_darlehen
objektwert = gesamtinvestition

for yr in range(1, 11):
    # Rent progression
    if yr >= adj_year:
        if yr == adj_year:
            b_miete = (target_sqm_m * wohnflaeche + stellplatz_m) * 12
        else:
            b_miete = projection[-1]["Brutto-Kaltmiete"] * (1 + miet_steigerung_pa)
    else:
        b_miete = kaltmiete_j1 if yr == 1 else projection[-1]["Brutto-Kaltmiete"]
        
    leerstand = b_miete * mietausfall_pct
    n_miete = b_miete - leerstand
    op_kosten = op_kosten_j1 if yr == 1 else projection[-1]["Op. Kosten"] * 1.02
    
    noi = n_miete - op_kosten
    zinsen = restschuld * hb_zins
    tilgung = annuitaet_pa - zinsen
    cf_v_st = noi - annuitaet_pa
    
    # AfA logic
    if "2_Degressiv" in afa_modell:
        prev_afa_sum = sum(p["AfA"] for p in projection) if yr > 1 else 0
        afa = (afa_basis - prev_afa_sum) * 0.05
    elif "3_Sonder" in afa_modell:
        afa = (afa_basis * 0.02) + (afa_basis * 0.05 if yr <= 4 else 0)
    elif "4_Denkmal" in afa_modell:
        afa = afa_basis * (0.09 if yr <= 8 else 0.07)
    else:
        afa = afa_basis * 0.02

    disagio_tax = disagio_betrag if yr == 1 else 0
    zv_ertrag = noi - zinsen - afa - disagio_tax - (sanierung if (yr == 1 and sanierung <= afa_basis * 0.15) else 0)
    steuer = max(0, zv_ertrag * steuersatz_privat)
    cf_n_st = cf_v_st - steuer
    
    restschuld = max(0, restschuld - tilgung)
    objektwert = objektwert * (1 + wert_steigerung_pa)
    ltv = restschuld / objektwert if objektwert > 0 else 0
    nav = objektwert - restschuld
    
    irr_stream = cf_n_st if yr < 10 else cf_n_st + (objektwert * 0.98 - restschuld)
    
    projection.append({
        "Jahr": yr, "Brutto-Kaltmiete": b_miete, "Netto-Kaltmiete": n_miete,
        "Op. Kosten": op_kosten, "NOI": noi, "Zinsen": zinsen, "Tilgung": tilgung,
        "CF v. St.": cf_v_st, "AfA": afa, "Steuer": steuer, "CF n. St.": cf_n_st,
        "Restschuld": restschuld, "Objektwert": objektwert, "LTV": ltv, "NAV": nav,
        "IRR Stream": irr_stream
    })

df_proj = pd.DataFrame(projection)

# Key Financial Metrics
bruttomietrendite = kaltmiete_j1 / kaufpreis
nettomietrendite = noi_j1 / gesamtinvestition
faktor = kaufpreis / kaltmiete_j1
roe_j1 = (df_proj.loc[0, "CF n. St."]) / eigenkapital
dscr_j1 = noi_j1 / annuitaet_pa

irr_cashflows = [-eigenkapital] + df_proj["IRR Stream"].tolist()
irr_10y = npf.irr(irr_cashflows)

npv = npf.npv(wacc_discount, [-eigenkapital] + df_proj["CF n. St."].tolist())

# Scoring System (0-100)
score_bmr = 25 if bruttomietrendite >= 0.06 else (20 if bruttomietrendite >= 0.05 else 10)
score_cf = 25 if (df_proj.loc[0, "CF n. St."] / 12) >= 100 else (20 if (df_proj.loc[0, "CF n. St."] / 12) >= 0 else 5)
score_roe = 25 if roe_j1 >= 0.10 else (20 if roe_j1 >= 0.06 else 10)
score_dscr = 25 if dscr_j1 >= 1.25 else (20 if dscr_j1 >= 1.10 else 5)
total_score = score_bmr + score_cf + score_roe + score_dscr

# -----------------------------------------------------------------------------
# MAIN DASHBOARD INTERFACE
# -----------------------------------------------------------------------------
st.title(f"🏢 {obj_titel}")
st.caption(f"Standort: {bundesland} | {wohnflaeche:.1f} qm | Baujahr {baujahr}")

# Top Metric Cards
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Monatlicher Cashflow (n. St.)", f"{df_proj.loc[0, 'CF n. St.']/12:,.2f} €", delta_color="normal")
col2.metric("10-Jahres IRR (Rendite)", f"{irr_10y*100:.1f} %")
col3.metric("DSCR Schuldendienst", f"{dscr_j1:.2f}", delta="Tragfähig" if dscr_j1 >= 1.1 else "Kritisch", delta_color="normal" if dscr_j1 >= 1.1 else "inverse")
col4.metric("Net Present Value (NPV)", f"{npv:,.0f} €")
col5.metric("Investment Score", f"{total_score} / 100 Pkt", delta="Kauf-Empfehlung" if total_score >= 70 else "Prüfen")

st.markdown("---")

# Main Navigation Tabs
tab_dash, tab_plan, tab_tax, tab_stress, tab_bank = st.tabs([
    "📊 Executive Dashboard", "📅 10-Jahres-Finanzplan", "⚖️ Privat vs. VV-GmbH", "⚡ Stresstest & Refinanzierung", "🏦 Bank-Exposé Pitch"
])

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE DASHBOARD
# -----------------------------------------------------------------------------
with tab_dash:
    c_left, c_right = st.columns([1, 1])
    
    with c_left:
        st.subheader("Key Financial Ratios")
        df_kpis = pd.DataFrame([
            {"Metrik": "Gesamtinvestition", "Wert": f"{gesamtinvestition:,.0f} €"},
            {"Metrik": "Eigenkapital (EK)", "Wert": f"{eigenkapital:,.0f} € ({ek_quote*100:.1f}%)"},
            {"Metrik": "Bruttomietrendite", "Wert": f"{bruttomietrendite*100:.2f} %"},
            {"Metrik": "Nettomietrendite (NOI)", "Wert": f"{nettomietrendite*100:.2f} %"},
            {"Metrik": "Kaufpreis-Faktor", "Wert": f"{faktor:.1f} Jahre"},
            {"Metrik": "EK-Rendite n. St. (ROE J1)", "Wert": f"{roe_j1*100:.2f} %"},
        ])
        st.table(df_kpis.set_index("Metrik"))
        
    with c_right:
        st.subheader("10-Jahres Vermögensaufbau vs. Restschuld")
        fig_chart = go.Figure()
        fig_chart.add_trace(go.Scatter(x=df_proj["Jahr"], y=df_proj["Objektwert"], mode='lines+markers', name='Objektwert (€)', line=dict(color='#0f172a', width=3)))
        fig_chart.add_trace(go.Scatter(x=df_proj["Jahr"], y=df_proj["NAV"], mode='lines+markers', name='Eigenkapital / NAV (€)', line=dict(color='#166534', width=3)))
        fig_chart.add_trace(go.Scatter(x=df_proj["Jahr"], y=df_proj["Restschuld"], mode='lines+markers', name='Restschuld (€)', line=dict(color='#991b1b', width=2, dash='dash')))
        fig_chart.update_layout(margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_chart, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: 10-JAHRES-FINANZPLAN
# -----------------------------------------------------------------------------
with tab_plan:
    st.subheader("Detaillierter 10-Jahres Liquiditäts- & Steuerplan")
    
    formatted_df = df_proj.copy()
    for col in ["Brutto-Kaltmiete", "Netto-Kaltmiete", "Op. Kosten", "NOI", "Zinsen", "Tilgung", "CF v. St.", "AfA", "Steuer", "CF n. St.", "Restschuld", "Objektwert", "NAV"]:
        formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f} €")
    formatted_df["LTV"] = formatted_df["LTV"].apply(lambda x: f"{x*100:.1f} %")
    
    st.dataframe(formatted_df.set_index("Jahr"), use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: STEUER- & RECHTSFORMVERGLEICH
# -----------------------------------------------------------------------------
with tab_tax:
    st.subheader("Vergleich: Direktbesitz (Privat) vs. vermögensverwaltende GmbH (VV-GmbH)")
    
    total_noi_10y = df_proj["NOI"].sum()
    total_tax_privat = df_proj["Steuer"].sum()
    total_tax_gmbh = (total_noi_10y - df_proj["Zinsen"].sum() - df_proj["AfA"].sum()) * 0.15825
    vorteil_gmbh_haltephase = total_tax_privat - total_tax_gmbh
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.info("### 👤 Privatbesitz (§ 21 EStG)")
        st.write(f"- **Steuersatz Haltephase:** {steuersatz_privat*100:.1f} %")
        st.write(f"- **Kumulierte Steuer (10 J.):** {total_tax_privat:,.0f} €")
        st.write("- **Exit nach 10 Jahren:** **100 % STEUERFREI** (§ 23 EStG)")
        
    with col_t2:
        st.success("### 🏢 VV-GmbH (15,825 % KSt/SolZ)")
        st.write("- **Steuersatz Haltephase:** 15,825 % (bei GewSt-Befreiung)")
        st.write(f"- **Kumulierte Steuer (10 J.):** {max(0, total_tax_gmbh):,.0f} €")
        st.write("- **Exit nach 10 Jahren:** **15,825 % KSt auf Veräußerungsgewinn**")
        
    st.metric("Netto-Steuervorteil VV-GmbH in Haltephase (10 Jahre)", f"{vorteil_gmbh_haltephase:,.0f} €")

# -----------------------------------------------------------------------------
# TAB 4: STRESSTEST & REFINANZIERUNG
# -----------------------------------------------------------------------------
with tab_stress:
    st.subheader("⚡ Refinanzierungs-Shock Test (Zinsbindungsende Jahr 11)")
    restschuld_j10 = df_proj.loc[9, "Restschuld"]
    
    st.write(f"Verbleibende Restschuld nach 10 Jahren: **{restschuld_j10:,.0f} €**")
    
    refin_rates = [0.035, 0.045, 0.055, 0.065, 0.075]
    refin_data = []
    
    for r in refin_rates:
        new_rate_m = (restschuld_j10 * (r + hb_tilgung)) / 12
        new_dscr = df_proj.loc[9, "NOI"] / (new_rate_m * 12)
        new_cf_m = (df_proj.loc[9, "NOI"] - (new_rate_m * 12) - df_proj.loc[9, "Steuer"]) / 12
        refin_data.append({
            "Anschluss-Zinssatz": f"{r*100:.1f} %",
            "Neue Rate (mtl.)": f"{new_rate_m:,.2f} €",
            "Neuer DSCR": f"{new_dscr:.2f}",
            "Neuer Cashflow n. St. (mtl.)": f"{new_cf_m:,.2f} €"
        })
        
    st.table(pd.DataFrame(refin_data).set_index("Anschluss-Zinssatz"))

# -----------------------------------------------------------------------------
# TAB 5: BANK-EXPOSÉ PITCH
# -----------------------------------------------------------------------------
with tab_bank:
    st.subheader("🏦 Bank-Pitch & Finanzierungsanfrage")
    st.write("Verwenden Sie diesen zusammenfassenden Bericht für das Gespräch mit Ihrer Bank.")
    
    st.markdown(f"""
    **Objekt:** {obj_titel}  
    **Gesamtinvestition:** {gesamtinvestition:,.2f} €  
    **Eigenkapital-Einsatz:** {eigenkapital:,.2f} € ({ek_quote*100:.1f} %)  
    **Gewünschtes Fremdkapital:** {fremdkapital:,.2f} €  
    
    ---
    ### Kapitaldienstfähigkeit (DSCR)
    - **Reinertrag (NOI Jahr 1):** {noi_j1:,.2f} €  
    - **Jahres-Annuität:** {annuitaet_pa:,.2f} €  
    - **DSCR Deckungsfaktor:** **{dscr_j1:.2f}**  
    - **Anfangsausreichung (LTV):** {fremdkapital/gesamtinvestition*100:.1f} %  
    """)
    
    if st.button("📄 Bank-Pitch als PDF generieren"):
        st.info("PDF-Generierungsmodul wird vorbereitet...")