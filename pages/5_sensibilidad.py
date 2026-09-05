import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from core import get_data, ensure_defaults, sidebar_contexto, get_universo, get_muestra_scored, presupuesto_actual
from data.sampling import muestra_estratificada
from data.scoring import calcular_score
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
total_convocatoria = float(universo["MONTO_SOLES"].sum())

sin_restricciones = RestriccionesEquidad(diversidad_activa=False, institutos_activa=False)
modo_caso_base = st.session_state.get("modo_caso_base", False)

st.caption(
    "El barrido de presupuesto y la comparación de escenarios de esta página comparten los mismos parámetros: "
    "ajústalos una sola vez aquí y ambos análisis se recalculan juntos, en vivo."
)

with st.container(border=True):
    st.markdown("##### 🎛️ Parámetros del análisis — cámbialos y todo lo de abajo se recalcula al instante")
    st.caption(
        "Estos son los valores que entran al barrido de presupuesto y a la comparación de escenarios (número de "
        "proyectos de la muestra, presupuesto y restricciones de equidad). Ajústalos aquí para analizar en vivo, "
        "sin salir de esta página ni afectar lo configurado en el Panel de decisión."
    )

    col_n, col_pres, col_div, col_ins = st.columns([1.1, 1.3, 1, 1])

    with col_n:
        if modo_caso_base:
            st.caption(f"**Número de proyectos:** fijado por el modo validación ({len(muestra)}, Anexo A).")
            muestra_comp = muestra
        else:
            n_disponibles_comp = max(len(universo), 1)
            n_muestra_comp = st.number_input(
                f"Número de proyectos en la muestra ({len(universo)} disponibles)",
                min_value=1, max_value=n_disponibles_comp,
                value=min(st.session_state.get("sens_n_muestra", int(st.session_state["n_muestra"])), n_disponibles_comp),
                step=1, key="sens_n_muestra",
            )
            muestra_comp = calcular_score(
                muestra_estratificada(universo, int(n_muestra_comp), st.session_state["semilla"])
            ).reset_index(drop=True)
            st.caption("Muestreo estratificado con la misma semilla del Panel de decisión.")

    costos_comp = muestra_comp["MONTO_SOLES"].tolist()
    scores_comp = muestra_comp["SCORE"].tolist()
    entidades_comp = muestra_comp["ENTIDAD_EJECUTORA_SUBVENCIONADO"].tolist()
    tipo_entidad_comp = muestra_comp["TIPO_ENTIDAD"].tolist()
    n_institutos_disp_comp = int((muestra_comp["TIPO_ENTIDAD"] == "INSTITUTO DE INVESTIGACIÓN").sum())

    with col_pres:
        pct_comp_default = round(100 * presupuesto_base / total_convocatoria, 1) if total_convocatoria else 40.0
        pct_comp_default = min(max(pct_comp_default, 5.0), 100.0)
        pct_comp = st.slider(
            "Presupuesto (% de la convocatoria)",
            min_value=5, max_value=150,
            value=int(round(st.session_state.get("sens_pct_presupuesto", pct_comp_default))),
            step=1, key="sens_pct_presupuesto",
        )
        st.caption("Hasta 150% para simular un incremento de hasta 50% sobre el total de la convocatoria.")
        presupuesto_pct_comp = total_convocatoria * pct_comp / 100

        usar_monto_manual_comp = st.checkbox(
            "Ingresar monto exacto (S/.)",
            value=st.session_state.get("sens_presupuesto_manual") is not None,
            key="sens_chk_monto_manual",
        )
        if usar_monto_manual_comp:
            valor_inicial_comp = st.session_state.get("sens_presupuesto_manual") or round(presupuesto_pct_comp, 2)
            monto_manual_comp = st.number_input(
                "Presupuesto (S/.)", min_value=0.0, value=float(valor_inicial_comp), step=10000.0,
                key="sens_num_monto_manual",
            )
            st.session_state["sens_presupuesto_manual"] = monto_manual_comp
        else:
            st.session_state["sens_presupuesto_manual"] = None

        presupuesto_comp = st.session_state["sens_presupuesto_manual"] or presupuesto_pct_comp
        st.caption(
            f"S/ {presupuesto_comp:,.0f}"
            + (" (monto exacto — anula el %)" if usar_monto_manual_comp else "")
        )
    with col_div:
        diversidad_activa_comp = st.toggle(
            "Diversidad institucional", value=st.session_state.get("sens_diversidad_activa", restricciones_actuales.diversidad_activa),
            key="sens_diversidad_activa",
        )
        tope_max_entidad = max(len(muestra_comp), 1)
        max_por_entidad_comp = st.number_input(
            "Máx. proyectos por entidad", min_value=1, max_value=tope_max_entidad,
            value=min(st.session_state.get("sens_max_por_entidad", restricciones_actuales.max_por_entidad), tope_max_entidad),
            disabled=not diversidad_activa_comp, key="sens_max_por_entidad",
        )
    with col_ins:
        institutos_activa_comp = st.toggle(
            "Fomento a institutos", value=st.session_state.get("sens_institutos_activa", restricciones_actuales.institutos_activa),
            key="sens_institutos_activa",
        )
        tope_institutos = max(len(muestra_comp), 1)
        min_institutos_comp = st.number_input(
            f"Mín. institutos financiados ({n_institutos_disp_comp} disponibles)", min_value=0, max_value=tope_institutos,
            value=min(st.session_state.get("sens_min_institutos", restricciones_actuales.min_institutos), tope_institutos),
            disabled=not institutos_activa_comp, key="sens_min_institutos",
        )

restricciones_comp = RestriccionesEquidad(
    diversidad_activa=diversidad_activa_comp,
    max_por_entidad=int(max_por_entidad_comp),
    institutos_activa=institutos_activa_comp,
    min_institutos=int(min_institutos_comp),
)

