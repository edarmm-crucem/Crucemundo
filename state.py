import streamlit as st

DEFAULTS = {
    "authenticated": False,
    "useremail": "",
    "displayname": "",
    "confirmstate": "idle",
    "historial": [],
    "sessiontype": "",
    "activepanel": None,
    "opensalidaform": False,
    "opencruceroform": False,
    "opennuevaagenciaform": False,
    "openbuscaragenciaform": False,
    "opencvcfitform": False,
    "salidayear": None,
    "salidaboat": None,
    "salidaname": None,
    "cruceroyear": None,
    "cruceroboat": None,
    "agencymatches": [],
    "agencyselectedidx": None,
    "cvcfit_locator": "",
    "cvcfit_result": None,
}

def init_state():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def clear_salida_state():
    for k in [
        "salidayear", "salidaboat", "salidaname",
        "salidayearwidget", "salidaboatwidget", "salidanamewidget"
    ]:
        st.session_state.pop(k, None)

def clear_crucero_state():
    for k in [
        "cruceroyear", "cruceroboat",
        "cruceroyearwidget", "cruceroboatwidget"
    ]:
        st.session_state.pop(k, None)

def clear_agencia_state():
    for k in [
        "agencymatches", "agencyselectedidx", "agencysearchquery",
        "agnombre", "agcodigo", "aggrupogest", "agtelefono", "agemail",
        "agdireccion", "agcomision", "agcomisionoferta", "agcomision2x1",
        "agiva", "agivaservicioopcional"
    ]:
        st.session_state.pop(k, None)

def clear_cvcfit_state():
    for k in ["cvcfit_locator", "cvcfit_result", "cvcfitlocatorwidget"]:
        st.session_state.pop(k, None)

def close_all_panels():
    st.session_state["opensalidaform"] = False
    st.session_state["opencruceroform"] = False
    st.session_state["opennuevaagenciaform"] = False
    st.session_state["openbuscaragenciaform"] = False
    st.session_state["opencvcfitform"] = False

def open_panel(panelname):
    close_all_panels()
    if panelname == "salida":
        clear_crucero_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["opensalidaform"] = True
    elif panelname == "crucero":
        clear_salida_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["opencruceroform"] = True
    elif panelname == "nuevaagencia":
        clear_salida_state()
        clear_crucero_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["opennuevaagenciaform"] = True
    elif panelname == "buscaragencia":
        clear_salida_state()
        clear_crucero_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["openbuscaragenciaform"] = True
    elif panelname == "cvcfit":
        clear_salida_state()
        clear_crucero_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["opencvcfitform"] = True
    st.session_state["activepanel"] = panelname

def clear_all_selectors():
    clear_salida_state()
    clear_crucero_state()
    clear_agencia_state()
    clear_cvcfit_state()
    close_all_panels()
    st.session_state["activepanel"] = None

def do_logout():
    keys_to_delete = list(st.session_state.keys())
    for k in keys_to_delete:
        st.session_state.pop(k, None)
    st.rerun()

def reset_salida_downstream(level):
    if level == "year":
        st.session_state["salidaboat"] = None
        st.session_state["salidaname"] = None
        st.session_state.pop("salidaboatwidget", None)
        st.session_state.pop("salidanamewidget", None)
    elif level == "boat":
        st.session_state["salidaname"] = None
        st.session_state.pop("salidanamewidget", None)

def on_year_change():
    st.session_state["salidayear"] = st.session_state.get("salidayearwidget")
    reset_salida_downstream("year")

def on_boat_change():
    st.session_state["salidaboat"] = st.session_state.get("salidaboatwidget")
    reset_salida_downstream("boat")

def on_salida_change():
    st.session_state["salidaname"] = st.session_state.get("salidanamewidget")

def reset_crucero_downstream(level):
    if level == "year":
        st.session_state["cruceroboat"] = None
        st.session_state.pop("cruceroboatwidget", None)

def on_crucero_year_change():
    st.session_state["cruceroyear"] = st.session_state.get("cruceroyearwidget")
    reset_crucero_downstream("year")

def on_crucero_boat_change():
    st.session_state["cruceroboat"] = st.session_state.get("cruceroboatwidget")
