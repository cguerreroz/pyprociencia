"""
Chequeo de factibilidad ANTES de llamar al solver. La idea es nunca dejar que
el usuario se tope con un "Infeasible" críptico del solver: se valida cada
restricción dura contra lo que realmente hay disponible en la muestra
seleccionada y se devuelve un diagnóstico legible, con qué relajar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from solvers.base import RestriccionesEquidad


@dataclass
class DiagnosticoFactibilidad:
    factible: bool
    problemas: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        if self.factible:
            return "El problema es factible con la configuración actual."
        return " · ".join(self.problemas)


def chequear_factibilidad(muestra: pd.DataFrame, restricciones: RestriccionesEquidad) -> DiagnosticoFactibilidad:
    problemas: list[str] = []
    n = len(muestra)

    if n == 0:
        return DiagnosticoFactibilidad(False, ["La muestra actual no tiene proyectos. Aumenta el número de proyectos de la muestra o cambia de convocatoria."])

    if restricciones.institutos_activa:
        n_institutos = int((muestra["TIPO_ENTIDAD"] == "INSTITUTO DE INVESTIGACIÓN").sum())
        if restricciones.min_institutos > n_institutos:
            problemas.append(
                f"Pediste un mínimo de {restricciones.min_institutos} institutos financiados, pero la muestra "
                f"solo tiene {n_institutos} proyectos de institutos de investigación. Reduce el mínimo a {n_institutos} "
                "o menos, aumenta el número de proyectos de la muestra, o elige otra convocatoria."
            )

    if restricciones.diversidad_activa and restricciones.max_por_entidad < 1:
        problemas.append("El máximo de proyectos por entidad debe ser al menos 1.")

    return DiagnosticoFactibilidad(factible=len(problemas) == 0, problemas=problemas)
