# 💼 Portal Laboral

Portal de gestión de búsqueda de empleo construido con **Python + Streamlit** y **Google Drive** como backend.

## ✨ Características

- 🔗 **Tarjetas de portales de empleo** — acceso directo a InfoJobs, LinkedIn, Indeed, Tecnoempleo...
- 📋 **Registro de candidaturas** — formulario para registrar cada solicitud
- 📄 **Copia automática de plantilla** — crea una copia de tu Google Sheet por cada candidatura (sin tocar el original)
- 📊 **Historial de sesión** — seguimiento de candidaturas registradas
- 🎨 **Diseño profesional** — interfaz oscura y moderna

## 🚀 Despliegue en Streamlit Cloud

1. Sube este repositorio a GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repo y selecciona `app.py`
4. ¡Listo!

## ⚙️ Configuración

Antes de desplegar, edita en `app.py`:

```python
# ID de tu plantilla de Google Sheets
TEMPLATE_SHEET_ID = "TU_ID_DE_SHEET_AQUI"

# ID del logo en Google Drive (debe ser público)
LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
```

### Cómo obtener el ID de tu Google Sheet

La URL de tu sheet tiene este formato:
```
https://docs.google.com/spreadsheets/d/AQUI_ESTA_EL_ID/edit
```

### Cómo hacer pública la imagen del logo

1. Ve a Google Drive → botón derecho sobre la imagen → **Compartir**
2. En "Acceso general" → selecciona **"Cualquier persona con el enlace"**
3. Copia el ID de la URL del archivo

## 📁 Estructura del proyecto

```
portal_laboral/
├── app.py              # Aplicación principal
├── requirements.txt    # Dependencias Python
└── README.md           # Este archivo
```

## 🔮 Próximas funcionalidades

- [ ] Autenticación con Google (OAuth)
- [ ] Escritura directa en Google Sheets via API
- [ ] Estadísticas y dashboard de candidaturas
- [ ] Notificaciones y recordatorios
- [ ] Filtros por estado (enviada, entrevista, rechazada...)
