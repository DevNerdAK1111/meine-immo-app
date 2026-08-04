import streamlit as st

def render_wissen_view():
    st.markdown("## Immobilienwissen für Investoren")
    st.markdown("<p style='color:#555759; font-size: 1.05rem;'>Fundiertes Praxiswissen, strategische Formeln und Steuer-Hacks für den erfolgreichen Vermögensaufbau mit Wohnimmobilien.</p>", unsafe_allow_html=True)
    st.divider()

    # --- HIGHLIGHT BANNER: DER FREMDKAPITALHEBEL ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #13381A 0%, #1e5227 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px;">
        <h3 style="color: #A37841; margin-top: 0; font-size: 1.4rem;">Warum Immobilien die beste Anlageklasse für den Vermögensaufbau sind</h3>
        <p style="font-size: 1.05rem; line-height: 1.6; color: #e0e0e0;">
            Immobilien sind die einzige Anlageklasse, bei der dir die Bank 80% bis 100% des Kapitals leiht, während deine Mieter durch ihre monatlichen Mietzahlungen den Kredit für dich abbezahlen. Gleichzeitig nutzt du den <b>Fremdkapitalhebel (Leverage-Effekt)</b>, um deinen Eigenkapitaleinsatz maximal zu verzinsen.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "1. Der Fremdkapital-Hebel", 
        "2. Die 4 Säulen der Rendite", 
        "3. Steuer-Hacks & AfA", 
        "4. Investor-Checkliste"
    ])

    # --- TAB 1: DER FREMDKAPITAL-HEBEL ---
    with tab1:
        st.markdown("### Wie der Leverage-Effekt dein Eigenkapital vervielfacht")
        st.markdown("""
        Wenn du 100.000 € in Aktien investierst, profitierst du exakt von der Wertsteigerung auf diese 100.000 €. 
        Bei einer Immobilie setzt du beispielsweise **20.000 € Eigenkapital** ein und kaufst eine Immobilie für **100.000 €** (80.000 € Bankdarlehen). 
        """)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div style="background-color: #faf8f5; border: 1fr solid #e0dbd0; border-left: 4px solid #13381A; padding: 18px; border-radius: 6px;">
                <h4 style="margin-top:0; color:#13381A;">Szenario: 5% Wertsteigerung</h4>
                <ul>
                    <li><b>Aktie (100% EK):</b> 100.000 € + 5% = 5.000 € Gewinn.<br>➔ <b>EK-Rendite: 5,0%</b></li>
                    <li><b>Immobilie (20% EK):</b> 100.000 € Objekt + 5% Wertzuwachs = 5.000 € Gewinn.<br>➔ <b>EK-Rendite: 25,0% auf deine 20.000 €!</b></li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown("""
            <div style="background-color: #faf8f5; border: 1fr solid #e0dbd0; border-left: 4px solid #A37841; padding: 18px; border-radius: 6px;">
                <h4 style="margin-top:0; color:#A37841;">Der 3-fache Vermögens-Booster</h4>
                <ol>
                    <li><b>Wertsteigerung:</b> Das Objekt steigt langfristig mit der Inflation im Wert.</li>
                    <li><b>Tilgung durch Dritte:</b> Der Mieter zahlt Monat für Monat die Bankentschuldung.</li>
                    <li><b>Steuerfreier Verkauf:</b> Nach 10 Jahren Haltedauer sind Veräußerungsgewinne für Privatpersonen in Deutschland komplett steuerfrei (§ 23 EStG).</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)

    # --- TAB 2: DIE 4 SÄULEN DER RENDITE ---
    with tab2:
        st.markdown("### Die wichtigsten Kennzahlen richtig verstehen")
        
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            with st.expander("1. Bruttomietrendite (%)", expanded=True):
                st.markdown("""
                **Formel:** `(Jahreskaltmiete / Kaufpreis) * 100`
                * **Bedeutung:** Die erste schnelle Daumenregel zur Einwertung einer Immobilie.
                * **Zielwert:** Für einen positiven Cashflow (je nach Zinssatz) liegt die Zielrendite meist zwischen **4,5% und 6,5%**.
                """)

            with st.expander("2. Netto-Cashflow (€/Monat)", expanded=True):
                st.markdown("""
                **Formel:** `Kaltmiete - Nicht umlegbares Hausgeld - Kapitaldienst (Zins + Tilgung) - Steuern`
                * **Bedeutung:** Das Geld, das am Monatsende nach allen Abzügen und Steuern tatsächlich auf deinem Bankkonto verbleibt.
                * **Zielwert:** Mindestens **0 € (Selbstläufer)**, idealerweise **+50 € bis +200 € pro Einheit**.
                """)

        with col_k2:
            with st.expander("3. Eigenkapitalrendite (ROE)", expanded=True):
                st.markdown("""
                **Formel:** `(Jährlicher Netto-Cashflow / Eingesetztes EK) * 100`
                * **Bedeutung:** Zeigt die tatsächliche Verzinsung deines persönlich eingesetzten Kapitals unter Berücksichtigung des Fremdkapitalhebels.
                * **Zielwert:** Erfahrene Investoren streben eine EK-Rendite von **> 12% bis 15%** an.
                """)

            with st.expander("4. DSCR (Debt Service Coverage Ratio)", expanded=True):
                st.markdown("""
                **Formel:** `Reinertrag (NOI) / Jährlicher Kapitaldienst (Zins + Tilgung)`
                * **Bedeutung:** Die Kennzahl der Banken für dein Risiko. Zeigt, wie sicher die Mieteinnahmen den Kredit decken.
                * **Zielwert:** Ein Wert von **> 1,15** signalisiert eine solide Abdeckung des Kapitaldienstes.
                """)

    # --- TAB 3: STEUER-HACKS & AFA ---
    with tab3:
        st.markdown("### Steuerliche Vorteile optimal ausschöpfen")
        st.markdown("""
        Immobilien bieten in Deutschland einzigartige steuerliche Gestaltungsmöglichkeiten. Über die **Absetzung für Abnutzung (AfA)** kannst du Gebäudewerte von deinem zu versteuernden Einkommen abziehen.
        """)

        st.markdown("""
        | AfA-Modell | Jährlicher Satz | Beschreibung & Anwendung |
        | :--- | :--- | :--- |
        | **Linear Standard** | **2,0% - 3,0%** | Standard für Bestandsimmobilien (3% für Baujahr ab 2023, 2% für Baujahr ab 1925). |
        | **Degressiv (§ 7 Abs. 5a EStG)** | **5,0%** | Für neu errichtete Wohngebäude (Baubeginn/Kauf ab Oct 2023 bis 2029). |
        | **Sonder-AfA (§ 7b EStG)** | **5,0% extra** | Für den Neubau von Mietwohnungen mit EH40-Standard und Baukostenobergrenzen. |
        | **Denkmal-AfA (§ 7h/7i EStG)**| **Bis zu 9% - 10%** | Hohe steuerliche Abschreibung von Sanierungskosten bei denkmalgeschützten Objekten. |
        """)

        st.info("**Wichtiger Investor-Hack:** Die 15%-Grenze bei anschaffungsnahen Herstellungskosten (§ 6 Abs. 1 Nr. 1a EStG). Wenn du in den ersten 3 Jahren nach Kauf mehr als 15% des Gebäudewerts sanierst, musst du diese Kosten über 33 bis 50 Jahre abschreiben, anstatt sie sofort als Werbungskosten abzusetzen!")

    # --- TAB 4: INVESTOR-CHECKLISTE ---
    with tab4:
        st.markdown("### Die 5-Punkte-Checkliste vor dem Kauf")
        
        st.markdown("""
        - [ ] **Makro-Lage checken:** Wächst die Region? (Bevölkerungsentwicklung, Arbeitsplätze, Infrastruktur, Universitäten).
        - [ ] **Mikro-Lage prüfen:** Wie ist die direkte Nachbarschaft? (ÖPNV-Anbindung, Einkaufsmöglichkeiten, Lärmbelastung).
        - [ ] **Hausgeldabrechnung analysieren:** Wie hoch ist die Instandhaltungsrücklage? Gibt es geplante Sonderumlagen?
        - [ ] **Mietpotenzial ermitteln:** Liegt die Ist-Miete unter dem örtlichen Mietspiegel? Gibt es Potenzial für Mietanpassungen?
        - [ ] **Kaufpreis-Faktor prüfen:** Kaufpreis geteilt durch Jahreskaltmiete. Ein Faktor von **< 20** gilt in vielen Regionen als sehr attraktiv.
        """)
