"""
MacroFIT - Extractor de Informes FIT
Streamlit app que replica la lógica del Google Apps Script original
con doble pasada de verificación, filtros y exportación Excel.
"""

import streamlit as st
import pandas as pd
import json
import re
import io
import time
from datetime import datetime
from pathlib import Path

# ── Google API ──────────────────────────────────────────────────────────────
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread

# ── Constantes ──────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

HEADERS = [
    "Barco", "Agencia", "Cod", "Grupo", "Confirmación",
    "Booking", "Itinerario", "Salida", "Regreso",
    "Neto", "Bruto", "Estado Reserva", "Pago", "Comercial", "Personas", "Idioma"
]

PATRON_ARCHIVO = re.compile(r"^[A-Z0-9_]+-\d{6}$", re.IGNORECASE)

# ── Utilidades de autenticación ──────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def crear_servicios(creds_json: dict):
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds)
    gc    = gspread.authorize(creds)
    return drive, gc


# ── Exploración de Drive ─────────────────────────────────────────────────────
def listar_carpetas(drive, parent_id):
    q = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"

    res = drive.files().list(
        q=q,
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        corpora="allDrives"
    ).execute()

    return res.get("files", [])


def listar_hojas(drive, parent_id):
    q = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"

    res = drive.files().list(
        q=q,
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        corpora="allDrives"
    ).execute()

    return res.get("files", [])


def descubrir_archivos(drive, carpeta_año_id: str) -> tuple[list[dict], list[str], list[str]]:
    """
    Navega: Año → Barcos → Salidas → Archivos (BARCO-AAMMDD).
    Devuelve (archivos, barcos_encontrados, salidas_encontradas).
    """
    archivos = []
    barcos_nombres = []
    salidas_nombres = []

    carpetas_barco = listar_carpetas(drive, carpeta_año_id)

    for barco in carpetas_barco:
        barcos_nombres.append(barco["name"])
        carpetas_salida = listar_carpetas(drive, barco["id"])

        for salida in carpetas_salida:
            salidas_nombres.append(f"{barco['name']} / {salida['name']}")
            hojas = listar_hojas(drive, salida["id"])

            for hoja in hojas:
                nombre = hoja["name"]
                archivos.append({
                    "id": hoja["id"],
                    "nombre": nombre,
                    "barco": barco["name"],
                    "salida": salida["name"],
                })

    return archivos, barcos_nombres, salidas_nombres


# ── Procesado de una hoja ────────────────────────────────────────────────────
def limpiar_numero(val) -> float:
    if not val:
        return 0.0
    s = str(val).strip()
    # Eliminar símbolos de moneda, espacios y caracteres no numéricos salvo , . -
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return 0.0
    # Formato 1.234,56 → 1234.56
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def procesar_hoja(valores: list[list], nombre_archivo: str) -> dict | None:
    """
    Recibe los display values (A1:Z60) de una hoja y extrae una fila de datos.
    Devuelve None si la hoja no es BOOKING/PROFORMA o es _GROUP.
    """
    v = valores

    def cel(fila, col, default="-"):
        try:
            val = v[fila][col]
            return val if val not in ("", None) else default
        except IndexError:
            return default

    # B2 debe contener BOOKING o PROFORMA
    b2 = str(cel(1, 1, "")).upper()
    if "BOOKING" not in b2 and "PROFORMA" not in b2:
        return None

    # Ignorar confirmaciones _GROUP
    confirmacion = str(cel(10, 6, "")).upper().strip()
    if confirmacion.endswith("_GROUP"):
        return None

    # Neto: suma de columnas Q y R en filas 33-40 (índices 32-39, cols 16-17)
    neto = 0.0
    for r in range(32, 40):
        neto += limpiar_numero(cel(r, 16, 0)) + limpiar_numero(cel(r, 17, 0))

    # Bruto: celda Y55 (índice fila 54, col 24... original col 16 = Q)
    bruto = limpiar_numero(cel(54, 16, 0))

    # Personas: V22 + Z22 + ... (fila 21, cols 6,10,13,15)
    personas = (
        limpiar_numero(cel(21, 6, 0)) +
        limpiar_numero(cel(21, 10, 0)) +
        limpiar_numero(cel(21, 13, 0)) +
        limpiar_numero(cel(21, 15, 0))
    )

    return {
        "Barco":         cel(12, 6),
        "Agencia":       cel(4, 6),
        "Cod":           cel(4, 15),
        "Grupo":         cel(4, 17),
        "Confirmación":  cel(10, 6),
        "Booking":       cel(2, 2),
        "Itinerario":    cel(18, 6),
        "Salida":        cel(16, 6),
        "Regreso":       cel(16, 10),
        "Neto":          round(neto, 2),
        "Bruto":         round(bruto, 2),
        "Estado Reserva":cel(9, 6),
        "Pago":          cel(56, 6),
        "Comercial":     cel(9, 16),
        "Personas":      int(personas),
        "Idioma":        cel(22, 6),
        "_archivo":      nombre_archivo,   # interno para verificación
    }


