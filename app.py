import time
from datetime import datetime
import streamlit as st

from config import 11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm
from state import init_state, do_logout
from styles import inject_styles
from auth import render_login
from ui_components import render_header, render_cards_grid, render_step
from panels import (
    render_panel_salida,
    render_panel_crucero,
    render_panel_nueva_agencia,
    render_panel_buscar_agencia,
    render_panel_cvcfit,
)

st.set_page_config(
    page_title="Crucemundo Hub",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_state()
inject_styles()

if not st.session_state["authenticated"]:
    render_login()
    st.stop()

confirmstate = st.session_state.get("confirmstate", "idle")
savedname = st.session_state.get("nombrecopia")
savedurl = st.session_state.get("copyurl")
processtitle = st.session_state.get("processtitle", "Estado del Proceso · Process Status")

render_header()
st.markdown('<div class="main-content">', unsafe_allow_html=True)
render_cards_grid()

render_panel_salida()
render_panel_crucero()
render_panel_nueva_agencia()
render_panel_buscar_agencia()
render_panel_cvcfit()

if confirmstate in ["step1", "step2", "step3", "done"]:
    st.markdown('<div class="panel-inline" style="max-width:520px;">', unsafe_allow_html=True)
    st.markdown(f"### {processtitle}")
    if confirmstate == "step1":
        render_step("Progreso · Progress", "Preparando plantilla · Preparing template...", "active")
    elif confirmstate == "step2":
        render_step("Progreso · Progress", "Generando copia en Drive · Creating Drive copy...", "active")
    elif confirmstate == "step3":
        render_step("Progreso · Progress", "Abriendo sesión · Opening session...", "active")
    elif confirmstate == "done":
        render_step("Progreso · Progress", "Completo · Complete", "done")
        st.markdown(
            f"""
            <div style="margin-top:0.8rem;">
                <div style="font-size:0.76rem;color:#1F2937;font-weight:600;">Sesión creada · Session created</div>
                <div style="font-size:0.71rem;color:#657087;margin-top:0.15rem;line-height:1.3;">
                    Puedes abrir tu sesión en el botón de abajo · You can open your session with the button below.
                </div>
                <a class="done-link" href="{savedurl}" target="_blank">Abrir sesión · Open session</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if confirmstate == "step1":
        time.sleep(0.7)
        st.session_state["confirmstate"] = "step2"
        st.rerun()
    elif confirmstate == "step2":
        time.sleep(0.7)
        st.session_state["confirmstate"] = "step3"
        st.rerun()
    elif confirmstate == "step3":
        time.sleep(0.7)
        st.session_state["confirmstate"] = "done"
        existing = [h["nombre"] for h in st.session_state["historial"]]
        if savedname and savedname not in existing:
            st.session_state["historial"].insert(0, {
                "nombre": savedname,
                "hora": datetime.now().strftime("%H:%M:%S"),
                "url": savedurl,
            })
        st.rerun()

if confirmstate == "done" and savedname and not st.session_state.get(f"opened_{savedname}"):
    st.session_state[f"opened_{savedname}"] = True
    st.markdown(
        f"<script>setTimeout(()=>window.open('{savedurl}','_blank'),300);</script>",
        unsafe_allow_html=True,
    )

st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
if st.button("Cerrar sesión / Logout", key="btnlogout"):
    do_logout()

if st.session_state.get("historial"):
    st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-eyebrow">ESTA SESIÓN · THIS SESSION</div>', unsafe_allow_html=True)
    for i, entry in enumerate(st.session_state["historial"], 1):
        st.markdown(
            f"""
            <div class="history-row">
                <div class="history-num">{i}</div>
                <div class="history-name">{entry["nombre"]}</div>
                <div class="history-time">{entry["hora"]}</div>
                <a class="history-link" href="{entry["url"]}" target="_blank">Abrir · Open</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    f"""
    <div class="portal-footer">
        <span class="footer-text">Panel de Control · Control Panel · v4.3.1</span>
        <span class="footer-text">Raíz Drive · Drive Root · {DRIVE_ROOT_ID}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)
