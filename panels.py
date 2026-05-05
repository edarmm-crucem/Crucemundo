from datetime import date
import streamlit as st

from config import AGENCY_FIELDS
from state import (
    on_year_change, on_boat_change, on_salida_change,
    on_crucero_year_change, on_crucero_boat_change
)
from agency_service import append_agency_row, percent_to_sheet_decimal, search_agencies
from cruise_service import get_years, get_boats, get_departures, create_crucero_file
from cvcfit_service import build_cvc_fit_from_locator, build_cvc_fit_doc

def render_panel_salida():
    if not st.session_state.get("opensalidaform"):
        return
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Seleccionar salida · Select departure")
    try:
        years = get_years()
        currentyear = st.session_state.get("salidayear")
        if currentyear not in years:
            currentyear = None
        selectedyear = st.selectbox(
            "AÑO / YEAR",
            options=years,
            index=years.index(currentyear) if currentyear in years else None,
            placeholder="Selecciona un año / Select a year",
            key="salidayearwidget",
            on_change=on_year_change,
        )
        if selectedyear != st.session_state.get("salidayear"):
            st.session_state["salidayear"] = selectedyear

        boats = get_boats(selectedyear) if selectedyear else []
        currentboat = st.session_state.get("salidaboat")
        if currentboat not in boats:
            currentboat = None
        selectedboat = st.selectbox(
            "BARCO / SHIP",
            options=boats,
            index=boats.index(currentboat) if currentboat in boats else None,
            placeholder="Selecciona un barco / Select a ship",
            key="salidaboatwidget",
            on_change=on_boat_change,
            disabled=not selectedyear,
        )
        if selectedboat != st.session_state.get("salidaboat"):
            st.session_state["salidaboat"] = selectedboat

        departures = get_departures(selectedyear, selectedboat) if selectedyear and selectedboat else []
        departurenames = [d["nombre"] for d in departures]
        currentdeparture = st.session_state.get("salidaname")
        if currentdeparture not in departurenames:
            currentdeparture = None
        selecteddeparture = st.selectbox(
            "SALIDA / DEPARTURE",
            options=departurenames,
            index=departurenames.index(currentdeparture) if currentdeparture in departurenames else None,
            placeholder="Selecciona una salida / Select a departure",
            key="salidanamewidget",
            on_change=on_salida_change,
            disabled=not selectedboat,
        )
        if selecteddeparture != st.session_state.get("salidaname"):
            st.session_state["salidaname"] = selecteddeparture

        if selecteddeparture:
            selectedobj = next((d for d in departures if d["nombre"] == selecteddeparture), None)
            if selectedobj:
                st.markdown(
                    f'<a class="done-link" href="{selectedobj["url"]}" target="_blank">Abrir salida · Open departure</a>',
                    unsafe_allow_html=True,
                )
    except Exception as e:
        st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)

def render_panel_crucero():
    if not st.session_state.get("opencruceroform"):
        return
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Crear crucero · Create cruise")
    try:
        years = get_years()
        currentcyear = st.session_state.get("cruceroyear")
        if currentcyear not in years:
            currentcyear = None
        cruceroyear = st.selectbox(
            "AÑO DESTINO / TARGET YEAR",
            options=years,
            index=years.index(currentcyear) if currentcyear in years else None,
            placeholder="Selecciona un año / Select a year",
            key="cruceroyearwidget",
            on_change=on_crucero_year_change,
        )
        if cruceroyear != st.session_state.get("cruceroyear"):
            st.session_state["cruceroyear"] = cruceroyear

        cruceroboats = get_boats(cruceroyear) if cruceroyear else []
        currentcboat = st.session_state.get("cruceroboat")
        if currentcboat not in cruceroboats:
            currentcboat = None
        cruceroboat = st.selectbox(
            "BARCO / SHIP",
            options=cruceroboats,
            index=cruceroboats.index(currentcboat) if currentcboat in cruceroboats else None,
            placeholder="Selecciona un barco / Select a ship",
            key="cruceroboatwidget",
            on_change=on_crucero_boat_change,
            disabled=not cruceroyear,
        )
        if cruceroboat != st.session_state.get("cruceroboat"):
            st.session_state["cruceroboat"] = cruceroboat

        fechasalida = st.date_input("FECHA DE SALIDA / DEPARTURE DATE", value=date.today(), format="DD/MM/YYYY")
        if cruceroboat and fechasalida:
            previewname = f"{cruceroboat}{fechasalida.strftime('%y%m%d')}"
            st.caption(f"Nombre previsto / Expected name: {previewname}")

        if st.button("Crear Crucero", key="btncrearcruceroaction", disabled=not (cruceroyear and cruceroboat and fechasalida)):
            if int(cruceroyear) != fechasalida.year:
                st.error("El año seleccionado no coincide con el año de la fecha / Selected year does not match the date year.")
            else:
                result = create_crucero_file(cruceroboat, fechasalida)
                if result["status"] == "duplicate":
                    st.warning(f"Ya existe / Already exists: {result['name']}")
                    st.markdown(
                        f'<a class="done-link" href="{result["url"]}" target="_blank">Abrir archivo existente · Open existing file</a>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.success(f"Archivo creado / File created: {result['name']}")
                    st.markdown(
                        f'<a class="done-link" href="{result["url"]}" target="_blank">Abrir crucero · Open cruise</a>',
                        unsafe_allow_html=True,
                    )
    except Exception as e:
        st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)

