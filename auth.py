import streamlit as st
from config import LOGO_URL, VALID_USERS, VALID_PASSWORD

def render_login():
    st.markdown('<div class="login-page"><div class="login-shell">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="login-head">
            <img class="login-logo" src="{LOGO_URL}" alt="Logo">
            <div class="login-title">Acceso</div>
            <div class="login-subtitle">Access</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="login-form-box">', unsafe_allow_html=True)
    with st.form("loginform", clear_on_submit=False):
        email = st.text_input("Mail / Email", placeholder="support@crucemundo.com")
        password = st.text_input("Contraseña / Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar / Login")
        if submitted:
            emailclean = email.strip().lower()
            if not emailclean or not password:
                st.error("Debes introducir mail y contraseña / Please enter email and password.")
            elif emailclean not in VALID_USERS:
                st.error("Usuario no autorizado / Unauthorized user.")
            elif password != VALID_PASSWORD:
                st.error("Contraseña incorrecta / Incorrect password.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["useremail"] = emailclean
                st.session_state["displayname"] = VALID_USERS[emailclean]
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="login-note">El mail valida el acceso y el alias se usará para nombrar la sesión / Email validates access and the alias will be used to name the session.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div></div>", unsafe_allow_html=True)
