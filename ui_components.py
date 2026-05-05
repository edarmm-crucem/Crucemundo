from datetime import datetime
import urllib.parse
import streamlit as st

from config import (
    LOGO_URL, FOLDER_ID, TEMPLATE_ID_ES, TEMPLATE_ID_GRUPOS, EXCURSIONES_SHEET_ID
)
from state import clear_all_selectors, open_panel

def get_saludo():
    hora = datetime.now().hour
    if 6 <= hora < 14:
        return "Buenos días"
    elif 14 <= hora < 21:
        return "Buenas tardes"
    return "Buenas noches"

def get_saludo_en():
    hora = datetime.now().hour
    if 6 <= hora < 14:
        return "Good morning"
    elif 14 <= hora < 21:
        return "Good afternoon"
    return "Good evening"

def render_step(label, detail, state):
    dot_class = {"done": "sd-done", "active": "sd-active", "wait": "sd-wait"}[state]
    text_class = {"done": "st-done", "active": "st-active", "wait": "st-wait"}[state]
    symbol = {"done": "✓", "active": "•", "wait": "•"}[state]
    st.markdown(
        f"""
        <div class="step">
            <div class="step-dot {dot_class}">{symbol}</div>
            <div class="step-content">
                <div class="{text_class}">{label}</div>
                <div class="step-detail">{detail}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def iniciar_proceso(sessiontype, templateid, prefixname, processtitle):
    clear_all_selectors()
    now = datetime.now()
    fechastr = now.strftime("%Y%m%d-%H%M")
    displayuser = st.session_state.get("displayname", "").strip() or "Sin usuario"
    nombrecopia = f"SESION - {displayuser} - {prefixname} - {fechastr}"
    copyurl = (
        f"https://docs.google.com/spreadsheets/d/{templateid}/copy"
        f"?copyDestination={FOLDER_ID}"
        f"&title={urllib.parse.quote(nombrecopia)}"
    )
    st.session_state["confirmstate"] = "step1"
    st.session_state["sessiontype"] = sessiontype
    st.session_state["nombrecopia"] = nombrecopia
    st.session_state["copyurl"] = copyurl
    st.session_state["processtitle"] = processtitle
    st.rerun()

def render_header():
    useremail = st.session_state.get("useremail", "").strip()
    displayuser = st.session_state.get("displayname", "").strip() or "Sin usuario"
    saludo = get_saludo()
    saludo_en = get_saludo_en()

    st.markdown(
        f"""
        <div class="portal-header">
            <div class="portal-header-left">
                <img class="portal-logo" src="{LOGO_URL}" alt="Logo">
                <div>
                    <div class="portal-title">{saludo}, {displayuser}. ¿Qué hacemos hoy?</div>
                    <div class="portal-title-en">{saludo_en}, {displayuser}. What are we doing today?</div>
                    <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
                    <div class="portal-subtitle-en">Tools and automations · Google Drive backend</div>
                </div>
            </div>
            <div class="user-top">{displayuser}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-head-row">
            <div class="section-eyebrow">ACCIONES RÁPIDAS · QUICK ACTIONS</div>
            <a class="web-chip" href="https://www.crucemundo.es" target="_blank" rel="noopener noreferrer">Ir a Crucemundo</a>
            <a class="web-chip" href="https://mail.google.com" target="_blank" rel="noopener noreferrer">Gmail</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="user-pill">{displayuser} · {useremail}</div>', unsafe_allow_html=True)

def render_action_card_open(card_class, icon, title, title_en, desc, desc_en):
    st.markdown(
        f"""
        <div class="action-box {card_class}">
            <div class="action-top">
                <div class="action-icon">{icon}</div>
                <div class="action-text">
                    <div class="action-title">{title}</div>
                    <div class="action-title-en">{title_en}</div>
                    <div class="action-desc">{desc}</div>
                    <div class="action-desc-en">{desc_en}</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )

def render_action_card_close():
    st.markdown("</div></div>", unsafe_allow_html=True)

def render_cards_grid():
    confirmstate = st.session_state.get("confirmstate", "idle")
    displayuser = st.session_state.get("displayname", "").strip() or "Sin usuario"
    excursionesurl = f"https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID}/edit"

    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8, gap="medium")

    with col1:
        render_action_card_open("card-es", "📄", "Nueva Confirmación", "New Confirmation",
                                f"Crear sesión MASTER de trabajo para {displayuser}",
                                f"Create MASTER working session for {displayuser}")
        if confirmstate in ["idle", "done"]:
            if st.button("Crear Sesión ES", key="btncreares"):
                iniciar_proceso("es", TEMPLATE_ID_ES, "MASTER", "Estado del Proceso · Process Status · Crear Sesión MASTER/CONFIRMATION")
        else:
            st.button("Crear Sesión ES", key="btncrearesdis", disabled=True)
        render_action_card_close()

    with col2:
        render_action_card_open("card-grupos", "👥", "Nueva Confirmación GRUPOS", "New GROUPS Confirmation",
                                f"Crear sesión MASTER GRUPOS de trabajo para {displayuser}",
                                f"Create MASTER GROUPS working session for {displayuser}")
        if confirmstate in ["idle", "done"]:
            if st.button("Crear Sesión GRUPOS", key="btncreargrupos"):
                iniciar_proceso("grupos", TEMPLATE_ID_GRUPOS, "MASTER GRUPOS", "Estado del Proceso · Process Status · Crear Sesión MASTER/GRUPOS")
        else:
            st.button("Crear Sesión GRUPOS", key="btncreargruposdis", disabled=True)
        render_action_card_close()

    with col3:
        render_action_card_open("card-salida", "🔎", "Ir a Salida", "Go to Departure",
                                "Buscar una salida existente por año, barco y código de salida",
                                "Find an existing departure by year, ship and departure code")
        if st.button("Buscar Salida", key="btnirsalida"):
            open_panel("salida")
            st.rerun()
        render_action_card_close()

    with col4:
        render_action_card_open("card-crucero", "🛳️", "Crear crucero", "Create Cruise",
                                "Crear salida nueva desde plantilla y guardarla en año/barco",
                                "Create a new departure from template and save it in year/ship")
        if st.button("Nuevo Crucero", key="btncrearcruceroopen"):
            open_panel("crucero")
            st.rerun()
        render_action_card_close()

    with col5:
        render_action_card_open("card-excursiones", "🧭", "Excursiones", "Excursions",
                                "Abrir la hoja de Excursiones",
                                "Open the Excursions sheet")
        st.markdown(f'<a class="done-link" href="{excursionesurl}" target="_blank">Abrir Excursiones</a>', unsafe_allow_html=True)
        render_action_card_close()

    with col6:
        render_action_card_open("card-nueva-agencia", "🏢", "Nueva Agencia", "New Agency",
                                "Crear una agencia y guardarla en la hoja Datos",
                                "Create an agency and save it in Datos sheet")
        if st.button("Nueva Agencia", key="btnnuevaagencia"):
            open_panel("nuevaagencia")
            st.rerun()
        render_action_card_close()

    with col7:
        render_action_card_open("card-buscar-agencia", "📇", "Buscar Agencia", "Find Agency",
                                "Buscar por cualquier dato y mostrar la ficha completa",
                                "Search by any known value and show the full record")
        if st.button("Buscar Agencia", key="btnbuscaragencia"):
            open_panel("buscaragencia")
            st.rerun()
        render_action_card_close()

    with col8:
        render_action_card_open("card-cvcfit", "🧾", "CVC Fit", "CVC Fit",
                                "Buscar por localizador y generar el DOC del contrato",
                                "Find by locator and generate the contract DOC")
        if st.button("Abrir CVC Fit", key="btncvcfitopen"):
            open_panel("cvcfit")
            st.rerun()
        render_action_card_close()
