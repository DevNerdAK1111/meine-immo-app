import streamlit as st
import pandas as pd
import json
from core.calculations import calc_projection
from core.helpers import fmt_eur, fmt_sqm, fmt_de, fmt_pct
from core.database import db_get_projects, db_delete_project

def render_pipeline_view(sb_client):
    st.markdown("## Investment-Pipeline")
    st.markdown("<p style='color:#555759;'>Übersicht aller gespeicherten Objekte (inkl. lokalem Backup).</p>", unsafe_allow_html=True)

    projects = db_get_projects(sb_client, st.session_state["user_email"])
    
    col_bk1, col_bk2 = st.columns(2)
    if projects:
        projects_json = json.dumps(projects, default=str, ensure_ascii=False, indent=2)
        col_bk1.download_button(
            label="📥 Projekte als Backup herunterladen (.json)",
            data=projects_json,
            file_name="valuon_estate_backup.json",
            mime="application/json",
            use_container_width=True
        )
    
    uploaded_backup = col_bk2.file_uploader("📤 Backup wiederherstellen (.json)", type=["json"])
    if uploaded_backup:
        try:
            imported_data = json.load(uploaded_backup)
            if isinstance(imported_data, list):
                if "local_projects" not in st.session_state:
                    st.session_state["local_projects"] = []
                for p in imported_data:
                    if p not in st.session_state["local_projects"]:
                        st.session_state["local_projects"].append(p)
                st.success("Backup erfolgreich eingelesen!")
                st.rerun()
        except Exception as e:
            st.error(f"Fehler beim Einlesen des Backups: {e}")

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
            
            loc = d.get("stadt", "")
            if d.get("stadtteil"): loc += f" ({d.get('stadtteil')})"
            if not loc: loc = d.get("bundesland", "Unbekannt")
                
            table_rows.append({
                "Objektname": p["project_name"],
                "Typ": d.get("objektart", "Eigentumswohnung"),
                "Standort": loc,
                "Kaufpreis": fmt_eur(d.get('kaufpreis', 0)),
                "Fläche": fmt_sqm(d.get('qm', 0)),
                "Cashflow (netto)": f"{fmt_de(calc_p.loc[0, 'CF n. St.']/12, 2)} €/M",
                "Bruttomietrendite": fmt_pct(calc_p.loc[0, 'Bruttomietrendite']*100),
                "10J-IRR": fmt_pct(irr_p*100)
            })
            
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
        
        st.divider()
        col_act1, col_act2 = st.columns(2)
        selected_proj = col_act1.selectbox("Projekt auswählen", [p["project_name"] for p in projects])
        
        if col_act1.button("In Analyse-Rechner laden", type="primary", use_container_width=True):
            p_target = next(p for p in projects if p["project_name"] == selected_proj)
            for k, v in p_target["input_data"].items():
                st.session_state[k] = v
            st.session_state["nav_choice"] = "Analyse"
            st.session_state["trigger_analysis"] = True
            st.rerun()

        if col_act2.button("Projekt löschen", use_container_width=True):
            p_target = next(p for p in projects if p["project_name"] == selected_proj)
            db_delete_project(sb_client, p_target["id"])
            st.rerun()
    else:
        st.info("Bisher keine Projekte gespeichert.")
