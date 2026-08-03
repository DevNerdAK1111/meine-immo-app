import streamlit as st

def load_valuon_styles():
    st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
            color: #2B2D2F;
            background-color: #F7F4EC;
        }
        
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1200px;
            background-color: #F7F4EC;
        }
        
        header[data-testid="stHeader"] {
            background: transparent !important;
            z-index: 1;
        }

        section[data-testid="stSidebar"] {
            width: 400px !important;
            min-width: 400px !important;
        }

        section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
            min-height: 42px !important;
            display: flex !important;
            align-items: flex-end !important;
            margin-bottom: 4px !important;
        }

        div[data-testid="InputInstructions"], 
        .stInputInstructions, 
        div[aria-live="polite"] {
            display: none !important;
        }
        
        .landing-hero {
            background: linear-gradient(135deg, #13381A 0%, #1c4d26 50%, #2b2d2f 100%);
            border-radius: 20px;
            padding: 50px 40px;
            color: #F7F4EC;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(19, 56, 26, 0.15);
            position: relative;
            overflow: hidden;
        }
        
        .landing-hero::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: url('https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=80');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            opacity: 0.12;
            z-index: 0;
        }
        
        .landing-content {
            position: relative;
            z-index: 1;
        }

        .valuon-card {
            background-color: #ffffff;
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid #D4C9B8;
            box-shadow: 0 4px 12px rgba(19, 56, 26, 0.03);
        }
        
        .valuon-placeholder {
            background: linear-gradient(135deg, #ffffff 0%, #F7F4EC 100%);
            border: 2px dashed #D4C9B8;
            border-radius: 16px;
            padding: 35px 30px;
            text-align: center;
            margin: 20px 0;
        }
        
        .stButton > button {
            border-radius: 980px !important;
            font-weight: 500 !important;
            padding: 8px 20px !important;
            transition: all 0.2s ease !important;
            border: 1px solid #D4C9B8 !important;
            background-color: #ffffff !important;
            color: #2B2D2F !important;
        }
        
        .stButton > button:hover {
            border-color: #13381A !important;
            color: #13381A !important;
            background-color: #F7F4EC !important;
        }
        
        .stButton > button[kind="primary"] {
            background-color: #13381A !important;
            color: #ffffff !important;
            border-color: #13381A !important;
        }
        
        .stButton > button[kind="primary"]:hover {
            background-color: #1b4d25 !important;
            color: #ffffff !important;
        }

        .metric-card {
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 15px;
            border: 1px solid #D4C9B8;
            background-color: #ffffff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
            position: relative;
            overflow: visible !important;
        }
        .metric-green { border-left: 4px solid #13381A; color: #13381A; }
        .metric-yellow { border-left: 4px solid #A37841; color: #5a4223; }
        .metric-red { border-left: 4px solid #8b3a2b; color: #6b2e22; }
        
        .metric-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .metric-title { 
            font-size: 0.78rem; 
            font-weight: 600; 
            text-transform: uppercase; 
            letter-spacing: 0.5px; 
            opacity: 0.75; 
        }
        .metric-value { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.5px; }
        .metric-status { font-size: 0.8rem; font-weight: 600; margin-top: 4px; }
        
        .tooltip-container {
            position: relative;
            display: inline-block;
            cursor: pointer;
        }
        
        .tooltip-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 17px;
            height: 17px;
            border-radius: 50%;
            background-color: #F4EFE6;
            color: #A37841;
            border: 1px solid #D4C9B8;
            font-size: 0.7rem;
            font-weight: 700;
            font-family: serif;
            font-style: italic;
            transition: all 0.2s ease;
        }
        
        .tooltip-container:hover .tooltip-icon {
            background-color: #13381A;
            color: #F7F4EC;
            border-color: #13381A;
        }
        
        .tooltip-box {
            visibility: hidden;
            width: 260px;
            background-color: #2B2D2F;
            color: #F7F4EC;
            text-align: left;
            border-radius: 10px;
            padding: 12px 14px;
            position: absolute;
            z-index: 99;
            bottom: 130%;
            right: 0;
            opacity: 0;
            transition: opacity 0.2s ease, transform 0.2s ease;
            transform: translateY(6px);
            font-size: 0.78rem;
            font-weight: 400;
            line-height: 1.4;
            box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            border: 1px solid #A37841;
            pointer-events: none;
        }

        .tooltip-box strong {
            color: #A37841;
            display: block;
            margin-bottom: 4px;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .tooltip-container:hover .tooltip-box {
            visibility: visible;
            opacity: 1;
            transform: translateY(0);
        }
        
        .badge-expose {
            background-color: #EBF2EC;
            color: #13381A;
            padding: 4px 12px;
            border-radius: 10px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 10px;
        }
        
        .nk-sub-badge {
            background-color: #F4EFE6;
            color: #555759;
            border: 1px solid #D4C9B8;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 0.8rem;
            font-weight: 600;
            text-align: center;
            margin-top: -6px;
            margin-bottom: 10px;
        }

        .nk-total-badge {
            background-color: #F4EFE6;
            color: #13381A;
            border: 1px solid #D4C9B8;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 0.9rem;
            font-weight: 700;
            display: flex;
            justify-content: space-between;
            margin-top: 8px;
            margin-bottom: 12px;
        }
    </style>
    """, unsafe_allow_html=True)
