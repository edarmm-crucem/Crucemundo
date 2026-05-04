# FILA 1 → se queda exactamente como la tienes ahora
col1, col2, col3, col4, col5, col6 = st.columns(6, gap="medium")

with col1:
    ...
with col2:
    ...
with col3:
    ...
with col4:
    ...
with col5:
    ...
with col6:
    ...

# ESPACIO ENTRE FILAS
st.markdown("<div style='height:0.9rem'></div>", unsafe_allow_html=True)

# FILA 2 → solo la tarjeta nueva
row2_col1, row2_col2, row2_col3, row2_col4, row2_col5, row2_col6 = st.columns(6, gap="medium")

with row2_col1:
    st.markdown("""
    <div class="action-box card-excursiones">
        <div class="action-top">
            <div class="action-icon">🏝️</div>
            <div class="action-text">
                <div class="action-title">Excursiones</div>
                <div class="action-title-en">Excursions</div>
                <div class="action-desc">Abrir la hoja de Excursiones</div>
                <div class="action-desc-en">Open the Excursions sheet</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    st.markdown(
        f'<a class="done-link" href="{excursiones_url}" target="_blank">Abrir Excursiones ↗</a>',
        unsafe_allow_html=True
    )

    st.markdown("</div></div>", unsafe_allow_html=True)