# ── Procesado principal con doble pasada ──────────────────────────────────────
def ejecutar_extraccion(drive, gc, archivos: list[dict], placeholder_progress, placeholder_estado):
    """
    Primera pasada: procesa todos los archivos.
    Segunda pasada: re-verifica los que dieron 0 registros o error.
    """
    resultados = []
    errores = []
    archivos_vacios = []

    total = len(archivos)

    # ── PASADA 1 ────────────────────────────────────────────────────────────
    placeholder_estado.markdown("### 🔄 Pasada 1 — Extracción inicial")
    pb1 = placeholder_progress.progress(0, text="Iniciando pasada 1…")

    for i, arch in enumerate(archivos):
        pct = int((i + 1) / total * 100)
        pb1.progress(pct, text=f"[{i+1}/{total}] {arch['barco']} · {arch['salida']} · {arch['nombre']}")

        filas_este = []
        try:
            sh = gc.open_by_key(arch["id"])
            for ws in sh.worksheets():
                vals = ws.get_all_values()
                # Extender a 60 filas × 26 cols para evitar IndexError
                padded = [row + [""] * (26 - len(row)) for row in vals]
                while len(padded) < 60:
                    padded.append([""] * 26)

                fila = procesar_hoja(padded, arch["nombre"])
                if fila:
                    fila["_barco_carpeta"]  = arch["barco"]
                    fila["_salida_carpeta"] = arch["salida"]
                    filas_este.append(fila)

        except Exception as e:
            errores.append({"archivo": arch["nombre"], "id": arch["id"], "error": str(e), "pasada": 1})

        if filas_este:
            resultados.extend(filas_este)
        else:
            archivos_vacios.append(arch)

    # ── PASADA 2 (re-verificación) ──────────────────────────────────────────
    reintento_ids = {a["id"] for a in archivos_vacios}
    reintento_ids |= {e["id"] for e in errores}

    reintento_lista = [a for a in archivos if a["id"] in reintento_ids]

    if reintento_lista:
        placeholder_estado.markdown(
            f"### 🔍 Pasada 2 — Re-verificando {len(reintento_lista)} archivos sin datos / con error"
        )
        pb2 = placeholder_progress.progress(0, text="Iniciando pasada 2…")
        errores_p1_ids = {e["id"] for e in errores}
        errores_p2 = []

        for j, arch in enumerate(reintento_lista):
            pct = int((j + 1) / len(reintento_lista) * 100)
            pb2.progress(pct, text=f"[{j+1}/{len(reintento_lista)}] Reintentando: {arch['nombre']}")
            time.sleep(0.3)  # pequeño throttle para evitar rate-limit

            filas_este = []
            try:
                sh = gc.open_by_key(arch["id"])
                for ws in sh.worksheets():
                    vals = ws.get_all_values()
                    padded = [row + [""] * (26 - len(row)) for row in vals]
                    while len(padded) < 60:
                        padded.append([""] * 26)

                    fila = procesar_hoja(padded, arch["nombre"])
                    if fila:
                        fila["_barco_carpeta"]  = arch["barco"]
                        fila["_salida_carpeta"] = arch["salida"]
                        filas_este.append(fila)

            except Exception as e:
                errores_p2.append({"archivo": arch["nombre"], "id": arch["id"], "error": str(e), "pasada": 2})

            if filas_este:
                # Solo añadir si no estaba ya en resultados
                conf_existentes = {r["Confirmación"] for r in resultados}
                nuevos = [f for f in filas_este if f["Confirmación"] not in conf_existentes]
                resultados.extend(nuevos)

                # Limpiar de errores si ahora funcionó
                errores = [e for e in errores if e["id"] != arch["id"]]

        errores.extend(errores_p2)

    placeholder_progress.empty()
    placeholder_estado.empty()
    return resultados, errores


