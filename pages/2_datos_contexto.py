import plotly.express as px
import streamlit as st

from core import get_data, ensure_defaults, sidebar_contexto, get_universo, get_muestra_scored, activar_caso_base, desactivar_caso_base
from data.caso_base import RESULTADO_ESPERADO
from data.convocatorias import etiqueta_convocatoria
from data.sampling import resumen_reduccion

st.title("🗂️ Datos y contexto")

df, resumen = get_data()
ensure_defaults(resumen)
sidebar_contexto(df, resumen)

modo_caso_base = st.session_state.get("modo_caso_base", False)

with st.container(border=True):
    st.markdown("##### 🔒 Modo validación — reproducir el caso exacto del informe")
    st.caption(
        "Fija la convocatoria 2018-01, los 30 códigos de proyecto exactos del Anexo A, el presupuesto S/ 3,600,000 "
        "y las restricciones originales (sin equidad de género). Debe dar score "
        f"**{RESULTADO_ESPERADO['score_total']}**, **{RESULTADO_ESPERADO['n_proyectos']}** proyectos financiados. "
        "El número de proyectos y la semilla NO reproducen el muestreo del informe (el equipo nunca publicó su "
        "código exacto de muestreo estratificado) — esta lista fija es la única forma de igualar el resultado bit a bit."
    )
    activar = st.toggle("Activar modo validación", value=modo_caso_base, key="toggle_caso_base")
    if activar != modo_caso_base:
        if activar:
            activar_caso_base(resumen)
        else:
            desactivar_caso_base()
        st.rerun()

st.divider()

if modo_caso_base:
    st.info("Convocatoria y muestra fijadas por el modo validación. Desactívalo arriba para elegir otra convocatoria o tamaño de muestra.")
    st.markdown(f"**Convocatoria:** {st.session_state['convocatoria'].title()}")
else:
    def _aplicar_seleccion_principal() -> None:
        st.session_state["convocatoria"] = st.session_state["selector_convocatoria_principal"]

    st.markdown("#### 1. Elige la convocatoria")
    opciones = resumen["CONVOCATORIA"].tolist()
    etiquetas = {row["CONVOCATORIA"]: etiqueta_convocatoria(row) for _, row in resumen.iterrows()}
    # Igual que en el selector de la barra lateral: se sincroniza el widget con
    # session_state["convocatoria"] en cada rerun y se usa on_change (no una
    # comparación manual + st.rerun()) para que el resto de la página -- KPIs,
    # avisos, gráficos y tabla -- se actualice de inmediato al elegir, sin
    # depender de un segundo clic ni desincronizarse del selector lateral.
    st.session_state["selector_convocatoria_principal"] = st.session_state["convocatoria"]
    st.selectbox(
        "Convocatoria (57 disponibles, de 2015 a 2021)",
        opciones,
        format_func=lambda c: etiquetas[c],
        key="selector_convocatoria_principal",
        on_change=_aplicar_seleccion_principal,
    )

fila = resumen[resumen["CONVOCATORIA"] == st.session_state["convocatoria"]].iloc[0]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Proyectos", int(fila["n_proyectos"]))
c2.metric("Presupuesto total solicitado", f"S/ {fila['presupuesto_total_soles']:,.0f}")
c3.metric("Entidades únicas", int(fila["n_entidades_unicas"]))
c4.metric("Institutos de investigación", int(fila["n_institutos"]))
c5.metric("Proyectos de mujeres", f"{int(fila['n_mujeres'])} ({fila['pct_mujeres']}%)")

avisos = []
if fila["aviso_pocos_proyectos"]:
    avisos.append("Esta convocatoria tiene pocos proyectos: el muestreo estratificado y las restricciones de equidad pueden ser poco informativas.")
if fila["aviso_sin_institutos"]:
    avisos.append("Esta convocatoria no tiene institutos de investigación: desactiva la restricción de fomento a institutos o quedará infactible.")
if fila["aviso_sin_mujeres"]:
    avisos.append("Esta convocatoria no tiene proyectos liderados por mujeres: desactiva la restricción de equidad de género o quedará infactible.")
for a in avisos:
    st.warning("⚠ " + a)

