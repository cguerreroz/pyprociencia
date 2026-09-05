"""
Punto de entrada del panel. Registra las 6 páginas con st.navigation.
Ejecutar con:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Mochila con Equidad — PROCIENCIA",
    page_icon="🎒",
    layout="wide",
    initial_sidebar_state="expanded",
)

paginas = [
    st.Page("pages/1_resumen.py", title="Resumen ejecutivo", icon="📌", default=True),
    st.Page("pages/2_datos_contexto.py", title="Datos y contexto", icon="🗂️"),
    st.Page("pages/3_modelo.py", title="Modelo de optimización", icon="🧮"),
    st.Page("pages/4_panel_decision.py", title="Panel de decisión", icon="🎒"),
    st.Page("pages/5_sensibilidad.py", title="Sensibilidad y escenarios", icon="📈"),
    st.Page("pages/6_metodologia.py", title="Metodología y transparencia", icon="📋"),
]

navegacion = st.navigation(paginas)
navegacion.run()
