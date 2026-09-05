import pandas as pd
import streamlit as st

from core import get_data, ensure_defaults, sidebar_contexto
from data.scoring import TABLA_B

st.title("📋 Metodología y transparencia")

df, resumen = get_data()
ensure_defaults(resumen)
sidebar_contexto(df, resumen)

st.markdown("#### Tabla A · qué es real y qué es supuesto de modelado")
tabla_a = pd.DataFrame([
    ("Los proyectos del dataset completo (909) y de las 57 convocatorias", "REAL", "Fuente oficial CONCYTEC, sin modificar"),
    ("Montos, entidad, tipo de entidad, sexo del investigador principal", "REAL", "Datos oficiales; solo se normaliza la moneda a soles"),
    ("Presupuesto de cada convocatoria (Σ MONTO de sus proyectos)", "REAL", "Calculado a partir de datos oficiales"),
    ("% del presupuesto de la convocatoria realmente disponible (40% por defecto)", "SIMULADO", "Supuesto de modelado, ajustable por el usuario"),
    ("Score de priorización (0-100) de cada proyecto", "SIMULADO", "Construido por el equipo (Sección 3.3); no es una evaluación oficial de PROCIENCIA"),
    ("Restricciones de diversidad institucional, institutos y equidad de género", "SIMULADO", "Reglas de política adicionales definidas por el equipo, ajustables por el usuario"),
], columns=["Elemento", "Origen", "Detalle"])
st.dataframe(tabla_a, width="stretch", hide_index=True)

st.markdown("#### Tabla B · score de priorización (fijo, no editable)")
st.dataframe(TABLA_B, width="stretch", hide_index=True)

st.divider()
st.markdown("#### Registro histórico de Gurobi (informe académico, Sección 4.1)")
st.caption(
    "Este panel resuelve con CBC (código abierto), no con Gurobi. El siguiente log se conserva únicamente como "
    "evidencia del informe académico original y con fines pedagógicos — no se ejecuta en este despliegue."
)
st.code(
"""Optimize a model with 8 rows, 30 columns and 50 nonzeros (Max)
Variable types: 0 continuous, 30 integer (30 binary)
Found heuristic solution: objective 1036.4000000
Presolve removed 3 rows and 9 columns
Presolved: 5 rows, 21 columns, 29 nonzeros
Found heuristic solution: objective 872.5000000
Found heuristic solution: objective 1063.2000000
Root relaxation: objective 1202.51334, 3 iterations
Nodes    |    Current Node    |     Objective Bounds
Expl Unexpl |  Obj  Depth IntInf | Incumbent    BestBd   Gap
0     0 1202.51334    0    1 1063.20000 1202.51334  13.1%
H    0     0                    1127.4000000 1202.51334   6.66%
H    0     0                    1153.4000000 1202.51334   4.26%
H    0     0                    1161.7000000 1202.51334   3.51%
0     0 1195.50047    0    3 1161.70000 1195.50047   2.91%
H    0     0                    1163.4000000 1195.50047   2.76%
H    0     0                    1171.7000000 1195.50047   2.03%
0     0 1188.49091    0    3 1171.70000 1188.49091   1.43%
0     0     cutoff    0      1171.70000 1171.70000   0.00%
Cutting planes:
Gomory: 1
MIR: 1
GUB cover: 1
Explored 1 nodes (11 simplex iterations) in 0.02 seconds
Optimal solution found (tolerance 1.00e-04)
Best objective 1.171700000000e+03, best bound 1.171700000000e+03, gap 0.0000%""",
    language="text",
)

with st.expander("Cómo leer este registro (piso y techo del Branch & Bound)"):
    st.markdown(
        "El algoritmo busca un **piso** (la mejor combinación real encontrada hasta el momento: líneas 'H') y un "
        "**techo** (el valor teórico más alto posible, relajando la exigencia de todo-o-nada: 'Root relaxation'). "
        "El techo baja con planos de corte (Gomory, MIR, GUB cover) hasta encontrarse con el piso — en este caso, "
        "ambos llegan a 1171.70, así que el gap de optimalidad es 0.00% y no puede existir una combinación mejor. "
        "CBC resuelve el mismo tipo de problema con la misma lógica de Branch & Bound / Branch & Cut."
    )

st.divider()
st.markdown("#### Límites y mejoras propuestas")
st.markdown(
    "- El score fue construido por el equipo, no por los pares evaluadores de PROCIENCIA: en una implementación "
    "real debería derivarse de la evaluación técnica oficial.\n"
    "- El % de presupuesto asignado a cada convocatoria es un supuesto; el techo presupuestal real no es público.\n"
    "- Extensión futura: incorporar indicadores bibliométricos, análisis de sensibilidad sobre costos inciertos, "
    "y un horizonte multi-periodo con compromisos plurianuales."
)

st.caption(
    "Fuente: \"Estadísticas de Proyectos de Investigación Científica por fuentes de financiamiento de PROCIENCIA "
    "(2015–2021)\", CONCYTEC, Plataforma Nacional de Datos Abiertos del Perú."
)
