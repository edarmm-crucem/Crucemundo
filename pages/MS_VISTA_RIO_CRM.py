import streamlit as st
import pytz
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from collections import defaultdict

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="MS VISTA RIO",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# AUTH
# ============================================================
if not st.session_state.get("authenticated"):
    st.warning("No tienes acceso. Vuelve al inicio.")
    st.stop()

# ============================================================
# CONSTANTES
# ============================================================
BARCO = "MS_VISTA_RIO"
MASTERCABINASID = "1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI"
CRMBARCO = "1ApNv3qK-_2ANOVwSZoOchAdwWaeQg0Evz-n54s6T2cE"
LOGOID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL = f"https://lh3.googleusercontent.com/d/{LOGOID}"

NOMBRE_BARCO_LIMPIO = BARCO.replace("_CRM", "").replace("_", " ")

# ============================================================
# UTILIDADES
# ============================================================
TIMEZONE = pytz.timezone("Europe/Madrid")
def now():
    return datetime.now(pytz.utc).astimezone(TIMEZONE).replace(tzinfo=None)
def getsaludo(lang="es"):
    hour = now().hour
    if lang == "en":
        if 6 <= hour < 14: return "Good morning"
        if 14 <= hour < 21: return "Good afternoon"
        return "Good evening"
    if 6 <= hour < 14: return "Buenos días"
    if 14 <= hour < 21: return "Buenas tardes"
    return "Buenas noches"

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = getsaludo("es")
SALUDOEN = getsaludo("en")

# ============================================================
# GOOGLE SHEETS SERVICE
# ============================================================
@st.cache_resource
def getgooglecreds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )

def getsheetsservice():
    return build("sheets", "v4", credentials=getgooglecreds())

# ============================================================
# FUNCIONES SHEETS
# ============================================================
@st.cache_data(ttl=60)
def getcabinas():
    service = getsheetsservice()
    result = service.spreadsheets().values().get(
        spreadsheetId=MASTERCABINASID,
        range="Hoja 1!A:D"
    ).execute()
    rows = result.get("values", [])
    return [r for r in rows if len(r) >= 4 and r[0] == BARCO]

@st.cache_data(ttl=60)
def getagencias():
    service = getsheetsservice()
    result = service.spreadsheets().values().get(
        spreadsheetId=MASTERCABINASID,
        range="AGENCIAS!A:B"
    ).execute()
    rows = result.get("values", [])
    agencias = {}
    for r in rows:
        if len(r) >= 2:
            agencias[r[0].strip()] = r[1].strip()
    return agencias

@st.cache_data(ttl=30)
def getsalidas():
    service = getsheetsservice()
    spreadsheet = service.spreadsheets().get(spreadsheetId=CRMBARCO).execute()
    return [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]

def crearsalida(ddmm, cabinas):
    service = getsheetsservice()
    service.spreadsheets().batchUpdate(
        spreadsheetId=CRMBARCO,
        body={"requests": [{"addSheet": {"properties": {"title": ddmm}}}]}
    ).execute()
    
    header = [["cabina", "categoria", "estado", "agencia", "pax", "localizador", "notes", "cupo_agencia", "cupo_maximo"]]
    rows = []
    for c in cabinas:
        rows.append([c[1], c[3], "LIBRE", "", "", "", "", "", ""])
        
    service.spreadsheets().values().update(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!A1",
        valueInputOption="RAW",
        body={"values": header + rows}
    ).execute()

@st.cache_data(ttl=5)
def getdatossalida(ddmm):
    service = getsheetsservice()
    result = service.spreadsheets().values().get(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!A:I"
    ).execute()
    rows = result.get("values", [])
    if len(rows) < 2:
        return []
    header = rows[0]
    return [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in rows[1:]]

def guardarcabina(ddmm, rowindex, agencia, pax, localizador, notas):
    service = getsheetsservice()
    fila = rowindex + 2
    service.spreadsheets().values().update(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!C{fila}:G{fila}",
        valueInputOption="RAW",
        body={"values": [["VENDIDA" if agencia else "LIBRE", agencia, pax, localizador, notas]]}
    ).execute()

