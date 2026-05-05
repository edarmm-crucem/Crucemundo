import streamlit as st

def inject_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; }
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #FFFFFF !important; }
        [data-testid="stAppViewContainer"] { background: #FFFFFF !important; }
        [data-testid="stHeader"] { background: transparent !important; }
        section[data-testid="stSidebar"] { display: none !important; }

        .block-container, section.stMain > .block-container, .stMainBlockContainer, [data-testid="stMainBlockContainer"] {
            padding-top: 0rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 1900px !important;
            margin: 0 auto !important;
        }

        .login-page { min-height: auto; display: flex; align-items: flex-start; justify-content: center; padding: 0.2rem 1rem 1rem; }
        .login-shell { width: 100%; max-width: 390px; margin: 0 auto; }
        .login-head { text-align: center; margin-bottom: 0.55rem; }
        .login-logo { height: 56px; width: auto; margin: 0 auto 0.65rem auto; display: block; }
        .login-title { font-size: 1.08rem; font-weight: 700; color: #1F2937; }
        .login-subtitle { font-size: 0.78rem; color: #7C869D; margin-top: 0.28rem; }
        .login-form-box { background: transparent !important; border: none !important; padding: 0 !important; }
        .login-note { margin-top: 0.65rem; text-align: center; font-size: 0.72rem; color: #8A93A5; }

        .portal-header { padding: 0.1rem 0 0.55rem 0; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.55rem; }
        .portal-header-left { display: flex; align-items: center; gap: 0.9rem; }
        .portal-logo { height: 42px; width: auto; object-fit: contain; display: block; }
        .portal-title, .portal-title-en { font-size: 0.96rem; font-weight: 700; color: #1F2937; line-height: 1.15; }
        .portal-title-en { margin-top: 0.12rem; }
        .portal-subtitle, .portal-subtitle-en { font-size: 0.72rem; color: #7C869D; line-height: 1.2; }
        .portal-subtitle { margin-top: 0.12rem; }
        .portal-subtitle-en { margin-top: 0.08rem; }
        .user-top { font-size: 0.72rem; color: #566079; white-space: nowrap; }

        .section-head-row { display: flex; align-items: center; justify-content: flex-start; gap: 0.55rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
        .section-eyebrow { display: inline-flex; align-items: center; padding: 0.34rem 0.74rem; border-radius: 999px; background: #EAF1FF; border: 1px solid #D6E3FF; color: #2E5FB8; font-size: 0.66rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0 !important; }
        .web-chip { display: inline-flex; align-items: center; justify-content: center; padding: 0.34rem 0.74rem; border-radius: 999px; background: #FFF3BF; border: 1px solid #F4D35E; color: #7A5900 !important; font-size: 0.70rem; font-weight: 700; line-height: 1; text-decoration: none; white-space: nowrap; }
        .user-pill { display: inline-flex; align-items: center; gap: 0.4rem; margin: 0.02rem 0 1rem; padding: 0.38rem 0.68rem; border-radius: 999px; background: #fff; border: 1px solid #E4E7EF; font-size: 0.72rem; color: #5D6880; max-width: 100%; word-break: break-word; }

        .action-box { width: 100%; min-height: 210px; border-radius: 22px; padding: 1rem; margin-bottom: 0.85rem; display: flex; flex-direction: column; justify-content: space-between; gap: 0.9rem; border: 1px solid transparent; }
        .card-es { background: #F3F7FF; border-color: #D9E5FF; }
        .card-grupos { background: #F4FBF6; border-color: #D8EEDC; }
        .card-salida { background: #FFF8F1; border-color: #F1DFC7; }
        .card-crucero { background: #F7F4FF; border-color: #E4DDF9; }
        .card-excursiones { background: #EEF8FB; border-color: #D5EAF1; }
        .card-nueva-agencia { background: #F1FAF4; border-color: #D7EEDC; }
        .card-buscar-agencia { background: #FFF7EF; border-color: #F4E1CA; }
        .card-cvcfit { background: #FFF2F7; border-color: #F4D7E3; }

        .action-top { display: flex; align-items: flex-start; gap: 0.75rem; }
        .action-icon { width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; }
        .action-text { display: flex; flex-direction: column; gap: 0.10rem; min-width: 0; }
        .action-title, .action-title-en { font-size: 0.95rem; font-weight: 700; color: #1F2937; line-height: 1.1; }
        .action-desc, .action-desc-en { font-size: 0.73rem; color: #6F7B91; line-height: 1.28; }
        .action-button-wrap { display: flex !important; justify-content: flex-start !important; align-items: center !important; width: 100% !important; margin-top: 0.1rem; }

        .panel-inline { margin-top: 1rem; padding-top: 0.2rem; width: 100%; max-width: 1100px; }
        .done-link { display: inline-flex; align-items: center; gap: 0.35rem; margin-top: 0.65rem; background: #D9E9FF; color: #214D92 !important; border: 1px solid #BDD6FF; border-radius: 999px; padding: 0.42rem 0.88rem; font-size: 0.71rem; font-weight: 600; text-decoration: none; }

        .agency-card, .cvcfit-card { background: #FBFCFF; border: 1px solid #E6EBF3; border-radius: 18px; padding: 1rem; margin-top: 0.75rem; }
        .agency-grid, .cvcfit-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.85rem 1rem; }
        .agency-item-label, .cvcfit-item-label { font-size: 0.68rem; color: #7E889D; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.16rem; }
        .agency-item-value, .cvcfit-item-value { font-size: 0.8rem; color: #1F2937; line-height: 1.35; word-break: break-word; }

        .history-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.28rem 0; margin-bottom: 0.35rem; width: 100%; max-width: 620px; }
        .history-num { width: 22px; height: 22px; border-radius: 7px; background: #F2F4F9; border: 1px solid #E3E7F1; display: flex; align-items: center; justify-content: center; font-size: 0.62rem; font-weight: 600; color: #5D6880; flex-shrink: 0; }
        .history-name { font-size: 0.75rem; color: #394255; flex: 1; overflow-wrap: break-word; }
        .history-time { font-size: 0.68rem; color: #A2ABBD; white-space: nowrap; }
        .history-link { font-size: 0.71rem; color: #5D6880; text-decoration: none; font-weight: 500; white-space: nowrap; }

        .portal-footer { margin-top: 1rem; padding: 0.5rem 0 0 0; display: flex; justify-content: space-between; align-items: center; gap: 0.8rem; flex-wrap: wrap; }
        .footer-text { font-size: 0.71rem; color: #A2ABBD; }

        @media (max-width: 1600px) {
            .agency-grid, .cvcfit-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 1300px) {
            .portal-header { flex-direction: column; align-items: flex-start; }
            .portal-footer { flex-direction: column; align-items: flex-start; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
