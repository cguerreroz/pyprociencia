"""
Heurística Greedy de referencia (Sección 4.4 del informe): ordena los
proyectos por razón score/costo y financia mientras el presupuesto lo
permita. Se evalúa solo bajo la restricción de presupuesto (sin las
restricciones de equidad), para aislar la comparación de calidad del método
de solución frente al modelo completo -- exactamente como en el informe.
"""

from __future__ import annotations

from typing import Sequence

from solvers.base import ResultadoOptimizacion


def resolver_greedy(costos: Sequence[float], scores: Sequence[float], presupuesto: float) -> ResultadoOptimizacion:
    n = len(costos)
    orden = sorted(range(n), key=lambda i: (scores[i] / costos[i]) if costos[i] > 0 else 0, reverse=True)

    seleccionados = []
    costo_acum = 0.0
    for i in orden:
        if costo_acum + costos[i] <= presupuesto:
            seleccionados.append(i)
            costo_acum += costos[i]

    score_total = sum(scores[i] for i in seleccionados)
    return ResultadoOptimizacion(
        estado="OPTIMO" if seleccionados else "SIN_PROYECTOS",
        seleccionados=seleccionados,
        score_total=round(score_total, 1),
        costo_total=round(costo_acum, 2),
        gap_pct=float("nan"),  # una heurística no certifica optimalidad
        mensaje="Heurística Greedy (razón score/costo) — no garantiza el óptimo.",
    )
