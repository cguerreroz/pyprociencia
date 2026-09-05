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
st.caption(
    "Los tres escenarios usan el mismo presupuesto y la misma muestra; solo cambia la regla de decisión. "
    "Compáralos en paralelo para justificar qué política de selección conviene adoptar."
)

res_completo = resolver_portafolio(costos, scores, presupuesto_base, entidades, tipo_entidad, sexo, restricciones_actuales)
res_sin_restr = resolver_portafolio(costos, scores, presupuesto_base, entidades, tipo_entidad, sexo, sin_restricciones)
res_greedy = resolver_greedy(costos, scores, presupuesto_base)


def _stats_escenario(resultado) -> dict | None:
    """KPIs de score/costo MÁS composición del portafolio (entidades, institutos,
    mujeres) -- sin esto último no se puede justificar el trade-off real entre
    'más score' y 'más equidad', solo se ve el número agregado."""
    if resultado.estado != "OPTIMO":
        return None
    idx = list(resultado.seleccionados)
    sub = muestra.iloc[idx] if idx else muestra.iloc[0:0]
    return {
        "score_total": resultado.score_total,
        "n_proyectos": len(idx),
        "costo_total": resultado.costo_total,
        "n_entidades": int(sub["ENTIDAD_EJECUTORA_SUBVENCIONADO"].nunique()),
        "n_institutos": int((sub["TIPO_ENTIDAD"] == "INSTITUTO DE INVESTIGACIÓN").sum()),
        "n_mujeres": int((sub["SEXO"] == "FEMENINO").sum()),
    }


escenarios = [
    {
        "titulo": "Modelo completo",
        "subtitulo": "Presupuesto + equidad",
        "color": "#2E6E5E",
        "resultado": res_completo,
        "nota": "La política vigente en el Panel de decisión: maximiza el score sujeto al presupuesto Y a las restricciones de equidad activas. Es la opción defendible si el comité debe cumplir criterios de fomento científico, no solo maximizar valor.",
    },
    {
        "titulo": "Sin restricciones",
        "subtitulo": "Solo presupuesto",
        "color": "#B8823A",
        "resultado": res_sin_restr,
        "nota": "El techo teórico de score con este presupuesto, ignorando toda política de equidad. Sirve como referencia de cuánto \"cuesta\" la equidad, no como alternativa recomendable si la equidad es un objetivo institucional.",
    },
    {
        "titulo": "Heurística Greedy",
        "subtitulo": "Regla score/costo",
        "color": "#8C8574",
        "resultado": res_greedy,
        "nota": "Cómo decidiría un comité sin herramienta de optimización: ordena por razón score/costo y llena el presupuesto. Sirve para justificar el uso del solver exacto frente a una regla manual.",
    },
]

