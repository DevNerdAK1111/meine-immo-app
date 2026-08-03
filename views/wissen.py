import streamlit as st

def render_wissen_view():
    st.markdown("## Immobilienwissen & Investment-Guide")
    st.markdown("<p style='color:#555759;'>Fundiertes Know-how, Kennzahlen-Erklärungen und Schutz vor typischen Investor-Fehlern.</p>", unsafe_allow_html=True)

    w_tab1, w_tab2, w_tab3 = st.tabs(["Indikatoren & KPIs", "Die 5 häufigsten Fehler", "Investment-Grundsätze"])

    with w_tab1:
        st.markdown("### Die wichtigsten Kennzahlen im Überblick")
        
        with st.expander("📌 Cashflow (netto nach Steuern)", expanded=True):
            st.markdown("""
            **Was ist das?**  
            Der Netto-Cashflow ist das Geld, das am Monatsende nach Abzug *aller* Kosten (Verwaltung, Instandhaltung, Hausgeld, Zinsen, Tilgung und Einkommensteuer) auf deinem Konto übrig bleibt.

            **Warum ist das wichtig?**  
            Ein positiver Cashflow baut passives Vermögen auf, ohne dass du monatlich aus eigener Tasche dazuzahlen musst (*„Zuzahlungsimmobilie“*). 

            * **Formel:** `Netto-Kaltmiete - Betriebskosten (nicht umlegbar) - Zins & Tilgung - Steuern`
            * **Zielwert:** Mindestens **50 € bis 150 € / Monat** Überschuss je Wohneinheit.
            """)

        with st.expander("📌 Bruttomietrendite vs. Nettomietrendite"):
            st.markdown("""
            **Was ist das?**  
            Die Rendite setzt den jährlichen Ertrag ins Verhältnis zum Kaufpreis bzw. zu den Gesamtkosten.

            * **Bruttomietrendite:** Schnellcheck für Exposés.  
              *(Jahreskaltmiete / Kaufpreis) × 100*
            * **Nettomietrendite:** Viel genauer, da Kaufnebenkosten und Bewirtschaftung eingerechnet werden.  
              *(Netto-Betriebseinkommen [NOI] / Gesamtinvestition) × 100*
            """)

        with st.expander("📌 DSCR (Debt Service Coverage Ratio)"):
            st.markdown("""
            **Was ist das?**  
            Der DSCR zeigt, wie gut der Reinertrag des Objekts (NOI) den monatlichen Bankkredit (Zins + Tilgung) deckt.

            **Richtwerte:**
            * **Unter 1,0:** Der Ertrag reicht nicht aus, um den Kredit zu zahlen.
            * **Ab 1,20 (Empfehlung):** Die Bank bewertet den Kredit als sicher (20 % Puffer).
            """)

    with w_tab2:
        st.markdown("### Die 5 teuersten Anfängerfehler")
        
        st.error("""
        **Fehler 1: Hausgeld nicht in umlegbar & nicht umlegbar trennen**  
        Nur der **nicht umlegbare Teil** (WEG-Verwalter + Instandhaltungsrücklage) ist eine echte Ausgabe für dich als Eigentümer!
        """)

        st.warning("""
        **Fehler 2: Die 15 %-Hürde bei der Sanierung (§ 6 Abs. 1 Nr. 1a EStG) ignorieren**  
        Wer in den ersten 3 Jahren nach Kauf mehr als 15 % des Gebäude-Kaufpreises netto saniert, muss diese Kosten über 33–50 Jahre langwierig abschreiben.
        """)

    with w_tab3:
        st.markdown("### Fundamentale Investment-Regeln")
        
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            st.markdown("""
            #### 1. Der Eigenkapital-Hebel (Leverage-Effekt)
            Immobilien sind die einzige Anlageklasse, bei der dir Banken 80–90 % des Kapitals zu sehr niedrigen Zinsen leihen.
            """)
        with col_w2:
            st.markdown("""
            #### 2. Die 10-Jahres-Spekulationsfrist (§ 23 EStG)
            Immobilien im Privatvermögen können nach einer Haltedauer von **10 Jahren komplett steuerfrei** verkauft werden.
            """)
