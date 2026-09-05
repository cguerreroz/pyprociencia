"""
Interfaz común del solver. Un único backend implementa esto en este proyecto
(CBC vía PuLP, ver cbc_backend.py) -- no hay Gurobi ni ningún otro motor en
el panel desplegado. Mantener esta interfaz separada de Streamlit permite
probar el modelo con pytest sin levantar la app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class RestriccionesEquidad:
    diversidad_activa: bool = True
    max_por_entidad: int = 1

    institutos_activa: bool = True
    min_institutos: int = 2


@dataclass
class ResultadoOptimizacion:
    estado: str  # "OPTIMO", "INFACTIBLE", "SIN_PROYECTOS"
    seleccionados: list[int] = field(default_factory=list)  # posiciones (0-based) dentro de la muestra
    score_total: float = 0.0
    costo_total: float = 0.0
    gap_pct: float = 0.0
    tiempo_seg: float = 0.0
    mensaje: str = ""


def construir_grupos_entidad_repetida(entidades: Sequence[str]) -> dict[str, list[int]]:
    """Índices (0-based) agrupados por entidad, solo para entidades con >= 2
    propuestas en la muestra actual -- la restricción de diversidad institucional
    solo aplica a esas."""
    grupos: dict[str, list[int]] = {}
    for i, e in enumerate(entidades):
        grupos.setdefault(e, []).append(i)
    return {e: idxs for e, idxs in grupos.items() if len(idxs) >= 2}
