# ************************************************************
# *************** 18. PANEL CVC FIT **************************
# ************************************************************
if st.session_state.get("opencvcfitform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### CVC Fit")

    locator = st.text_input(
        "Localizador",
        key="cvcfitlocatorwidget",
        placeholder="Introduce el localizador exacto de BOOKING ES!G11",
    )

    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    def progress_callback(i, total, spreadsheet_name):
        status_placeholder.info(f"Revisando {i}/{total}: {spreadsheet_name}")
        progress_placeholder.progress(i / total)

    if st.button("Generar PDF CVC Fit", key="btncvcfitaction", disabled=not locator.strip()):
        st.session_state["cvcfit_result"] = None
        try:
            with st.spinner("Buscando localizador y generando PDF..."):
                result = build_cvc_fit_pdf_from_locator(locator, progress_callback=progress_callback)
            st.session_state["cvcfit_result"] = result
            status_placeholder.success(
                f"Encontrado en {result['spreadsheet_name']} "
                f"({result['checked_files']}/{result['total_files']})"
            )
        except Exception as e:
            progress_placeholder.empty()
            status_placeholder.error(str(e))
            st.session_state["cvcfit_result"] = None

    result = st.session_state.get("cvcfit_result")
    if result:
        st.markdown('<div class="cvcfit-card"><div class="cvcfit-grid">', unsafe_allow_html=True)
        fields = [
            ("Localizador", result["locator"]),
            ("Nombre", result["nombre"]),
            ("Spreadsheet", result["spreadsheet_name"]),
            ("Archivo PDF", result["filename"]),
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
            "Descargar PDF",
            data=result["pdf_bytes"],
            file_name=result["filename"],
            mime="application/pdf",
            key="btncvcfitdownload",
        )

    st.markdown("</div>", unsafe_allow_html=True)
