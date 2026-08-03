import streamlit as st
import pandas as pd
import json
from core.calculations import calc_projection
from core.helpers import fmt_eur, fmt_sqm, fmt_de, fmt_pct
from core.database import db_get_projects, db_delete_project

def render_pipeline_view(sb_client):
    st.markdown("## Objekt Datenbank")
    st.markdown("<p style='color:#555759;'>Zentrale Verwaltung aller gespeicherten Immobilien-Objekte.</p>", unsafe_allow_html=True)

    projects = db_get_projects(sb_client, st.session_state["user_email"])
    
    # Optionaler Export-Button für Backups bleibt diskret im Hintergrund
    with st.expander("🛠️ Daten-Export / Backup", expanded=False):
        if projects:
            projects_json = json.dumps(projects, default=str, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 Alle Projekte als JSON-Backup herunterladen",
                data=projects_json,
                file_name="valuon_estate_backup.json",
                mime="application/json",
                use_container_width=True
            )

    st.divider()

    if projects:
        table_rows = []
        for p in projects:
            d = p["input_data"]
            calc_p, _, _, _, irr_p, _, _ = calc_projection({
                'kaufpreis': d.get("kaufpreis", 0), 'sanierung': d.get("sanierung", 0),
                'bundesland': d.get("bundesland", "Niedersachsen"),
                'grwt_proz': d.get("grwt_p", 5.0)/100, 'notar_proz': d.get("notar_p", 2.0)/100,
                'makler_proz': d.get("makler_p", 3.57)/100, 'sonst_nk': d.get("sonst_nk", 0.0),
                'disagio_proz': d.get("disagio_p", 0)/100, 'ek_euro': d.get("ek_euro", 0.0),
                'ek_quote': d.get("ek_quote", 0.2), 'loan_type': d.get("loan_type", "Annuitätendarlehen"),
                'hb_zins': d.get("hb_zins", 3.8)/100, 'hb_tilg': d.get("hb_tilg", 2.0)/100,
                'grace_years': d.get("grace_years", 0), 'kfw_amt': d.get("kfw_amt", 0),
                'kfw_zins': d.get("kfw_zins", 2.1)/100, 'kfw_tilg': d.get("kfw_tilg", 3.0)/100,
                'kfw_grace_years': d.get("kfw_grace_years", 0), 'kfw_grant': d.get("kfw_grant", 0),
                'sondertilg': d.get("sondertilg", 0), 'ist_sqm': d.get("ist_sqm", 0),
                'target_sqm': d.get("target_sqm", 0) or d.get("ist_sqm", 0),
                'adj_year': d.get("adj_year", 3), 'park': d.get("park", 0),
                'vac_rate': d.get("vac_rate_pct", 2.0)/100, 'qm': d.get("qm", 0),
                'hausgeld': d.get("hausgeld", 0), 'hausgeld_nicht_umlegbar': d.get("hausgeld_nicht_umlegbar", 0),
                'inst_sqm': d.get("inst_sqm", 12.0), 'mgt_monat': d.get("mgt_monat", 30.0),
                'capex_j3': d.get("capex_j3", 0), 'capex_j6': d.get("capex_j6", 0),
                'tax_rate': d.get("tax_rate_pct", 42.0)/100, 'afa_model': d.get("afa_model", "1_Linear_Standard"),
                'afa_lin': d.get("afa_lin", 2.0)/100, 'miet_inc': d.get("miet_inc", 1.5)/100,
                'cost_inc': d.get("cost_inc", 2.0)/100, 'val_inc': d.get("val_inc", 1.5)/100,
                'wacc': d.get("wacc", 6.0)/100, 'exit_cost': d.get("exit_cost", 2.0)/100,
                'grund_anteil': d.get("grund_anteil", 0.2)
            }, full_repayment=False)
            
            stadt_str = d.get("stadt", "-")
            if d.get("stadtteil"): 
                stadt_str += f" ({d.get('stadtteil')})"
                
            table_rows.append({
                "Objektname": p["project_name"],
                "Typ": d.get("objektart", "Eigentumswohnung"),
                "Stadt": stadt_str,
                "Kaufpreis": fmt_eur(d.get('kaufpreis', 0)),
                "Fläche": fmt_sqm(d.get('qm', 0)),
                "Netto-CF": f"{fmt_de(calc_p.loc[0, 'CF n. St.']/12, 0)} €/M",
                "Rendite": fmt_pct(calc_p.loc[0, 'Bruttomietrendite']*100),
                "10J-IRR": fmt_pct(irr_p*100)
            })
            
        df_display = pd.DataFrame(table_rows)
        
        st.markdown("💡 *Klicke direkt auf eine Zeile in der Tabelle, um das Objekt auszuwählen:*")
        
        # Interaktive Tabelle mit Zeilenauswahl (verhindert horizontales Scrollen durch saubere Spaltenbreiten)
        event = st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        selected_rows = event.selection.rows
        
        if selected_rows:
            idx = selected_rows[0]
            p_target = projects[idx]
            
            st.markdown(f"**Ausgewähltes Objekt:** `{p_target['project_name']}`")
            
            col_act1, col_act2 = st.columns(2)
            if col_act1.button("🚀 In Analyse-Rechner laden", type="primary", use_container_width=True):
                for k, v in p_target["input_data"].items():
                    st.session_state[k] = v
                st.session_state["nav_choice"] = "Analyse"
                st.session_state["trigger_analysis"] = True
                st.rerun()

            if col_act2.button("🗑️ Projekt aus Datenbank löschen", use_container_width=True):
                db_delete_project(sb_client, p_target["id"])
                st.rerun()
        else:
            st.info("👆 Bitte klicke oben in der Tabelle auf ein Objekt, um es zu laden oder zu löschen.")
    else:
        st.info("Bisher keine Objekte in der Datenbank gespeichert.")