cols = st.columns(3)
stats = {}
for col, esc in zip(cols, escenarios):
    s = _stats_escenario(esc["resultado"])
    stats[esc["titulo"]] = s
    with col:
        st.markdown(
            f"""
            <div style="border-top:4px solid {esc['color']}; border-radius:4px; padding:10px 2px 2px 2px;">
                <div style="font-weight:700; font-size:1rem;">{esc['titulo']}</div>
                <div style="font-size:0.78rem; color:#888; margin-bottom:6px;">{esc['subtitulo']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if s is None:
            st.warning("No factible con este presupuesto/restricciones.")
        else:
            st.metric("Score total", f"{s['score_total']:,.1f}")
            st.metric("Proyectos financiados", f"{s['n_proyectos']} / {len(muestra)}")
            st.metric("Presupuesto usado", f"S/ {s['costo_total']:,.0f}", f"{100*s['costo_total']/presupuesto_base:.1f}% del asignado" if presupuesto_base else None)
            st.caption(f"Entidades distintas: **{s['n_entidades']}** · Institutos: **{s['n_institutos']}** · Proyectos de mujeres: **{s['n_mujeres']}**")
        st.caption(esc["nota"])

st.markdown("##### Detalle comparativo")
filas_detalle = []
etiquetas_fila = [
    ("score_total", "Score total", "{:,.1f}"),
    ("n_proyectos", "Proyectos financiados", "{:,.0f}"),
    ("costo_total", "Presupuesto usado (S/.)", "{:,.0f}"),
    ("n_entidades", "Entidades distintas financiadas", "{:,.0f}"),
    ("n_institutos", "Institutos financiados", "{:,.0f}"),
    ("n_mujeres", "Proyectos de mujeres financiados", "{:,.0f}"),
]
for clave, etiqueta, fmt in etiquetas_fila:
    fila = {"Indicador": etiqueta}
    for esc in escenarios:
        s = stats[esc["titulo"]]
        fila[esc["titulo"]] = fmt.format(s[clave]) if s else "—"
    filas_detalle.append(fila)
st.dataframe(pd.DataFrame(filas_detalle), width="stretch", hide_index=True)

fig_comp = px.bar(
    pd.DataFrame([{"Escenario": e["titulo"], "Score total": stats[e["titulo"]]["score_total"]} for e in escenarios if stats[e["titulo"]]]),
    x="Escenario", y="Score total", color="Escenario", text="Score total",
    color_discrete_map={e["titulo"]: e["color"] for e in escenarios},
)
fig_comp.update_layout(height=340, margin=dict(t=10), showlegend=False)
st.plotly_chart(fig_comp, width="stretch")

def _delta_texto(delta: int, nombre: str) -> str:
    if delta == 0:
        return f"el mismo número de {nombre}"
    if delta > 0:
        return f"{delta} {nombre} más"
    return f"{abs(delta)} {nombre} menos"


if stats["Modelo completo"] and stats["Sin restricciones"]:
    c, s = stats["Modelo completo"], stats["Sin restricciones"]
    costo_equidad = s["score_total"] - c["score_total"]
    pct_costo = 100 * costo_equidad / s["score_total"] if s["score_total"] else 0
    delta_entidades = c["n_entidades"] - s["n_entidades"]
    delta_institutos = c["n_institutos"] - s["n_institutos"]
    delta_mujeres = c["n_mujeres"] - s["n_mujeres"]
    st.metric(
        "Costo de la equidad",
        f"{costo_equidad:,.1f} puntos ({pct_costo:.1f}%)",
        help="Score que se deja de ganar por imponer diversidad institucional, fomento a institutos y equidad de género.",
    )
    st.info(
        f"**Cómo leer esto para decidir:** exigir equidad cuesta **{pct_costo:.1f}%** del score máximo posible con este "
        f"presupuesto, y a cambio el modelo completo financia {_delta_texto(delta_entidades, 'entidades distintas')}, "
        f"{_delta_texto(delta_institutos, 'institutos')} y {_delta_texto(delta_mujeres, 'proyectos de mujeres')} "
        "que la opción sin restricciones. "
        + ("Si ese costo en puntos es bajo frente a la ganancia en diversidad, la equidad sale casi gratis y conviene mantenerla. "
           if pct_costo < 10 else
           "Es un costo considerable: el comité debe decidir explícitamente si la ganancia en diversidad institucional y de género "
           "justifica renunciar a ese score, en vez de que la política de equidad se adopte por defecto sin discutir el trade-off. ")
    )

    if stats.get("Sin restricciones") and stats.get("Heurística Greedy"):
        # Comparación en igualdad de condiciones: ambas sin restricciones de
        # equidad, para aislar "calidad del método" de "costo de la política".
        # Comparar Greedy contra el Modelo completo mezclaría las dos cosas y
        # podría dar una diferencia negativa sin significado claro.
        ganancia_vs_greedy = stats["Sin restricciones"]["score_total"] - stats["Heurística Greedy"]["score_total"]
        st.caption(
            f"Comparando en igualdad de condiciones (ambos sin restricciones de equidad, para no mezclar "
            f"\"calidad del método\" con \"costo de la política\"): el solver exacto (CBC) gana "
            f"**{ganancia_vs_greedy:,.1f} puntos** frente a la heurística Greedy con el mismo presupuesto — "
            "así de subóptima puede quedar una priorización manual por razón score/costo."
        )
