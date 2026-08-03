import numpy as np
import numpy_financial as npf
import pandas as pd

def calc_projection(data, full_repayment=False):
    kp = data['kaufpreis']
    san = data['sanierung']
    grwt_rate = data.get('grwt_proz', 0.05)
    nk_proz = grwt_rate + data['notar_proz'] + data['makler_proz']
    nk_abs = kp * nk_proz + data['sonst_nk']
    c_base = kp + san + nk_abs
    ek_euro_input = data.get('ek_euro', 0.0)
    disagio_p = data['disagio_proz']
    disagio_betrag = c_base * (1 - data.get('ek_quote', 0.20)) * disagio_p
    tot_inv = c_base + disagio_betrag
    ek_abs = min(ek_euro_input, tot_inv) if ek_euro_input > 0 else tot_inv * 0.20
    ek_quote_calculated = (ek_abs / tot_inv) if tot_inv > 0 else 0.0
    fk_tot = max(0.0, tot_inv - ek_abs)
    
    kfw_loan = max(0, data['kfw_amt'] - data['kfw_grant'])
    hb_loan = max(0.0, fk_tot - kfw_loan)
    afa_base = (kp + nk_abs) * (1 - data['grund_anteil'])
    
    rows = []
    restschuld_hb = hb_loan
    restschuld_kfw = kfw_loan
    obj_val = tot_inv
    current_sqm_rent = data['ist_sqm']
    
    hausgeld_tot = data['hausgeld']
    hausgeld_nu = data.get('hausgeld_nicht_umlegbar', 0.0)
    eff_nicht_umlegbar = (hausgeld_tot * 0.25) if (hausgeld_tot > 0 and hausgeld_nu <= 0) else hausgeld_nu
    annual_nu_hausgeld = eff_nicht_umlegbar * 12
    
    loan_type = data.get('loan_type', 'Annuitätendarlehen')
    hb_initial_annuity = hb_loan * (data['hb_zins'] + data['hb_tilg']) if hb_loan > 0 else 0
    kfw_initial_annuity = kfw_loan * (data['kfw_zins'] + data['kfw_tilg']) if kfw_loan > 0 else 0
    
    yr = 1
    max_yr = 40 if full_repayment else 10
    building_book_value = afa_base
    
    while yr <= max_yr:
        if full_repayment and yr > 10 and restschuld_hb <= 0 and restschuld_kfw <= 0:
            break
        if yr >= data['adj_year']:
            current_sqm_rent = data['target_sqm'] if yr == data['adj_year'] else current_sqm_rent * (1 + data['miet_inc'])
        
        gross_rent = (current_sqm_rent * data['qm'] + data['park']) * 12
        net_rent = gross_rent * (1 - data['vac_rate'])
        op_costs = (annual_nu_hausgeld + (data['inst_sqm'] * data['qm']) + (data['mgt_monat'] * 12)) * ((1 + data['cost_inc']) ** (yr - 1))
        capex = data['capex_j3'] if yr == 3 else (data['capex_j6'] if yr == 6 else 0)
        noi = net_rent - op_costs - capex
        
        zins_hb = restschuld_hb * data['hb_zins'] if restschuld_hb > 0 else 0.0
        tilg_hb = 0.0
        if restschuld_hb > 0 and yr > data['grace_years']:
            if loan_type == "Annuitätendarlehen":
                tilg_hb = max(0.0, min(restschuld_hb, hb_initial_annuity - zins_hb))
            elif loan_type == "Tilgungsdarlehen":
                tilg_hb = min(restschuld_hb, hb_loan * data['hb_tilg'])
            else:
                tilg_hb = restschuld_hb if (yr == max_yr or (not full_repayment and yr == 10)) else 0.0
                
        zins_kfw = restschuld_kfw * data['kfw_zins'] if (kfw_loan > 0 and restschuld_kfw > 0) else 0.0
        tilg_kfw = 0.0
        if kfw_loan > 0 and restschuld_kfw > 0 and yr > data.get('kfw_grace_years', 0):
            if loan_type == "Endfälliges Darlehen":
                tilg_kfw = restschuld_kfw if (yr == max_yr or (not full_repayment and yr == 10)) else 0.0
            else:
                tilg_kfw = max(0.0, min(restschuld_kfw, kfw_initial_annuity - zins_kfw))
                
        zins_tot = zins_hb + zins_kfw
        actual_sondertilg = min(restschuld_hb, data['sondertilg']) if (restschuld_hb > 0 and yr > data.get('grace_years', 0)) else 0.0
        tilg_tot = tilg_hb + tilg_kfw + actual_sondertilg
        cf_v_st = noi - zins_tot - tilg_tot
        
        if data['afa_model'] == "2_Degressiv_§7_5a":
            afa_val = building_book_value * 0.05
            building_book_value = max(0.0, building_book_value - afa_val)
        elif data['afa_model'] == "3_Sonder_AfA_§7b":
            afa_val = (afa_base * 0.02) + (afa_base * 0.05 if yr <= 4 else 0)
        elif data['afa_model'] == "4_Denkmal_§7h_7i":
            afa_val = afa_base * (0.09 if yr <= 8 else 0.07)
        else:
            afa_val = afa_base * data['afa_lin']
            
        taxable_inc = noi - zins_tot - afa_val - (disagio_betrag if yr == 1 else 0) - (san if (yr == 1 and san <= afa_base * 0.15) else 0)
        tax_val = taxable_inc * data['tax_rate']
        cf_n_st = cf_v_st - tax_val
        
        restschuld_hb = max(0.0, restschuld_hb - tilg_hb - actual_sondertilg)
        restschuld_kfw = max(0.0, restschuld_kfw - tilg_kfw)
        restschuld_tot = restschuld_hb + restschuld_kfw
        
        obj_val *= (1 + data['val_inc'])
        nav = obj_val - restschuld_tot
        
        rows.append({
            "Jahr": yr, "Bruttomietrendite": gross_rent / kp if kp > 0 else 0,
            "Brutto-Kaltmiete": gross_rent, "NOI": noi, "Zinsen": zins_tot,
            "Tilgung": tilg_tot, "CF v. St.": cf_v_st, "AfA": afa_val,
            "Steuer": tax_val, "CF n. St.": cf_n_st, "Restschuld": restschuld_tot,
            "Objektwert": obj_val, "NAV": nav, "LTV": restschuld_tot / obj_val if obj_val > 0 else 0
        })
        yr += 1
        if not full_repayment and yr > 10:
            break
            
    df = pd.DataFrame(rows)
    cf_stream = [-ek_abs] + list(df['CF n. St.'].iloc[:-1]) + [df['CF n. St.'].iloc[-1] + (df['Objektwert'].iloc[-1] * (1 - data['exit_cost']) - df['Restschuld'].iloc[-1])]
    try:
        irr = npf.irr(cf_stream)
    except:
        irr = 0.0
    return df, tot_inv, ek_abs, fk_tot, irr, afa_base, ek_quote_calculated

def get_metric_status(val, tg, ty):
    return ("green", "Zielwert erreicht") if val >= tg else ("yellow", "Im Toleranzbereich") if val >= ty else ("red", "Kriterium unterschritten")
