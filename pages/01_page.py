import streamlit as st

st.set_page_config(
    page_title="Página 01",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if not st.session_state.get("authenticated"):
    st.warning("No tienes acceso. Vuelve al inicio.")
    st.stop()

st.markdown("# 📋 Página 01")
st.markdown("---")
st.info("Esta página está en construcción. Aquí irá el contenido de **Acciones**.")