# ── Exportar a Excel ─────────────────────────────────────────────────────────
def exportar_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export = df.drop(columns=[c for c in df.columns if c.startswith("_")], errors="ignore")
        df_export.to_excel(writer, index=False, sheet_name="VentasFIT")

        wb  = writer.book
        ws  = writer.sheets["VentasFIT"]

        # Formatos
        fmt_header = wb.add_format({
            "bold": True, "bg_color": "#d9e1f2", "border": 1,
            "align": "center", "valign": "vcenter", "font_name": "Calibri"
        })
        fmt_euro = wb.add_format({
            "num_format": '#,##0.00 €', "bg_color": "#fff2cc",
            "font_name": "Calibri"
        })
        fmt_normal = wb.add_format({"font_name": "Calibri"})

        for col_num, col_name in enumerate(df_export.columns):
            ws.write(0, col_num, col_name, fmt_header)
            if col_name in ("Neto", "Bruto"):
                ws.set_column(col_num, col_num, 14, fmt_euro)
            else:
                ws.set_column(col_num, col_num, 16, fmt_normal)

        # Autofilter
        ws.autofilter(0, 0, len(df_export), len(df_export.columns) - 1)

    return output.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# ── APP PRINCIPAL ──────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="MacroFIT Extractor",
        page_icon="🚢",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── CSS personalizado ──────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2563ab 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { margin: 0; font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; }
    .main-header p  { margin: 0.4rem 0 0; opacity: 0.8; font-size: 0.95rem; }

    .metric-card {
        background: #f8faff;
        border: 1px solid #dce6f7;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-card .val { font-size: 2rem; font-weight: 700; color: #1a3a5c; }
    .metric-card .lbl { font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }

    .stDataFrame { border: 1px solid #dce6f7; border-radius: 8px; }

    .badge-ok  { background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:99px; font-size:0.8rem; }
    .badge-err { background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:99px; font-size:0.8rem; }

    div[data-testid="stSidebar"] { background: #f1f5fb; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="main-header">
        <h1>🚢 MacroFIT Extractor</h1>
        <p>Extracción automática de informes FIT · Doble pasada de verificación</p>
    </div>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # ── SIDEBAR — Configuración ────────────────────────────────────────────
    # ════════════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown("## ⚙️ Configuración")

        st.markdown("### 📁 Carpeta raíz de Drive")
        id_raiz = st.text_input(
            "ID de la carpeta raíz FIT",
            value="11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm",
            help="ID que aparece en la URL de Drive"
        )

        st.divider()
        st.markdown("### 📅 Año a procesar")
        año_sel = st.text_input("Año", value=str(datetime.now().year))

        st.divider()
        iniciar = st.button("▶️ Iniciar Extracción", use_container_width=True, type="primary")

        st.markdown("---")
        st.caption("MacroFIT v2.0 · Doble pasada · Exportación Excel")

    # ════════════════════════════════════════════════════════════════════════
    # ── ESTADO DE SESIÓN ───────────────────────────────────────────────────
    # ════════════════════════════════════════════════════════════════════════
    if "df_resultados" not in st.session_state:
        st.session_state.df_resultados = None
    if "errores"       not in st.session_state:
        st.session_state.errores = []
    if "meta"          not in st.session_state:
        st.session_state.meta = {}

    # ════════════════════════════════════════════════════════════════════════
    # ── INICIO DE EXTRACCIÓN ───────────────────────────────────────────────
    # ════════════════════════════════════════════════════════════════════════
    if iniciar:
        if not id_raiz.strip():
            st.error("⚠️  Introduce el ID de la carpeta raíz.")
            return
        if not año_sel.strip().isdigit():
            st.error("⚠️  El año debe ser numérico.")
            return

        # Cargar credenciales desde st.secrets (configuradas en Streamlit Cloud)
        try:
            creds_dict = dict(st.secrets["gcpserviceaccount"])
        except KeyError:
            st.error("⚠️  No se encontraron credenciales en Secrets. Ve a **Manage app → Secrets** y añade la sección `[gcpserviceaccount]`.")
            return

        with st.spinner("Conectando con Google Drive…"):
            try:
                drive, gc = crear_servicios(creds_dict)
            except Exception as e:
                st.error(f"Error de autenticación: {e}")
                return

        # Buscar carpeta del año
        with st.spinner(f"Buscando carpeta del año {año_sel}…"):
            # Listar TODO lo que hay en la raíz para debug
            q_debug = f"'{id_raiz}' in parents and trashed=false"
            res_debug = drive.files().list(q=q_debug, fields="files(id,name,mimeType)").execute()
            st.write("📂 Contenido de la carpeta raíz:", res_debug.get("files", []))
            
            q = f"'{id_raiz}' in parents and name='{año_sel}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            res = drive.files().list(q=q, fields="files(id,name)").execute()
            carpetas_año = res.get("files", [])

        if not carpetas_año:
            st.error(f"No se encontró la carpeta del año **{año_sel}** en la raíz indicada.")
            return

        carpeta_año_id = carpetas_año[0]["id"]

        # Descubrir estructura
        with st.spinner("Explorando estructura de carpetas…"):
            archivos, barcos, salidas = descubrir_archivos(drive, carpeta_año_id)

        if not archivos:
            st.warning("No se encontraron archivos Sheets en la estructura de carpetas.")
            return

        st.info(
            f"📂 **{len(barcos)} barcos** · **{len(salidas)} salidas** · "
            f"**{len(archivos)} archivos** encontrados. Iniciando extracción…"
        )

        # Contenedores para progreso en tiempo real
        placeholder_prog   = st.empty()
        placeholder_estado = st.empty()

        t_inicio = time.time()
        resultados, errores = ejecutar_extraccion(
            drive, gc, archivos, placeholder_prog, placeholder_estado
        )
        t_fin = time.time()

        # Guardar en sesión
        if resultados:
            df = pd.DataFrame(resultados)
            # Marcar duplicados por Confirmación
            df["_duplicado"] = df["Confirmación"].duplicated(keep=False)
            st.session_state.df_resultados = df
        else:
            st.session_state.df_resultados = pd.DataFrame()

        st.session_state.errores = errores
        st.session_state.meta = {
            "año": año_sel,
            "archivos_total": len(archivos),
            "tiempo": round(t_fin - t_inicio, 1),
            "ts": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # ── MOSTRAR RESULTADOS ─────────────────────────────────────────────────
    # ════════════════════════════════════════════════════════════════════════
    df_all = st.session_state.df_resultados

    if df_all is None:
        st.markdown("""
        <div style="text-align:center;padding:4rem 0;color:#94a3b8;">
            <div style="font-size:4rem">🚢</div>
            <div style="font-size:1.2rem;font-weight:600;margin-top:1rem;">Listo para procesar</div>
            <div style="margin-top:0.5rem;font-size:0.9rem;">
                Configura las credenciales y el año en el panel lateral, luego pulsa Iniciar.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    meta = st.session_state.meta
    errores = st.session_state.errores

    # ── Métricas resumen ───────────────────────────────────────────────────
    n_filas = len(df_all)
    n_dup   = int(df_all["_duplicado"].sum()) if "_duplicado" in df_all.columns else 0
    neto_t  = df_all["Neto"].sum()  if "Neto"  in df_all.columns else 0
    bruto_t = df_all["Bruto"].sum() if "Bruto" in df_all.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="val">{n_filas}</div>
            <div class="lbl">Localizadores</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="val">{meta.get('archivos_total','–')}</div>
            <div class="lbl">Archivos procesados</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="val" style="color:#b45309">{n_dup}</div>
            <div class="lbl">Confirmaciones duplicadas</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="val" style="color:#15803d">{neto_t:,.0f} €</div>
            <div class="lbl">Neto total</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="val" style="color:#1d4ed8">{bruto_t:,.0f} €</div>
            <div class="lbl">Bruto total</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"<div style='margin:.5rem 0;font-size:.8rem;color:#94a3b8;'>Generado: {meta.get('ts','–')} · {meta.get('tiempo','–')}s · Año {meta.get('año','–')}</div>", unsafe_allow_html=True)

    # ── Alertas duplicados / errores ──────────────────────────────────────
    if n_dup > 0:
        st.warning(f"⚠️  Se detectaron **{n_dup} filas** con Confirmación duplicada (marcadas en la tabla).")
    if errores:
        with st.expander(f"❌ {len(errores)} error(es) durante el proceso", expanded=False):
            df_err = pd.DataFrame(errores)
            st.dataframe(df_err, use_container_width=True, height=200)

    # ── FILTROS ───────────────────────────────────────────────────────────
    st.markdown("### 🔍 Filtros")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    df_vis = df_all.copy()

    with col_f1:
        barcos_u = sorted(df_vis["Barco"].dropna().unique().tolist())
        sel_barco = st.multiselect("Barco", barcos_u, key="f_barco")

    with col_f2:
        agencias_u = sorted(df_vis["Agencia"].dropna().unique().tolist())
        sel_agencia = st.multiselect("Agencia", agencias_u, key="f_agencia")

    with col_f3:
        estados_u = sorted(df_vis["Estado Reserva"].dropna().unique().tolist())
        sel_estado = st.multiselect("Estado Reserva", estados_u, key="f_estado")

    with col_f4:
        solo_dup = st.checkbox("Solo duplicados", key="f_dup")
        solo_err_neto = st.checkbox("Neto = 0", key="f_neto0")

    # Filtro texto libre
    texto_libre = st.text_input("🔎 Buscar en toda la tabla (Confirmación, Agencia, Comercial…)", key="f_txt")

    # Aplicar filtros
    if sel_barco:
        df_vis = df_vis[df_vis["Barco"].isin(sel_barco)]
    if sel_agencia:
        df_vis = df_vis[df_vis["Agencia"].isin(sel_agencia)]
    if sel_estado:
        df_vis = df_vis[df_vis["Estado Reserva"].isin(sel_estado)]
    if solo_dup and "_duplicado" in df_vis.columns:
        df_vis = df_vis[df_vis["_duplicado"] == True]
    if solo_err_neto:
        df_vis = df_vis[df_vis["Neto"] == 0]
    if texto_libre:
        mask = df_vis.apply(
            lambda row: row.astype(str).str.contains(texto_libre, case=False, na=False).any(),
            axis=1
        )
        df_vis = df_vis[mask]

    # ── Tabla principal ───────────────────────────────────────────────────
    st.markdown(f"### 📋 Resultados ({len(df_vis)} filas)")

    cols_mostrar = [c for c in HEADERS if c in df_vis.columns]
    if "_duplicado" in df_vis.columns:
        cols_mostrar_ext = cols_mostrar + ["_duplicado"]
    else:
        cols_mostrar_ext = cols_mostrar

    df_display = df_vis[cols_mostrar_ext].copy()

    # Resaltar duplicados
    def highlight_dup(row):
        if row.get("_duplicado", False):
            return ["background-color: #fee2e2; color: #991b1b"] * len(row)
        return [""] * len(row)

    # Formateo de columnas numéricas
    fmt = {
        "Neto":  "{:,.2f} €",
        "Bruto": "{:,.2f} €",
    }
    if "Personas" in df_display.columns:
        fmt["Personas"] = "{:,.0f}"

    styled = df_display.style.apply(highlight_dup, axis=1).format(fmt, na_rep="-")

    st.dataframe(
        styled,
        use_container_width=True,
        height=520,
        column_config={
            "_duplicado": st.column_config.CheckboxColumn("Dup.", width="small"),
            "Neto":       st.column_config.NumberColumn("Neto", format="%.2f €"),
            "Bruto":      st.column_config.NumberColumn("Bruto", format="%.2f €"),
        }
    )

    # ── Exportación ───────────────────────────────────────────────────────
    st.markdown("### 💾 Exportar")
    c_ex1, c_ex2 = st.columns(2)

    with c_ex1:
        xlsx_bytes = exportar_excel(df_vis)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            label="⬇️  Descargar Excel (filtrado)",
            data=xlsx_bytes,
            file_name=f"VentasFIT_{meta.get('año','X')}_{ts_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with c_ex2:
        xlsx_all = exportar_excel(df_all)
        st.download_button(
            label="⬇️  Descargar Excel (todo)",
            data=xlsx_all,
            file_name=f"VentasFIT_{meta.get('año','X')}_COMPLETO_{ts_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # ── Pestaña de detalle por barco ──────────────────────────────────────
    if "Barco" in df_vis.columns and len(df_vis) > 0:
        with st.expander("📊 Resumen por Barco", expanded=False):
            resumen = df_vis.groupby("Barco").agg(
                Localizadores=("Confirmación", "count"),
                Neto_Total=("Neto", "sum"),
                Bruto_Total=("Bruto", "sum"),
                Personas_Total=("Personas", "sum"),
            ).sort_values("Neto_Total", ascending=False)

            resumen["Neto_Total"]  = resumen["Neto_Total"].map("{:,.2f} €".format)
            resumen["Bruto_Total"] = resumen["Bruto_Total"].map("{:,.2f} €".format)
            st.dataframe(resumen, use_container_width=True)

    if "Agencia" in df_vis.columns and len(df_vis) > 0:
        with st.expander("📊 Resumen por Agencia (Top 20)", expanded=False):
            resumen_ag = df_vis.groupby("Agencia").agg(
                Localizadores=("Confirmación", "count"),
                Neto_Total=("Neto", "sum"),
            ).sort_values("Neto_Total", ascending=False).head(20)

            resumen_ag["Neto_Total"] = resumen_ag["Neto_Total"].map("{:,.2f} €".format)
            st.dataframe(resumen_ag, use_container_width=True)


if __name__ == "__main__":
    main()
