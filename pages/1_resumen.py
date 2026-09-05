import streamlit as st

from core import get_data, ensure_defaults, sidebar_contexto, get_universo, get_muestra_scored, presupuesto_actual, diagnostico_y_resultado

st.title("🎒 Modelos Binarios: Programación Entera Binaria")
st.caption("Selección de proyectos de investigación en PROCIENCIA bajo restricción presupuestal y criterios de fomento de política científica — Panel Análisis Prescriptivo")

df, resumen = get_data()
ensure_defaults(resumen)
sidebar_contexto(df, resumen)

universo = get_universo(df)
muestra = get_muestra_scored(universo)
presupuesto = presupuesto_actual(universo)
diag, resultado = diagnostico_y_resultado(muestra, presupuesto)

st.subheader(st.session_state["convocatoria"].title())
if st.session_state.get("modo_caso_base"):
    st.caption("🔒 Modo validación activo — reproduciendo el caso exacto del informe (Anexo A).")

if resultado is not None and resultado.estado == "OPTIMO":
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Score total", f"{resultado.score_total:,.1f}")
    c2.metric("Proyectos financiados", f"{len(resultado.seleccionados)} / {len(muestra)}")
    c3.metric("Presupuesto usado", f"{100*resultado.costo_total/presupuesto:.1f}%" if presupuesto else "—")
    c4.metric("Presupuesto disponible", f"S/ {presupuesto:,.0f}")
    c5.metric("Gap de optimalidad", f"{resultado.gap_pct:.2f}%")
else:
    st.warning("⚠ " + (diag.resumen() if diag else "Configura la convocatoria y la muestra en la página 'Datos y contexto'."))

st.page_link("pages/4_panel_decision.py", label="Ir al panel de decisión →", icon="🎒")

st.divider()
st.markdown("#### Qué es real y qué es supuesto de modelado")
col_real, col_sim = st.columns(2)
with col_real:
    st.success(
        "**Real (CONCYTEC / PROCIENCIA)**\n\n"
        "- Las 909 filas del dataset, sin nulos ni duplicados\n"
        "- Las 57 convocatorias, sus proyectos, entidades, montos y sexo del investigador principal\n"
        "- El presupuesto total de cada convocatoria (suma de los montos ya normalizados a soles)"
    )
with col_sim:
    st.warning(
        "**Simulado (supuesto del equipo)**\n\n"
        "- El % del presupuesto realmente asignado a la convocatoria (40% por defecto)\n"
        "- El score de priorización (Sección 3.3 del informe — no es una evaluación oficial)\n"
        "- Los mínimos de institutos y de % de mujeres, y el máximo por entidad (política adoptada por el equipo)"
    )

st.caption(
    "Basado en el dataset abierto de CONCYTEC (2015–2021) y en el informe académico "
    "\"Selección de Proyectos de Investigación PROCIENCIA bajo Restricción Presupuestal y criterios de fomento de política científica\" "
    "— Maestría en Ciencia de Datos, Modelos Prescriptivos y Optimización - 2026-II."
)
