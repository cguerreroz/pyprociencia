import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import get_data, ensure_defaults, sidebar_contexto, get_universo, get_muestra_scored, diagnostico_y_resultado
from solvers.base import RestriccionesEquidad

st.title("🎒 Panel de decisión")
st.caption("El núcleo prescriptivo: mueve el presupuesto o las restricciones de equidad y el portafolio óptimo se recalcula al instante con CBC.")

df, resumen = get_data()
ensure_defaults(resumen)
sidebar_contexto(df, resumen)

universo = get_universo(df)
muestra = get_muestra_scored(universo)
total_convocatoria = float(universo["MONTO_SOLES"].sum())
total_muestra = float(muestra["MONTO_SOLES"].sum())

# ---------------- Controles ----------------
st.markdown("#### Presupuesto")
col_pct, col_manual = st.columns([2, 1])
with col_pct:
    pct_presupuesto = st.slider(
        "% del total solicitado por la convocatoria",
        min_value=5, max_value=100, value=round(st.session_state["pct_presupuesto"] * 100), step=1,
    )
    st.session_state["pct_presupuesto"] = pct_presupuesto / 100
    st.session_state["presupuesto_manual"] = None
with col_manual:
    usar_manual = st.checkbox("Ingresar monto exacto (S/.)")
    if usar_manual:
        monto_manual = st.number_input("Presupuesto (S/.)", min_value=0.0, value=round(total_convocatoria * st.session_state["pct_presupuesto"], 2), step=10000.0)
        st.session_state["presupuesto_manual"] = monto_manual

presupuesto = st.session_state["presupuesto_manual"] or round(total_convocatoria * st.session_state["pct_presupuesto"], 2)

st.caption(
    f"Total solicitado por la convocatoria completa: **S/ {total_convocatoria:,.0f}** · "
    f"Total solicitado por la muestra actual ({len(muestra)} proyectos): **S/ {total_muestra:,.0f}** · "
    f"Presupuesto asignado: **S/ {presupuesto:,.0f}**"
)
if presupuesto >= total_muestra:
    st.info(
        "ℹ El presupuesto asignado alcanza para financiar el 100% de la muestra actual: no es una restricción "
        "activa. Sube el % de muestra, reduce el % de presupuesto o cambia de convocatoria para un problema de "
        "decisión no trivial."
    )

st.markdown("#### Restricciones de equidad")
r = st.session_state["restricciones"]
col1, col2, col3 = st.columns(3)
with col1:
    diversidad_activa = st.toggle("Diversidad institucional", value=r.diversidad_activa)
    max_por_entidad = st.number_input("Máx. proyectos por entidad repetida", min_value=1, max_value=5, value=r.max_por_entidad, disabled=not diversidad_activa)
with col2:
    n_institutos_disp = int((muestra["TIPO_ENTIDAD"] == "INSTITUTO DE INVESTIGACIÓN").sum())
    institutos_activa = st.toggle("Fomento a institutos", value=r.institutos_activa)
    min_institutos = st.number_input(f"Mín. institutos financiados (máx. {n_institutos_disp} en la muestra)", min_value=0, max_value=max(n_institutos_disp, 0), value=min(r.min_institutos, max(n_institutos_disp, 0)), disabled=not institutos_activa)
with col3:
    n_mujeres_disp = int((muestra["SEXO"] == "FEMENINO").sum())
    genero_activa = st.toggle("Equidad de género", value=r.genero_activa)
    min_pct_mujeres = st.slider(f"Mín. % financiados liderados por mujeres ({n_mujeres_disp} disponibles en la muestra)", min_value=0, max_value=100, value=round(r.min_pct_mujeres * 100), disabled=not genero_activa)

st.session_state["restricciones"] = RestriccionesEquidad(
    diversidad_activa=diversidad_activa,
    max_por_entidad=int(max_por_entidad),
    institutos_activa=institutos_activa,
    min_institutos=int(min_institutos),
    genero_activa=genero_activa,
    min_pct_mujeres=min_pct_mujeres / 100,
)

st.divider()

diag, resultado = diagnostico_y_resultado(muestra, presupuesto)

if not diag.factible:
    st.error("⚠ Diagnóstico de factibilidad: " + diag.resumen())
    st.stop()

if resultado is None or resultado.estado != "OPTIMO":
    st.error(resultado.mensaje if resultado else "No se pudo resolver el modelo.")
    st.stop()

seleccionados = set(resultado.seleccionados)
muestra = muestra.reset_index(drop=True)
muestra["FINANCIADO"] = muestra.index.isin(seleccionados)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Score total", f"{resultado.score_total:,.1f}")
c2.metric("Proyectos financiados", f"{len(seleccionados)} / {len(muestra)}")
c3.metric("Presupuesto usado", f"S/ {resultado.costo_total:,.0f}  ({100*resultado.costo_total/presupuesto:.1f}%)")
c4.metric("Holgura", f"S/ {presupuesto - resultado.costo_total:,.0f}")
c5.metric("Gap de optimalidad", f"{resultado.gap_pct:.2f}%  ·  {resultado.tiempo_seg*1000:.0f} ms")

st.markdown("#### Portafolio óptimo")
col_bar, col_donut = st.columns([2, 1])
with col_bar:
    orden = muestra.sort_values("SCORE", ascending=True)
    fig = px.bar(
        orden, x="SCORE", y="CODIGO_ORDEN", color="FINANCIADO", orientation="h",
        color_discrete_map={True: "#2E6E5E", False: "#8C8574"},
        labels={"SCORE": "Score", "CODIGO_ORDEN": "Proyecto", "FINANCIADO": "Financiado"},
    )
    fig.update_layout(height=max(380, 18 * len(muestra)), margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
with col_donut:
    fig2 = go.Figure(data=[go.Pie(
        labels=["Usado", "Disponible"],
        values=[resultado.costo_total, max(presupuesto - resultado.costo_total, 0)],
        hole=0.55, marker_colors=["#B8823A", "#E7E1D2"],
    )])
    fig2.update_layout(height=300, margin=dict(t=10), showlegend=True)
    st.plotly_chart(fig2, width="stretch")

    no_seleccionados = muestra[~muestra["FINANCIADO"]].sort_values("SCORE", ascending=False)
    st.caption("**Frontera** — próximos candidatos si sube el presupuesto:")
    if len(no_seleccionados):
        for _, row in no_seleccionados.head(3).iterrows():
            st.caption(f"· {row['CODIGO_ORDEN']} — score {row['SCORE']}, requiere S/ {row['MONTO_SOLES']:,.0f} más")
    else:
        st.caption("Todos los proyectos de la muestra ya están financiados.")

st.markdown("#### Tabla exportable")
tabla = muestra[[
    "CODIGO_ORDEN", "ENTIDAD_EJECUTORA_SUBVENCIONADO", "TIPO_ENTIDAD", "SEXO",
    "MONTO_SOLES", "SCORE", "FINANCIADO",
]].rename(columns={"ENTIDAD_EJECUTORA_SUBVENCIONADO": "ENTIDAD", "MONTO_SOLES": "MONTO (S/.)"}).sort_values("SCORE", ascending=False)
st.dataframe(tabla, width="stretch", hide_index=True)

col_csv, col_xlsx = st.columns(2)
with col_csv:
    st.download_button("⬇ Descargar CSV", tabla.to_csv(index=False).encode("utf-8-sig"), "portafolio_optimo.csv", "text/csv")
with col_xlsx:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        tabla.to_excel(writer, index=False, sheet_name="Portafolio")
    st.download_button(
        "⬇ Descargar Excel", buffer.getvalue(), "portafolio_optimo.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
