import streamlit as st

from core import get_data, ensure_defaults, sidebar_contexto, get_universo, get_muestra_scored
from data.scoring import TABLA_B

st.title("🧮 Modelo de optimización")

df, resumen = get_data()
ensure_defaults(resumen)
sidebar_contexto(df, resumen)

st.markdown("#### Formulación")
st.latex(r"""
\begin{aligned}
\textbf{Variables: } & x_i \in \{0,1\} \quad i = 1,\dots,n \text{ (proyectos de la muestra actual)} \\[4pt]
\textbf{Maximizar: } & Z = \sum_i s_i \, x_i \qquad \text{(score total)} \\[4pt]
\textbf{Sujeto a: } & \sum_i c_i \, x_i \le B & \text{(presupuesto)} \\
& \sum_{i \in E} x_i \le k & \text{(diversidad institucional, por entidad } E \text{ con} \ge 2 \text{ propuestas)} \\
& \sum_{i \in \text{Institutos}} x_i \ge m & \text{(fomento a institutos de investigación)}
\end{aligned}
""")

st.info(
    "**B** = presupuesto disponible = % elegido × (Σ MONTO de *todos* los proyectos de la convocatoria, "
    "no solo de la muestra). **k** y **m** se ajustan en la página *Panel de decisión* — son las dos "
    "restricciones de equidad configurables. **s_i** y **c_i** (score y costo de cada proyecto) no se ajustan aquí."
)

st.divider()
st.markdown("#### El score (s_i) es fijo — Sección 3.3 y Tabla B del informe")
st.latex(r"\text{Score}_i = 100 \times \big(0.40 \cdot \text{EntidadScore}_i + 0.35 \cdot \text{DiversidadScore}_i + 0.25 \cdot \text{GéneroScore}_i\big)")
st.caption(
    "Sin parámetros libres: los pesos (0.40 / 0.35 / 0.25) y las categorías de abajo se calculan automáticamente "
    "para cada proyecto. Es un criterio simulado (no oficial de PROCIENCIA), pero su cálculo no cambia con la interacción del usuario."
)
st.dataframe(TABLA_B, width="stretch", hide_index=True)

st.divider()
st.markdown("#### Vista previa: score calculado sobre la muestra actual")
universo = get_universo(df)
muestra = get_muestra_scored(universo)
st.dataframe(
    muestra[[
        "CODIGO_ORDEN", "ENTIDAD_EJECUTORA_SUBVENCIONADO", "TIPO_ENTIDAD", "SEXO",
        "ENTIDAD_SCORE", "DIVERSIDAD_SCORE", "GENERO_SCORE", "SCORE",
    ]].rename(columns={
        "ENTIDAD_EJECUTORA_SUBVENCIONADO": "ENTIDAD",
        "ENTIDAD_SCORE": "EntidadScore",
        "DIVERSIDAD_SCORE": "DiversidadScore",
        "GENERO_SCORE": "GéneroScore",
    }).sort_values("SCORE", ascending=False),
    width="stretch",
    hide_index=True,
)
