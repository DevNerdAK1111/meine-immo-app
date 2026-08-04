import numpy as np
import pandas as pd
import numpy_financial as npf

def get_metric_status(val, target, tolerance=0.0):
    if val is None:
        return ("neutral", "Keine Angabe")
    if val >= target:
        return ("green", "Ziel erreicht")
    elif val >= (target - abs(tolerance)):
        return ("yellow", "Im Toleranzbereich")
    else:
        return ("red", "Unter Zielvorgabe")


def calc_projection(data, full_repayment=False):
    kp = data['kaufpreis']
    sanierung = data['sanierung']
    
    # Nebenkosten
    nk = kp * (data['grwt_proz'] + data['notar_proz'] + data['makler_proz']) + data['sonst_nk']
    tot_inv = kp + sanierung + nk
    
    ek_abs = data['ek_euro']
    fk_tot = max(0.0, tot_inv - ek_abs)
    
    # KfW & Hausbank Splitting
    kfw_amt = min(fk_tot, max(0.0, data['kfw_amt'] - data['kfw_grant']))
    hb_loan_init = max(0.0, fk_tot - kfw_amt)
    
    # Zinsbindungs- & Anschluss-Parameter
    zinsbindung = data.get('zinsbindung', 10)
    hb_zins_init = data['hb_zins']
    hb_tilg_init = data['hb_tilg']
    
    folge_zins = data.get('folge_zins', hb_zins_init)
    folge_mode = data.get('folge_mode', "Rate konstant halten (Annuität)")
    folge_tilg = data.get('folge_tilg', hb_tilg_init)
    sondertilg_input = data.get('sondertilg', 0.0)
    
    capex_list = data.get('capex_list', [])
    
    hb_annuity_init = hb_loan_init * (hb_zins_init + hb_tilg_init)
    
    grund_anteil = data.get('grund_anteil', 0.20)
    geb_wert = kp * (1.0 - grund_anteil)
    afa_model = data.get('afa_model', '1_Linear_Standard')
    afa_lin_rate = data.get('afa_lin', 0.02)
    
    book_value = geb_wert + sanierung
    
    qm = data['qm']
    ist_miete_monat = data['ist_sqm'] * qm
    target_miete_monat = data['target_sqm'] * qm
    adj_year = data.get('adj_year', 3)
    
    miet_inc = data.get('miet_inc', 0.015)
    cost_inc = data.get('cost_inc', 0.02)
    val_inc = data.get('val_inc', 0.0)
    exit_cost_pct = data.get('exit_cost', 0.02)
    
    inst_annual_base = data['inst_sqm'] * qm
    mgt_annual_base = data['mgt_monat'] * 12
    hausgeld_non_reimb_base = data['hausgeld_nicht_umlegbar'] * 12
    vac_rate = data['vac_rate']
    tax_rate = data['tax_rate']
    
    hb_rest = hb_loan_init
    kfw_rest = kfw_amt
    obj_val = kp + sanierung
    
    rows = []
    y = 0
    max_years = 50 if full_repayment else 10
    
    first_year_afa = 0.0
    
    while True:
        y += 1
        
        if y <= zinsbindung:
            curr_hb_zins = hb_zins_init
            curr_hb_annuity = hb_annuity_init
        else:
            curr_hb_zins = folge_zins
            if y == zinsbindung + 1 and folge_mode != "Rate konstant halten (Annuität)":
                curr_hb_annuity = hb_rest * (folge_zins + folge_tilg)
            elif folge_mode == "Rate konstant halten (Annuität)":
                curr_hb_annuity = hb_annuity_init
            else:
                curr_hb_annuity = hb_rest * (folge_zins + folge_tilg)

        hb_zins_year = hb_rest * curr_hb_zins
        hb_tilg_year = min(hb_rest, max(0.0, curr_hb_annuity - hb_zins_year))
        hb_rest -= hb_tilg_year
        
        sondertilg_year = min(hb_rest, sondertilg_input)
        hb_rest -= sondertilg_year
        hb_tilg_year += sondertilg_year
        
        kfw_zins_year = kfw_rest * data['kfw_zins']
        kfw_annu = kfw_amt * (data['kfw_zins'] + data['kfw_tilg'])
        kfw_tilg_year = min(kfw_rest, max(0.0, kfw_annu - kfw_zins_year))
        kfw_rest -= kfw_tilg_year
        
        tot_zins = hb_zins_year + kfw_zins_year
        tot_tilg = hb_tilg_year + kfw_tilg_year
        tot_rest = hb_rest + kfw_rest
        
        if y < adj_year:
            m_monat = ist_miete_monat
        else:
            m_monat = target_miete_monat * ((1.0 + miet_inc) ** (y - adj_year))
        
        gross_rent = m_monat * 12
        net_rent = gross_rent * (1.0 - vac_rate)
        
        cost_factor = (1.0 + cost_inc) ** (y - 1)
        inst = inst_annual_base * cost_factor
        mgt = mgt_annual_base * cost_factor
        hg_nr = hausgeld_non_reimb_base * cost_factor
        tot_costs = inst + mgt + hg_nr
        
        year_capex = sum([item['betrag'] for item in capex_list if item['jahr'] == y])
        
        noi = net_rent - tot_costs
        cf_v_st = noi - (tot_zins + tot_tilg) - year_capex
        
        # Exakte AfA-Berechnung inkl. Kombination degressiv + Sonder-AfA
        if afa_model == "1_Linear_Standard":
            afa_annual = (geb_wert + sanierung) * afa_lin_rate
        elif afa_model == "2_Degressiv_§7_5a":
            total_life = max(1, int(round(100 / (afa_lin_rate * 100))))
            remaining_life = max(1, total_life - (y - 1))
            afa_deg = book_value * 0.05
            afa_lin_equiv = book_value / remaining_life
            afa_annual = max(afa_deg, afa_lin_equiv)
            book_value = max(0.0, book_value - afa_annual)
        elif afa_model == "3_Sonder_AfA_§7b":
            base_lin = (geb_wert + sanierung) * afa_lin_rate
            sonder = (geb_wert + sanierung) * 0.05 if y <= 4 else 0.0
            afa_annual = base_lin + sonder
        elif afa_model == "4_Denkmal_§7h_7i":
            base_lin = geb_wert * afa_lin_rate
            denkmal_san = (sanierung * 0.09 if y <= 8 else (sanierung * 0.07 if y <= 12 else 0.0))
            afa_annual = base_lin + denkmal_san
        elif afa_model == "5_Degressiv_plus_Sonder":
            total_life = max(1, int(round(100 / (afa_lin_rate * 100))))
            remaining_life = max(1, total_life - (y - 1))
            afa_deg = book_value * 0.05
            afa_lin_equiv = book_value / remaining_life
            current_deg = max(afa_deg, afa_lin_equiv)
            sonder = (geb_wert + sanierung) * 0.05 if y <= 4 else 0.0
            afa_annual = current_deg + sonder
            book_value = max(0.0, book_value - afa_annual)
        else:
            afa_annual = (geb_wert + sanierung) * afa_lin_rate

        if y == 1:
            first_year_afa = afa_annual

        taxable_income = noi - tot_zins - afa_annual
        tax = taxable_income * tax_rate
        cf_n_st = cf_v_st - tax
        
        obj_val = obj_val * (1.0 + val_inc)
        exit_cost_eur = obj_val * exit_cost_pct
        nav_gross = obj_val - tot_rest
        nav_net = nav_gross - exit_cost_eur
        
        ltv = (tot_rest / obj_val) if obj_val > 0 else 0.0
        brutto_rendite = (gross_rent / kp) if kp > 0 else 0.0
        
        rows.append({
            'Jahr': y,
            'Bruttomietrendite': brutto_rendite,
            'Brutto-Kaltmiete': gross_rent,
            'NOI': noi,
            'Zinsen': tot_zins,
            'Tilgung': tot_tilg,
            'CF v. St.': cf_v_st,
            'AfA': afa_annual,
            'Steuer': tax,
            'CF n. St.': cf_n_st,
            'Restschuld': tot_rest,
            'Objektwert': obj_val,
            'Exit-Kosten': exit_cost_eur,
            'NAV (vor Exit)': nav_gross,
            'NAV (nach Exit)': nav_net,
            'NAV': nav_net,
            'LTV': ltv
        })
        
        if full_repayment and tot_rest <= 1.0:
            break
        if not full_repayment and y >= 10:
            break
        if y >= max_years:
            break
            
    df_proj = pd.DataFrame(rows)
    
    cfs = [-ek_abs] + df_proj['CF n. St.'].tolist()
    cfs[-1] += df_proj.iloc[-1]['NAV (nach Exit)']
    
    try:
        irr = npf.irr(cfs)
        if np.isnan(irr) or np.isinf(irr):
            irr = 0.0
    except:
        irr = 0.0
        
    ek_quote_calc = (ek_abs / tot_inv) if tot_inv > 0 else 0.0
    
    return df_proj, tot_inv, ek_abs, fk_tot, irr, first_year_afa, ek_quote_calc