def render_panel_nueva_agencia():
    if not st.session_state.get("opennuevaagenciaform"):
        return
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Nueva Agencia · New Agency")
    with st.form("formnuevaagencia", clear_on_submit=False):
        rowa1, rowa2 = st.columns(2, gap="medium")
        with rowa1:
            agnombre = st.text_input("Nombre", key="agnombre")
        with rowa2:
            agcodigo = st.text_input("CODIGO", key="agcodigo")

        rowb1, rowb2 = st.columns(2, gap="medium")
        with rowb1:
            aggrupogest = st.text_input("Grupo Gest", key="aggrupogest")
        with rowb2:
            agtelefono = st.text_input("Telefono", key="agtelefono")

        rowc1, rowc2 = st.columns(2, gap="medium")
        with rowc1:
            agemail = st.text_input("Email", key="agemail")
        with rowc2:
            agdireccion = st.text_input("Direccion", key="agdireccion")

        st.markdown("#### Comisiones e IVA")
        rowd1, rowd2, rowd3 = st.columns(3, gap="medium")
        with rowd1:
            agcomision = st.number_input("COMISION AGENCIA %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="agcomision")
        with rowd2:
            agcomisionoferta = st.number_input("COMISION AGENCIA CON OFERTA %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="agcomisionoferta")
        with rowd3:
            agcomision2x1 = st.number_input("COMISION AGENCIA OFERTA 2X1 %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="agcomision2x1")

        rowe1, rowe2 = st.columns(2, gap="medium")
        with rowe1:
            agiva = st.number_input("IVA %", min_value=0.0, max_value=100.0, value=21.0, step=0.5, format="%.2f", key="agiva")
        with rowe2:
            agivaservicioopcional = st.number_input("IVA SERVICIO OPCIONAL %", min_value=0.0, max_value=100.0, value=21.0, step=0.5, format="%.2f", key="agivaservicioopcional")

        guardaragencia = st.form_submit_button("Guardar Agencia")
        if guardaragencia:
            if not agnombre.strip():
                st.error("El campo Nombre es obligatorio.")
            elif not agcodigo.strip():
                st.error("El campo CODIGO es obligatorio.")
            else:
                agencydata = {
                    "Nombre": agnombre.strip(),
                    "CODIGO": agcodigo.strip(),
                    "Grupo Gest": aggrupogest.strip(),
                    "Telefono": agtelefono.strip(),
                    "Email": agemail.strip(),
                    "Direccion": agdireccion.strip(),
                    "COMISION AGENCIA": percent_to_sheet_decimal(agcomision),
                    "COMISION AGENCIA CON OFERTA ": percent_to_sheet_decimal(agcomisionoferta),
                    "COMISION AGENCIA OFERTA 2X1 ": percent_to_sheet_decimal(agcomision2x1),
                    "IVA": percent_to_sheet_decimal(agiva),
                    "IVA SERVICIO OPCIONAL": percent_to_sheet_decimal(agivaservicioopcional),
                }
                try:
                    append_agency_row(agencydata)
                    st.success(f"Agencia guardada correctamente: {agencydata['Nombre']}")
                except Exception as e:
                    st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)

def render_panel_buscar_agencia():
    if not st.session_state.get("openbuscaragenciaform"):
        return
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Buscar Agencia · Find Agency")
    searchquery = st.text_input(
        "Introduce lo que sepas (nombre, código, grupo, teléfono, email o dirección)",
        key="agencysearchquery",
        placeholder="Ej: Viajes Pepe / AG123 / 912345678 / info@...",
    )
    if st.button("Buscar coincidencias", key="btnejecutarbusquedaagencia"):
        try:
            matches = search_agencies(searchquery)
            st.session_state["agencymatches"] = matches
            st.session_state["agencyselectedidx"] = None
        except Exception as e:
            st.exception(e)

    matches = st.session_state.get("agencymatches", [])
    if searchquery and not matches:
        st.info("No hay coincidencias.")

    if len(matches) == 1:
        selectedagency = matches[0]
        st.markdown('<div class="agency-card"><div class="agency-grid">', unsafe_allow_html=True)
        for field in AGENCY_FIELDS:
            st.markdown(
                f"""
                <div>
                    <div class="agency-item-label">{field}</div>
                    <div class="agency-item-value">{selectedagency.get(field, "") or "-"}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

    elif len(matches) > 1:
        options = [f"{i+1}. {ag['Nombre']} · {ag['CODIGO']} · {ag['Telefono']} · {ag['Email']}" for i, ag in enumerate(matches)]
        selectedlabel = st.selectbox(
            "Elige la agencia correcta",
            options=options,
            index=None,
            placeholder="Selecciona una coincidencia",
        )
        if selectedlabel:
            selectedidx = options.index(selectedlabel)
            selectedagency = matches[selectedidx]
            st.markdown('<div class="agency-card"><div class="agency-grid">', unsafe_allow_html=True)
            for field in AGENCY_FIELDS:
                st.markdown(
                    f"""
                    <div>
                        <div class="agency-item-label">{field}</div>
                        <div class="agency-item-value">{selectedagency.get(field, "") or "-"}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_panel_cvcfit():
    if not st.session_state.get("opencvcfitform"):
        return
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### CVC Fit")
    locator = st.text_input("Localizador", key="cvcfitlocatorwidget", placeholder="Ej: ALB260101-001")

    if st.button("Generar CVC Fit", key="btncvcfitaction", disabled=not locator):
        try:
            payload = build_cvc_fit_from_locator(locator)
            doc_io = build_cvc_fit_doc(payload)
            payload["doc_bytes"] = doc_io.getvalue()
            st.session_state["cvcfit_result"] = payload
            st.success("Documento generado correctamente.")
        except Exception as e:
            st.session_state["cvcfit_result"] = None
            st.exception(e)

    result = st.session_state.get("cvcfit_result")
    if result:
        st.markdown('<div class="cvcfit-card"><div class="cvcfit-grid">', unsafe_allow_html=True)
        fields = [
            ("Localizador", result["locator"]),
            ("Barco", result["boat_name"]),
            ("Salida", result["fecha_salida_str"]),
            ("Límite pago", result["fecha_limite_pago_str"]),
            ("Nombre", result["nombre"]),
            ("Apellidos", result["apellidos"]),
            ("DNI", result["dni"]),
            ("Personas", result["personas"]),
            ("Habitaciones", result["habitaciones"]),
            ("Total", result["total"]),
            ("Pestaña", result["sheet_title"]),
            ("Archivo Drive", result["filename"]),
        ]
        for label, value in fields:
            st.markdown(
                f"""
                <div>
                    <div class="cvcfit-item-label">{label}</div>
                    <div class="cvcfit-item-value">{value if value not in [None, ''] else '-'}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

        st.markdown(
            f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank">Abrir hoja origen</a>',
            unsafe_allow_html=True,
        )

        st.download_button(
            "Descargar DOCX",
            data=result["doc_bytes"],
            file_name=result["filename"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="btncvcfitdownload",
        )
    st.markdown("</div>", unsafe_allow_html=True)