st.divider()
if modo_caso_base:
    st.markdown("#### 2. Tamaño de la muestra")
    st.caption("Fijado por el modo validación: los 30 códigos exactos del Anexo A del informe.")
else:
    st.markdown("#### 2. Define el tamaño de la muestra")
    n_disponibles = int(fila["n_proyectos"])
    st.session_state["n_muestra"] = min(int(st.session_state["n_muestra"]), n_disponibles)
    if n_disponibles <= 1:
        st.caption(f"Esta convocatoria solo tiene {n_disponibles} proyecto: se incluye automáticamente, sin muestreo.")
        col_sem, col_btn = st.columns([1, 1])
    else:
        col_pct, col_sem, col_btn = st.columns([2, 1, 1])
        with col_pct:
            n_muestra = st.slider(
                "Número de proyectos a incluir en el análisis",
                min_value=1, max_value=n_disponibles, value=int(st.session_state["n_muestra"]), step=1,
                help="Muestreo aleatorio estratificado por tipo de entidad (conserva la proporción real de universidades, institutos, empresas, etc.)",
            )
            st.session_state["n_muestra"] = n_muestra
    with col_sem:
        st.session_state["semilla"] = st.number_input("Semilla", min_value=0, max_value=9999, value=st.session_state["semilla"], step=1)
    with col_btn:
        st.write("")
        st.write("")
        if st.button("🎲 Nueva muestra aleatoria"):
            st.session_state["semilla"] = int(st.session_state["semilla"]) + 1
            st.rerun()

universo = get_universo(df)
muestra = get_muestra_scored(universo)
red = resumen_reduccion(len(df), len(universo), len(muestra))

st.markdown(
    f"**{red['dataset_completo']} proyectos (2015–2021) → {red['convocatoria']} en esta convocatoria "
    f"({red['pct_convocatoria']}% del total) → {red['muestra']} en la muestra actual "
    f"({red['pct_muestra_de_convocatoria']}% de la convocatoria)**"
)

st.divider()
st.markdown("#### 3. Exploración de la convocatoria seleccionada")
tab1, tab2, tab3, tab4 = st.tabs(["Montos", "Por tipo de entidad", "Por sexo", "Calidad de datos"])
with tab1:
    fig = px.histogram(universo, x="MONTO_SOLES", nbins=25, labels={"MONTO_SOLES": "Monto (S/.)"})
    fig.update_layout(height=380, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
with tab2:
    conteo = universo["TIPO_ENTIDAD"].value_counts().reset_index()
    conteo.columns = ["Tipo de entidad", "N proyectos"]
    fig = px.bar(conteo, x="N proyectos", y="Tipo de entidad", orientation="h")
    fig.update_layout(height=380, margin=dict(t=10), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")
with tab3:
    conteo = universo["SEXO"].value_counts().reset_index()
    conteo.columns = ["Sexo", "N proyectos"]
    fig = px.pie(conteo, names="Sexo", values="N proyectos", hole=0.5)
    fig.update_layout(height=380, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
with tab4:
    st.markdown(
        f"- **Nulos en el dataset completo:** {df.attrs['n_nulos_originales']}\n"
        f"- **CODIGO_ORDEN duplicados:** {df.attrs['n_duplicados_originales']}\n"
        "- **DEPARTAMENTO** es constante (LIMA) en el 100% de los 909 registros — no aporta varianza geográfica y no se usa como filtro.\n"
        "- **Moneda:** 873 registros en soles, 23 en euros y 13 en libras esterlinas en el dataset completo; "
        "todos se normalizan a soles antes de cualquier cálculo (1 EUR ≈ S/ 4.15, 1 GBP ≈ S/ 4.75)."
    )

st.dataframe(
    muestra[["CODIGO_ORDEN", "ENTIDAD_EJECUTORA_SUBVENCIONADO", "TIPO_ENTIDAD", "SEXO", "MONTO_SOLES", "SCORE"]]
    .rename(columns={"ENTIDAD_EJECUTORA_SUBVENCIONADO": "ENTIDAD", "MONTO_SOLES": "MONTO (S/.)"}),
    width="stretch",
    hide_index=True,
)