def guardar_cupo_sheets(ddmm, datos_completos, agencia, nuevo_limite):
    service = getsheetsservice()
    fila_destino = None
    for i, d in enumerate(datos_completos):
        if d.get("cupo_agencia", "").strip() == agencia:
            fila_destino = i + 2
            break
            
    if fila_destino is None:
        for i, d in enumerate(datos_completos):
            if not d.get("cupo_agencia", "").strip():
                fila_destino = i + 2
                break
        if fila_destino is None:
            fila_destino = len(datos_completos) + 2

    service.spreadsheets().values().update(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!H{fila_destino}:I{fila_destino}",
        valueInputOption="RAW",
        body={"values": [[agencia, str(nuevo_limite)]]}
    ).execute()

# ============================================================
# CSS
# ============================================================
st.markdown(
    '''
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .portal-header { padding: 0.1rem 0 0.55rem 0; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.55rem; }
        .portal-header-left { display: flex; align-items: center; gap: 1.2rem; }
        .portal-logo { height: 50px; width: auto; object-fit: contain; display: block; }
        .portal-title, .portal-title-en { font-size: 0.96rem; font-weight: 500; color: #4B5563; line-height: 1.2; }
        .portal-title strong, .portal-title-en strong { color: #111827; }
        .portal-title-en { margin-top: 0.12rem; font-style: italic; color: #6B7280; }
        
        .ship-badge-container { display: flex; flex-direction: column; align-items: flex-end; text-align: right; }
        .ship-title { font-size: 1.5rem; font-weight: 900; color: #1E3A8A; letter-spacing: 0.05em; line-height: 1; }
        .ship-subtitle { font-size: 0.75rem; font-weight: 600; color: #4B5563; text-transform: uppercase; margin-top: 0.2rem; letter-spacing: 0.1em; }
        
        section[data-testid="stMain"] > div:first-child { padding-top: 1rem !important; }
        
        /* Estructura de Cubierta de Barco Real (Filas paralelas) */
        .deck-layout { background: #FFFFFF; padding: 1.2rem; border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 1.5rem; }
        .deck-row { display: flex; flex-wrap: nowrap; gap: 0.5rem; overflow-x: auto; padding: 0.2rem 0; }
        .deck-row-style { justify-content: flex-start; } 
        
        /* Pasillo horizontal central */
        .horizontal-corridor { height: 18px; margin: 0.4rem 0; background-image: linear-gradient(to right, #E5E7EB 50%, rgba(255,255,255,0) 0%); background-position: bottom; background-size: 15px 2px; background-repeat: repeat-x; display: flex; align-items: center; padding-left: 0.5rem; font-size: 0.6rem; font-weight: 700; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.15em; }
        
        .cabina-box {
            min-width: 72px; max-width: 72px; height: 54px; border-radius: 6px; border: 2px solid transparent;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            font-size: 0.78rem; font-weight: 700; cursor: pointer; transition: all 0.15s;
            box-sizing: border-box;
        }
        .cabina-libre { background: #F3F4F6; border-color: #D1D5DB; color: #6B7280; }
        .cabina-vendida { border-color: #1F2937 !important; border-width: 3px !important; }
        .categoria-label { font-size: 0.95rem; font-weight: 800; color: #1E3A8A; margin: 1rem 0 0.6rem 0; background: #EFF6FF; padding: 0.4rem 0.8rem; border-radius: 6px; display: inline-block; border-left: 4px solid #3B82F6; }
    </style>
    ''',
    unsafe_allow_html=True,
)

