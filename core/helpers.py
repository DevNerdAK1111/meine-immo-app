import numpy as np
import streamlit as st
from constants import GRUNDERWERBSTEUER_MAP

def fmt_de(val, decimals=2, suffix=""):
    if val is None or np.isnan(val):
        return "-"
    formatted = f"{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} {suffix}".strip() if suffix else formatted

def fmt_eur(val, decimals=0):
    return fmt_de(val, decimals, "€")

def fmt_pct(val, decimals=2):
    return fmt_de(val, decimals, "%")

def fmt_sqm(val, decimals=0):
    return fmt_de(val, decimals, "m²")

def get_smart_defaults(baujahr, objektart):
    bj = int(baujahr) if baujahr else 2000
    obj = str(objektart) if objektart else "Eigentumswohnung"
    age = max(0, 2026 - bj)
    
    if any(k in obj for k in ["Mehrfamilienhaus", "Einfamilienhaus", "Zweifamilienhaus", "Reihenhaus", "Wohn- und Geschäftshaus"]):
        category = "MFH"
    elif "Gewerbe" in obj:
        category = "GEWERBE"
    else:
        category = "ETW"
        
    if age < 5:
        inst = 7.0 if category == "ETW" else (10.0 if category == "MFH" else 6.0)
    elif age <= 15:
        inst = 9.0 if category == "ETW" else (14.0 if category == "MFH" else 8.0)
    elif age <= 30:
        inst = 12.0 if category == "ETW" else (18.0 if category == "MFH" else 10.0)
    else:
        inst = 16.0 if category == "ETW" else (24.0 if category == "MFH" else 14.0)
        
    if "Mikroapartment" in obj:
        mgt = 45.0
    elif category == "MFH":
        mgt = 20.0
    elif category == "GEWERBE":
        mgt = 40.0
    else:
        mgt = 30.0
        
    if "Mikroapartment" in obj:
        vac = 4.0
    elif category == "GEWERBE":
        vac = 7.5
    else:
        vac = 2.0
        
    return inst, mgt, vac

def update_smart_defaults():
    bj = st.session_state.get("baujahr", 2000)
    obj = st.session_state.get("objektart", "Eigentumswohnung")
    inst, mgt, vac = get_smart_defaults(bj, obj)
    st.session_state["inst_sqm"] = inst
    st.session_state["mgt_monat"] = mgt
    st.session_state["vac_rate_pct"] = vac

def update_grwt_from_bundesland():
    bl = st.session_state.get("bundesland", "Niedersachsen")
    st.session_state["grwt_p"] = GRUNDERWERBSTEUER_MAP.get(bl, 0.05) * 100

def update_ist_from_monat():
    qm = st.session_state.get("qm", 0.0)
    monat = st.session_state.get("ist_miete_monat", 0.0)
    st.session_state["ist_sqm"] = (monat / qm) if qm > 0 else 0.0
    if st.session_state.get("target_auto_sync", True):
        st.session_state["target_miete_monat"] = monat
        st.session_state["target_sqm"] = st.session_state["ist_sqm"]

def update_ist_from_sqm():
    qm = st.session_state.get("qm", 0.0)
    sqm_val = st.session_state.get("ist_sqm", 0.0)
    st.session_state["ist_miete_monat"] = (sqm_val * qm) if qm > 0 else 0.0
    if st.session_state.get("target_auto_sync", True):
        st.session_state["target_miete_monat"] = st.session_state["ist_miete_monat"]
        st.session_state["target_sqm"] = sqm_val

def update_target_from_monat():
    qm = st.session_state.get("qm", 0.0)
    monat = st.session_state.get("target_miete_monat", 0.0)
    st.session_state["target_sqm"] = (monat / qm) if qm > 0 else 0.0
    st.session_state["target_auto_sync"] = False

def update_target_from_sqm():
    qm = st.session_state.get("qm", 0.0)
    sqm_val = st.session_state.get("target_sqm", 0.0)
    st.session_state["target_miete_monat"] = (sqm_val * qm) if qm > 0 else 0.0
    st.session_state["target_auto_sync"] = False

def update_qm_callback():
    qm = st.session_state.get("qm", 0.0)
    if qm > 0:
        monat = st.session_state.get("ist_miete_monat", 0.0)
        if monat > 0:
            st.session_state["ist_sqm"] = monat / qm
        if st.session_state.get("target_auto_sync", True):
            st.session_state["target_miete_monat"] = monat
            st.session_state["target_sqm"] = monat / qm

def check_input_sanity(d: dict) -> list:
    warnings = []
    if d['hb_zins'] > 0.15:
        warnings.append(f"Zinssatz Hausbank ({fmt_pct(d['hb_zins']*100)}) ist ungewöhnlich hoch.")
    if d['tax_rate'] > 0.50:
        warnings.append(f"Grenzsteuersatz ({fmt_pct(d['tax_rate']*100)}) liegt über dem Höchstsatz.")
    return warnings
