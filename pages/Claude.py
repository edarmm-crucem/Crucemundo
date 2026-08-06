# ============================================================
# PÁGINA: PREGUNTA A CLAUDE — lee el documento IA_BRUTO cada vez
# ============================================================ 

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI

st.set_page_config(
    page_title="Pregunta a Claude",
    page_icon="favicon1.png",
    layout="wide"
)
DOCUMENTID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"
DOCUMENTNAME = "IA_BRUTO"

if not st.session_state.get("authenticated"):
    st.warning("Debes iniciar sesión desde la página principal.")
    st.stop()


@st.cache_resource
def getgooglecreds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )


@st.cache_resource
def getdriveservice():
    return build("drive", "v3", credentials=getgooglecreds())


@st.cache_data(ttl=300)
def getdocumenttext():
    """Lee siempre la última versión del documento (cache de 5 min, ya que se actualiza cada noche)."""
    service = getdriveservice()
    data = service.files().export(fileId=DOCUMENTID, mimeType="text/plain").execute()
    return data.decode("utf-8") if isinstance(data, bytes) else data


from openai import OpenAI

def preguntaraldocumento(documenttext, pregunta, historial):
    apikey = st.secrets.get("openrouterapikey")
    if not apikey:
        raise Exception(
            "Falta 'openrouterapikey' en los Secrets de Streamlit Cloud "
            "(Manage app → Settings → Secrets)."
        )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=apikey,
    )

    systemprompt = f"""Eres un asistente que responde preguntas basándose en el contenido
del documento "{DOCUMENTNAME}", que se actualiza automáticamente cada noche con información
extraída de la página web de Crucemundo. Responde solo con lo que aparece en el documento;
si algo no está, dilo claramente en vez de inventarlo."""

    messages = [
        {"role": "system", "content": systemprompt + "\n\n--- CONTENIDO DEL DOCUMENTO ---\n" + documenttext + "\n--- FIN ---"},
    ] + historial + [{"role": "user", "content": pregunta}]

    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-5",  # o el modelo que prefieras, ver nota abajo
        messages=messages,
        max_tokens=1500,
        extra_headers={
            "HTTP-Referer": "https://crucemundo.streamlit.app",  # opcional pero recomendado por OpenRouter
            "X-Title": "Crucemundo Hub",
        },
    )
    return response.choices[0].message.content


st.markdown("### 🤖 Pregunta a Claude")
st.caption(f"Fuente: documento «{DOCUMENTNAME}», actualizado automáticamente cada noche desde crucemundo.es")

if st.button("← Volver al Hub"):
    st.switch_page("app.py")  # ajusta el nombre si tu archivo principal se llama distinto

try:
    documenttext = getdocumenttext()
    st.success(f"Documento cargado ({len(documenttext)} caracteres)")
except Exception as exc:
    st.error(f"No se pudo leer el documento: {exc}")
    st.stop()

if "claudehistorial" not in st.session_state:
    st.session_state.claudehistorial = []

for msg in st.session_state.claudehistorial:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

pregunta = st.chat_input("Pregunta algo sobre la información de Crucemundo...")
if pregunta:
    st.session_state.claudehistorial.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.write(pregunta)
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            respuesta = preguntaraldocumento(
                documenttext, pregunta, st.session_state.claudehistorial[:-1]
            )
        st.write(respuesta)
    st.session_state.claudehistorial.append({"role": "assistant", "content": respuesta})

if st.session_state.claudehistorial and st.button("🗑️ Limpiar conversación"):
    st.session_state.claudehistorial = []
    st.rerun()