# ============================================================
# CABECERA OPTIMIZADA CON BARCO DESTACADO
# ============================================================
st.markdown(
    f'''
    <div class="portal-header">
        <div class="portal-header-left">
            <img class="portal-logo" src="{LOGOURL}" alt="Logo">
            <div>
                <div class="portal-title">{SALUDO}, <strong>{DISPLAYUSER}</strong>. ¿Qué hacemos hoy?</div>
                <div class="portal-title-en">{SALUDOEN}, <strong>{DISPLAYUSER}</strong>. What are we doing today?</div>
            </div>
        </div>
        <div class="ship-badge-container">
            <div class="ship-title">🚢 {NOMBRE_BARCO_LIMPIO}</div>
            <div class="ship-subtitle">Panel de Control / Control Panel</div>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)

st.markdown("---")

# ============================================================
# CARGA DE DATOS BASE
# ============================================================
cabinas = getcabinas()
agencias = getagencias()
salidas = getsalidas()

if not cabinas:
    st.error(f"No se encontraron cabinas para {BARCO} en el master.")
    st.stop()

# ============================================================
# SELECTOR DE MODO INICIAL
# ============================================================
opciones_modo = ["Mapa de cabinas", "Ver Cupos", "Configurar Cupos", "Nueva salida", "Inicio"]

modo = st.radio(
    "¿Qué quieres hacer?", 
    opciones_modo, 
    index=4, 
    horizontal=True
)

# ------------------------------------------------------------
# MODO: INICIO
# ------------------------------------------------------------
if modo == "Inicio":
    st.markdown(f"### 👋 Bienvenido al Panel del {NOMBRE_BARCO_LIMPIO}")
    st.markdown(
        f"""
        Has iniciado sesión correctamente como **{DISPLAYUSER}**. 
        
        Desde este panel centralizado puedes gestionar de forma ágil la ocupación del buque. Utiliza el menú superior para navegar entre las herramientas disponibles:
        
        *   **🚢 Mapa de cabinas:** Visualiza los planos de las cubiertas orientados de forma realista (Conteo e inicio desde el extremo derecho avanzando hacia la izquierda).
        *   **📊 Ver Cupos:** Consulta de manera analítica el estado de los cupos de las agencias comerciales para cualquier salida seleccionada.
        *   **⚙️ Configurar Cupos:** Añade agencias y modifica sus límites de cupos asignados de forma directa sin salir de la plataforma.
        *   **📅 Nueva salida:** Genera la estructura inicial para una nueva fecha operativa del barco en la base de datos.
        """
    )
    st.markdown("---")
    st.page_link("app.py", label=" Volver al Menú Principal (Selección de Barcos)", icon="🏠")

# ------------------------------------------------------------
# MODO: NUEVA SALIDA
# ------------------------------------------------------------
elif modo == "Nueva salida":
    st.markdown("#### Crear una nueva salida")
    ddmm = st.text_input("Fecha de salida (DDMM)", max_chars=4, placeholder="2705")
    if ddmm and len(ddmm) == 4:
        if ddmm in salidas:
            st.warning(f"La salida {ddmm} ya existe.")
        else:
            if st.button("✅ Crear salida"):
                with st.spinner("Creando salida..."):
                    crearsalida(ddmm, cabinas)
                    st.cache_data.clear()
                    st.success(f"Salida {ddmm} creada correctamente.")
                    st.rerun()

# ------------------------------------------------------------
# MODOS INTERACTIVOS (SALIDAS EXISTENTES)
# ------------------------------------------------------------
else:
    if not salidas:
        st.info("No hay salidas creadas todavía.")
        st.stop()

    ddmm_sel = st.selectbox("Selecciona salida para operar", salidas)

    if ddmm_sel:
        datos = getdatossalida(ddmm_sel)
        
        if not datos:
            st.warning("La salida seleccionada no contiene datos.")
            st.stop()

        ventas_por_agencia = defaultdict(int)
        cupos_salida = {}
        
        for d in datos:
            ag_en_fila = d.get("agencia", "").strip()
            if ag_en_fila:
                ventas_por_agencia[ag_en_fila] += 1
            
            c_ag = d.get("cupo_agencia", "").strip()
            c_max = d.get("cupo_maximo", "").strip()
            if c_ag and c_max:
                try:
                    cupos_salida[c_ag] = int(c_max)
                except ValueError:
                    pass

        # ------------------------------------------------------------
        # OPCIÓN: VER CUPOS
        # ------------------------------------------------------------
        if modo == "Ver Cupos":
            st.markdown(f"### 📊 Estado de Cupos — Salida {ddmm_sel}")
            if not cupos_salida:
                st.info("No hay cupos configurados para esta salida todavía. Ve a la sección 'Configurar Cupos' para asignarlos.")
            else:
                tabla_cupos = []
                for ag in agencias.keys():
                    limite = cupos_salida.get(ag, 0)
                    vendidas = ventas_por_agencia[ag]
                    disponibles = limite - vendidas
                    
                    if limite > 0 or vendidas > 0:
                        estado = "🚨 Excedido" if disponibles < 0 else "✅ OK"
                        tabla_cupos.append({
                            "Agencia": ag,
                            "Cupo Máximo": limite,
                            "Cabinas Vendidas": vendidas,
                            "Disponibles": disponibles,
                            "Estado": estado
                        })
                
                if tabla_cupos:
                    st.table(tabla_cupos)
                else:
                    st.warning("No hay datos de cupos disponibles de agencias activas.")

        # ------------------------------------------------------------
        # OPCIÓN: CONFIGURAR CUPOS
        # ------------------------------------------------------------
        elif modo == "Configurar Cupos":
            st.markdown(f"### ⚙️ Añadir / Modificar Cupos — Salida {ddmm_sel}")
            col_a, col_b = st.columns(2)
            with col_a:
                agencia_cupo = st.selectbox("Selecciona la Agencia", list(agencias.keys()))
            with col_b:
                cupo_actual_valor = cupos_salida.get(agencia_cupo, 0)
                nuevo_limite = st.number_input(
                    f"Cupo máximo para {agencia_cupo}", 
                    min_value=0, 
                    max_value=100, 
                    value=int(cupo_actual_valor)
                )
            
            if st.button("💾 Guardar Configuración de Cupo"):
                with st.spinner("Guardando en Sheets..."):
                    guardar_cupo_sheets(ddmm_sel, datos, agencia_cupo, nuevo_limite)
                    st.cache_data.clear()
                    st.success(f"Cupo de {agencia_cupo} actualizado a {nuevo_limite} para la salida {ddmm_sel}.")
                    st.rerun()

        # ------------------------------------------------------------
        # OPCIÓN: MAPA DE CABINAS (DISTRIBUCIÓN REVERSA COMPLETA)
        # ------------------------------------------------------------
        elif modo == "Mapa de cabinas":
            estadocabina = {d.get("cabina", ""): d for d in datos}
            porcategoria = defaultdict(list)
            for c in cabinas:
                porcategoria[c[3]].append(c[1])

            if cupos_salida:
                with st.expander("📊 Vista Rápida de Alertas de Cupos", expanded=True):
                    c_cups = st.columns(min(len(cupos_salida), 5))
                    for idx, (ag, lim) in enumerate(cupos_salida.items()):
                        actuales = ventas_por_agencia[ag]
                        with c_cups[idx % len(c_cups)]:
                            if actuales > lim:
                                st.metric(label=f"🚨 {ag} (Excedido)", value=f"{actuales} / {lim}")
                            else:
                                block_label = f"💼 {ag}"
                                st.metric(label=block_label, value=f"{actuales} / {lim}")

            st.markdown(f"### 🚢 Distribución de Cubiertas — Salida {ddmm_sel}")
            st.caption("◀ Conteo desde la Derecha hacia la Izquierda en ambas filas (Fila Superior: Impares | Fila Inferior: Pares)")
            
            for categoria, nums in porcategoria.items():
                st.markdown(f'<div class="categoria-label">📍 {categoria}</div>', unsafe_allow_html=True)
                
                impares = []
                pares = []
                
                for num in nums:
                    try:
                        num_limpio = ''.join(filter(str.isdigit, num))
                        val = int(num_limpio)
                        if val % 2 != 0:
                            impares.append((val, num))
                        else:
                            pares.append((val, num))
                    except ValueError:
                        pares.append((999, num))

                # ORDENACIÓN: Ambos de mayor a menor para comenzar con el número más pequeño en la derecha
                impares_ordenados = [item[1] for item in sorted(impares, key=lambda x: x[0], reverse=True)]
                pares_ordenados = [item[1] for item in sorted(pares, key=lambda x: x[0], reverse=True)]

                # Construir HTML de la cubierta completa
                html = '<div class="deck-layout">'
                
                # --- FILA SUPERIOR: IMPARES (Menores a la Derecha) ---
                html += '<div class="deck-row deck-row-style">'
                for num in impares_ordenados:
                    info = estadocabina.get(num, {})
                    agencia = info.get("agencia", "")
                    estado = info.get("estado", "LIBRE")
                    color = agencias.get(agencia, "#F3F4F6") if agencia else "#F3F4F6"
                    border = "#1F2937" if estado == "VENDIDA" else "#D1D5DB"
                    textcolor = "#1F2937" if agencia else "#9CA3AF"
                    html += f'''
                    <div class="cabina-box" style="background:{color};border-color:{border};color:{textcolor};"
                         onclick="window.parent.postMessage({{type:'streamlit:setComponentValue', value:'{num}'}}, '*')">
                        <span>{num}</span>
                        <span style="font-size:0.55rem; font-weight:600; white-space:nowrap; overflow:hidden;">{agencia or "libre"}</span>
                    </div>'''
                html += '</div>'
                
                # --- PASILLO INTERIOR ---
                html += '<div class="horizontal-corridor">Pasillo Central de Cubierta</div>'
                
                # --- FILA INFERIOR: PARES (Menores a la Derecha) ---
                html += '<div class="deck-row deck-row-style">'
                for num in pares_ordenados:
                    info = estadocabina.get(num, {})
                    agencia = info.get("agencia", "")
                    estado = info.get("estado", "LIBRE")
                    color = agencias.get(agencia, "#F3F4F6") if agencia else "#F3F4F6"
                    border = "#1F2937" if estado == "VENDIDA" else "#D1D5DB"
                    textcolor = "#1F2937" if agencia else "#9CA3AF"
                    html += f'''
                    <div class="cabina-box" style="background:{color};border-color:{border};color:{textcolor};"
                         onclick="window.parent.postMessage({{type:'streamlit:setComponentValue', value:'{num}'}}, '*')">
                        <span>{num}</span>
                        <span style="font-size:0.55rem; font-weight:600; white-space:nowrap; overflow:hidden;">{agencia or "libre"}</span>
                    </div>'''
                html += '</div>'
                
                html += '</div>' # Cierre deck-layout
                st.markdown(html, unsafe_allow_html=True)

            # Panel de Asignación
            st.markdown("---")
            st.markdown("#### ✏️ Asignar cabina")
            col1, col2 = st.columns([1, 2])
            with col1:
                nums_disponibles = [c[1] for c in cabinas]
                cabina_input = st.selectbox("Cabina", sorted(nums_disponibles))

            if cabina_input:
                info = estadocabina.get(cabina_input, {})
                agencia_actual_cabina = info.get("agencia", "").strip()
                
                permitir_guardado = True
                if agencia_actual_cabina:
                    st.error(f"⚠️ **¡Atención!** La cabina {cabina_input} ya se encuentra asignada a la agencia **{agencia_actual_cabina}**.")
                    confirmar_sustitucion = st.checkbox(f"¿Quieres sustituir la asignación de {agencia_actual_cabina}?", value=False)
                    if not confirmar_sustitucion:
                        permitir_guardado = False

                with col2:
                    agencia_sel = st.selectbox(
                        "Agencia",
                        [""] + list(agencias.keys()),
                        index=list(agencias.keys()).index(info.get("agencia", "")) + 1
                        if info.get("agencia") in agencias else 0,
                        disabled=not permitir_guardado
                    )
                c1, c2, c3 = st.columns(3)
                with c1:
                    pax_input = st.number_input("Pax", min_value=0, max_value=10, value=int(info.get("pax", 0) or 0), disabled=not permitir_guardado)
                with c2:
                    loc_input = st.text_input("Localizador", value=info.get("localizador", ""), disabled=not permitir_guardado)
                with c3:
                    notas_input = st.text_input("Notas", value=info.get("notas", ""), disabled=not permitir_guardado)

                if agencia_sel in cupos_salida:
                    limite_agencia = cupos_salida[agencia_sel]
                    ocupadas_ya = ventas_por_agencia[agencia_sel]
                    se_mantiene = (agencia_sel == agencia_actual_cabina)
                    
                    if ocupadas_ya >= limite_agencia and not se_mantiene:
                        st.error(f"🚫 **Cupo Máximo Superado:** {agencia_sel} ya tiene {ocupadas_ya} cabinas. El límite para esta salida es de {limite_agencia}.")

                if st.button("💾 Guardar", disabled=not permitir_guardado):
                    rowindex = next((i for i, d in enumerate(datos) if d.get("cabina") == cabina_input), None)
                    if rowindex is not None:
                        with st.spinner("Guardando..."):
                            guardarcabina(ddmm_sel, rowindex, agencia_sel, pax_input, loc_input, notas_input)
                            st.cache_data.clear()
                            st.success(f"Cabina {cabina_input} actualizada correctamente.")
                            st.rerun()

# ============================================================
# PIE DE PÁGINA (BOTÓN NAVEGACIÓN GLOBAL AL RAÍZ)
# ============================================================
st.markdown("---")
st.page_link("app.py", label=" Volver al Menú Principal (Selección de Barcos)", icon="🏠")