st.divider()

st.markdown("#### Barrido: score y proyectos financiados vs. presupuesto")
st.caption(
    "Usa la muestra y las restricciones configuradas arriba; solo el % de presupuesto varía a lo largo del eje X, "
    "para ver en qué punto el presupuesto deja (o no) de ser la restricción activa."
)
col_a, col_b = st.columns(2)
pct_min = col_a.slider("% mínimo de la convocatoria", 5, 145, 10)
pct_max = col_b.slider("% máximo de la convocatoria", pct_min + 5, 150, 60)

pasos = np.linspace(pct_min, pct_max, 12)
filas = []
for pct in pasos:
    b = total_convocatoria * pct / 100
    res = resolver_portafolio(costos_comp, scores_comp, b, entidades_comp, tipo_entidad_comp, restricciones_comp)
    if res.estado == "OPTIMO":
        filas.append({"pct_presupuesto": round(pct, 1), "presupuesto": b, "score_total": res.score_total, "n_proyectos": len(res.seleccionados)})
barrido = pd.DataFrame(filas)

if len(barrido):
    fig = px.line(barrido, x="pct_presupuesto", y="score_total", markers=True, labels={"pct_presupuesto": "% de la convocatoria", "score_total": "Score total"})
    fig.add_vline(x=round(100 * presupuesto_comp / total_convocatoria, 1), line_dash="dash", line_color="#B8823A", annotation_text="presupuesto del análisis")
    fig.update_layout(height=380, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(barrido.rename(columns={"pct_presupuesto": "% convocatoria", "presupuesto": "Presupuesto (S/.)", "score_total": "Score total", "n_proyectos": "N proyectos"}), width="stretch", hide_index=True)
else:
    st.info("Ningún punto del barrido fue factible con las restricciones activas; prueba desactivarlas o relajarlas en \"Parámetros del análisis\" arriba.")

st.divider()
st.markdown("#### Comparación de escenarios")
st.caption(
    "Los tres escenarios usan la misma muestra y presupuesto configurados arriba; solo cambia la regla de decisión. "
    "Compáralos en paralelo para justificar qué política de selección conviene adoptar."
)

res_completo = resolver_portafolio(costos_comp, scores_comp, presupuesto_comp, entidades_comp, tipo_entidad_comp, restricciones_comp)
res_sin_restr = resolver_portafolio(costos_comp, scores_comp, presupuesto_comp, entidades_comp, tipo_entidad_comp, sin_restricciones)
res_greedy = resolver_greedy(costos_comp, scores_comp, presupuesto_comp)


def _stats_escenario(resultado) -> dict | None:
    """KPIs de score/costo MÁS composición del portafolio (entidades, institutos)
    -- sin esto último no se puede justificar el trade-off real entre 'más score'
    y 'más equidad', solo se ve el número agregado."""
    if resultado.estado != "OPTIMO":
        return None
    idx = list(resultado.seleccionados)
    sub = muestra_comp.iloc[idx] if idx else muestra_comp.iloc[0:0]
    return {
        "score_total": resultado.score_total,
        "n_proyectos": len(idx),
        "costo_total": resultado.costo_total,
        "n_entidades": int(sub["ENTIDAD_EJECUTORA_SUBVENCIONADO"].nunique()),
        "n_institutos": int((sub["TIPO_ENTIDAD"] == "INSTITUTO DE INVESTIGACIÓN").sum()),
    }


escenarios = [
    {
        "titulo": "Modelo completo",
        "subtitulo": "Presupuesto + equidad",
        "color": "#2E6E5E",
        "resultado": res_completo,
        "nota": "La política ajustable arriba: maximiza el score sujeto al presupuesto Y a las restricciones de equidad activas. Es la opción defendible si el comité debe cumplir criterios de fomento científico, no solo maximizar valor.",
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
            st.metric("Proyectos financiados", f"{s['n_proyectos']} / {len(muestra_comp)}")
            st.metric("Presupuesto usado", f"S/ {s['costo_total']:,.0f}", f"{100*s['costo_total']/presupuesto_comp:.1f}% del asignado" if presupuesto_comp else None)
            st.caption(f"Entidades distintas: **{s['n_entidades']}** · Institutos: **{s['n_institutos']}**")
        st.caption(esc["nota"])

st.markdown("##### Detalle comparativo")
filas_detalle = []
etiquetas_fila = [
    ("score_total", "Score total", "{:,.1f}"),
    ("n_proyectos", "Proyectos financiados", "{:,.0f}"),
    ("costo_total", "Presupuesto usado (S/.)", "{:,.0f}"),
    ("n_entidades", "Entidades distintas financiadas", "{:,.0f}"),
    ("n_institutos", "Institutos financiados", "{:,.0f}"),
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
    st.metric(
        "Costo de la equidad",
        f"{costo_equidad:,.1f} puntos ({pct_costo:.1f}%)",
        help="Score que se deja de ganar por imponer diversidad institucional y fomento a institutos.",
    )
    st.info(
        f"**Cómo leer esto para decidir:** exigir equidad cuesta **{pct_costo:.1f}%** del score máximo posible con este "
        f"presupuesto, y a cambio el modelo completo financia {_delta_texto(delta_entidades, 'entidades distintas')} y "
        f"{_delta_texto(delta_institutos, 'institutos')} "
        "que la opción sin restricciones. "
        + ("Si ese costo en puntos es bajo frente a la ganancia en diversidad, la equidad sale casi gratis y conviene mantenerla. "
           if pct_costo < 10 else
           "Es un costo considerable: el comité debe decidir explícitamente si la ganancia en diversidad institucional "
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
