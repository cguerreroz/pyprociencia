"""
Único motor de optimización del panel: CBC (Coin-or Branch and Cut) a través
de PuLP. Código abierto, sin licencia, se instala con `pip install pulp` y
corre igual en un portátil que en Streamlit Community Cloud.

Resuelve exactamente el mismo problema de programación entera binaria del
informe académico (antes resuelto con Gurobi): maximizar el score total
sujeto a presupuesto, diversidad institucional, mínimo de institutos y
--nueva-- mínimo porcentaje de proyectos liderados por mujeres. CBC certifica
optimalidad igual que Gurobi para un problema de este tamaño (decenas a un
par de cientos de variables binarias): ambos son solvers exactos de
Branch & Bound / Branch & Cut, la diferencia es de implementación, no de
calidad de la respuesta.
"""

from __future__ import annotations

import time
from typing import Sequence

import pulp

from solvers.base import (
    ResultadoOptimizacion,
    RestriccionesEquidad,
    construir_grupos_entidad_repetida,
)


def resolver_portafolio(
    costos: Sequence[float],
    scores: Sequence[float],
    presupuesto: float,
    entidades: Sequence[str],
    tipo_entidad: Sequence[str],
    sexo: Sequence[str],
    restricciones: RestriccionesEquidad,
) -> ResultadoOptimizacion:
    n = len(costos)
    if n == 0:
        return ResultadoOptimizacion(estado="SIN_PROYECTOS", mensaje="No hay proyectos en la muestra actual.")

    t0 = time.perf_counter()

    modelo = pulp.LpProblem("Seleccion_Proyectos_PROCIENCIA", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]

    # Objetivo: maximizar el score total
    modelo += pulp.lpSum(scores[i] * x[i] for i in range(n)), "Score_total"

    # Presupuesto
    modelo += pulp.lpSum(costos[i] * x[i] for i in range(n)) <= presupuesto, "Presupuesto"

    # Diversidad institucional: máx. N proyectos por entidad con >= 2 propuestas
    if restricciones.diversidad_activa:
        grupos = construir_grupos_entidad_repetida(entidades)
        for entidad, idxs in grupos.items():
            nombre_restr = f"Diversidad_{abs(hash(entidad)) % 10_000_000}"
            modelo += pulp.lpSum(x[i] for i in idxs) <= restricciones.max_por_entidad, nombre_restr

    # Fomento a institutos de investigación
    if restricciones.institutos_activa and restricciones.min_institutos > 0:
        idx_institutos = [i for i in range(n) if tipo_entidad[i] == "INSTITUTO DE INVESTIGACIÓN"]
        modelo += pulp.lpSum(x[i] for i in idx_institutos) >= restricciones.min_institutos, "Min_institutos"

    # Equidad de género: Sum x(mujer) >= p * Sum x(todas)  <=>  Sum x(mujer) - p*Sum x(todas) >= 0
    if restricciones.genero_activa and restricciones.min_pct_mujeres > 0:
        idx_mujeres = [i for i in range(n) if sexo[i] == "FEMENINO"]
        p = restricciones.min_pct_mujeres
        modelo += (
            pulp.lpSum(x[i] for i in idx_mujeres) - p * pulp.lpSum(x[i] for i in range(n)) >= 0
        ), "Min_pct_mujeres"

    solver_cbc = pulp.PULP_CBC_CMD(msg=False)
    estado_solver = modelo.solve(solver_cbc)
    tiempo_seg = time.perf_counter() - t0

    estado_txt = pulp.LpStatus[estado_solver]

    if estado_txt != "Optimal":
        return ResultadoOptimizacion(
            estado="INFACTIBLE",
            tiempo_seg=tiempo_seg,
            mensaje=(
                "CBC no encontró una solución factible con esta combinación de presupuesto y restricciones "
                "(estado del solver: " + estado_txt + "). Revisa el diagnóstico de factibilidad."
            ),
        )

    seleccionados = [i for i in range(n) if pulp.value(x[i]) > 0.5]
    score_total = sum(scores[i] for i in seleccionados)
    costo_total = sum(costos[i] for i in seleccionados)

    return ResultadoOptimizacion(
        estado="OPTIMO",
        seleccionados=seleccionados,
        score_total=round(score_total, 1),
        costo_total=round(costo_total, 2),
        gap_pct=0.00,  # CBC resuelve este tamaño de problema hasta optimalidad certificada (gap 0)
        tiempo_seg=tiempo_seg,
        mensaje=f"Óptimo certificado: {len(seleccionados)} de {n} proyectos financiados.",
    )
