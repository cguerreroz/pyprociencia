import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from core import get_data, ensure_defaults, sidebar_contexto, get_universo, get_muestra_scored, presupuesto_actual
from solvers.base import RestriccionesEquidad
from solvers.cbc_backend import resolver_portafolio
from solvers.greedy import resolver_greedy

st.title("📈 Sensibilidad y escenarios")

df, resumen = get_data()
ensure_defaults(resumen)
sidebar_contexto(df, resumen)

universo = get_universo(df)
muestra = get_muestra_scored(universo).reset_index(drop=True)
presupuesto_base = presupuesto_actual(universo)
restricciones_actuales = st.session_state["restricciones"]

costos = muestra["MONTO_SOLES"].tolist()
scores = muestra["SCORE"].tolist()
entidades = muestra["ENTIDAD_EJECUTORA_SUBVENCIONADO"].tolist()
tipo_entidad = muestra["TIPO_ENTIDAD"].tolist()
sexo = muestra["SEXO"].tolist()
sin_restricciones = RestriccionesEquidad(diversidad_activa=False, institutos_activa=False, genero_activa=False)

st.markdown("#### Barrido: score y proyectos financiados vs. presupuesto")
total_convocatoria = float(universo["MONTO_SOLES"].sum())
col_a, col_b = st.columns(2)
pct_min = col_a.slider("% mínimo de la convocatoria", 5, 95, 10)
pct_max = col_b.slider("% máximo de la convocatoria", pct_min + 5, 100, 60)

pasos = np.linspace(pct_min, pct_max, 12)
filas = []
for pct in pasos:
    b = total_convocatoria * pct / 100
    res = resolver_portafolio(costos, scores, b, entidades, tipo_entidad, sexo, restricciones_actuales)
    if res.estado == "OPTIMO":
        filas.append({"pct_presupuesto": round(pct, 1), "presupuesto": b, "score_total": res.score_total, "n_proyectos": len(res.seleccionados)})
barrido = pd.DataFrame(filas)

if len(barrido):
    fig = px.line(barrido, x="pct_presupuesto", y="score_total", markers=True, labels={"pct_presupuesto": "% de la convocatoria", "score_total": "Score total"})
    fig.add_vline(x=round(100 * presupuesto_base / total_convocatoria, 1), line_dash="dash", line_color="#B8823A", annotation_text="presupuesto actual")
    fig.update_layout(height=380, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(barrido.rename(columns={"pct_presupuesto": "% convocatoria", "presupuesto": "Presupuesto (S/.)", "score_total": "Score total", "n_proyectos": "N proyectos"}), width="stretch", hide_index=True)
else:
    st.info("Ningún punto del barrido fue factible con las restricciones actuales; prueba desactivar alguna en el Panel de decisión.")

st.divider()
st.markdown("#### Comparación de escenarios (al presupuesto actual)")

res_completo = resolver_portafolio(costos, scores, presupuesto_base, entidades, tipo_entidad, sexo, restricciones_actuales)
res_sin_restr = resolver_portafolio(costos, scores, presupuesto_base, entidades, tipo_entidad, sexo, sin_restricciones)
res_greedy = resolver_greedy(costos, scores, presupuesto_base)

comparacion = pd.DataFrame([
    {"Escenario": "Modelo completo (presupuesto + equidad)", "Score total": res_completo.score_total, "N proyectos": len(res_completo.seleccionados), "Costo usado (S/.)": res_completo.costo_total, "% presupuesto": round(100*res_completo.costo_total/presupuesto_base, 1) if presupuesto_base else 0},
    {"Escenario": "Sin restricciones adicionales (solo presupuesto)", "Score total": res_sin_restr.score_total, "N proyectos": len(res_sin_restr.seleccionados), "Costo usado (S/.)": res_sin_restr.costo_total, "% presupuesto": round(100*res_sin_restr.costo_total/presupuesto_base, 1) if presupuesto_base else 0},
    {"Escenario": "Heurística Greedy (razón score/costo)", "Score total": res_greedy.score_total, "N proyectos": len(res_greedy.seleccionados), "Costo usado (S/.)": res_greedy.costo_total, "% presupuesto": round(100*res_greedy.costo_total/presupuesto_base, 1) if presupuesto_base else 0},
])
st.dataframe(comparacion, width="stretch", hide_index=True)

fig_comp = px.bar(comparacion, x="Escenario", y="Score total", color="Escenario", text="Score total")
fig_comp.update_layout(height=360, margin=dict(t=10), showlegend=False)
st.plotly_chart(fig_comp, width="stretch")

if res_completo.estado == "OPTIMO" and res_sin_restr.estado == "OPTIMO":
    costo_equidad = res_sin_restr.score_total - res_completo.score_total
    pct_costo = 100 * costo_equidad / res_sin_restr.score_total if res_sin_restr.score_total else 0
    st.metric("Costo de la equidad", f"{costo_equidad:,.1f} puntos ({pct_costo:.1f}%)", help="Score que se deja de ganar por imponer diversidad institucional, fomento a institutos y equidad de género.")
