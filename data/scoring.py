"""
Score de priorización -- EXACTAMENTE como lo define la Sección 3.3 y la Tabla B
del informe "Selección de Proyectos de Investigación PROCIENCIA bajo
Restricción Presupuestal". Es un elemento declarado SIMULADO por el equipo
(no un criterio oficial de PROCIENCIA), pero su cálculo es fijo: no expone
pesos ni categorías ajustables en la interfaz.

    Score = 100 * (0.40 * EntidadScore + 0.35 * DiversidadScore + 0.25 * GeneroScore)

Los pesos (0.40 / 0.35 / 0.25) y los tres sub-scores fueron verificados por
ingeniería inversa contra los 30 proyectos y sus scores publicados en el
Anexo A del informe -- incluida la distinción "universidad nacional/pública"
(0.90) vs. "universidad (otra)" (0.70), que el dataset no marca de forma
explícita y que el informe resuelve por el nombre de la entidad (toda
universidad pública peruana incluye la palabra NACIONAL en su denominación
oficial).
"""

from __future__ import annotations

import pandas as pd

from data.loader import es_universidad_nacional

PESO_ENTIDAD = 0.40
PESO_DIVERSIDAD = 0.35
PESO_GENERO = 0.25

ENTIDAD_SCORE_INSTITUTO = 1.00
ENTIDAD_SCORE_UNIV_NACIONAL = 0.90
ENTIDAD_SCORE_UNIV_OTRA = 0.70
ENTIDAD_SCORE_OTRO = 0.50

GENERO_SCORE_MUJER = 1.00
GENERO_SCORE_HOMBRE = 0.60


def _entidad_score_fila(tipo_entidad: str, nombre_entidad: str) -> float:
    tipo = str(tipo_entidad).upper()
    if tipo == "INSTITUTO DE INVESTIGACIÓN":
        return ENTIDAD_SCORE_INSTITUTO
    if tipo == "UNIVERSIDAD":
        return ENTIDAD_SCORE_UNIV_NACIONAL if es_universidad_nacional(nombre_entidad) else ENTIDAD_SCORE_UNIV_OTRA
    return ENTIDAD_SCORE_OTRO


def calcular_score(muestra: pd.DataFrame) -> pd.DataFrame:
    """Agrega EntidadScore, DiversidadScore, GeneroScore y SCORE a la muestra
    dada. La diversidad se calcula SIEMPRE sobre la composición de la muestra
    actual (1 / n° de propuestas de esa entidad dentro de la muestra), tal
    como en el informe -- por eso este cálculo se rehace cada vez que cambia
    el universo (convocatoria) o el tamaño de muestra.
    """
    df = muestra.copy()

    df["ENTIDAD_SCORE"] = [
        _entidad_score_fila(t, e)
        for t, e in zip(df["TIPO_ENTIDAD"], df["ENTIDAD_EJECUTORA_SUBVENCIONADO"])
    ]

    frecuencia_entidad = df["ENTIDAD_EJECUTORA_SUBVENCIONADO"].map(df["ENTIDAD_EJECUTORA_SUBVENCIONADO"].value_counts())
    df["DIVERSIDAD_SCORE"] = (1.0 / frecuencia_entidad).round(4)

    df["GENERO_SCORE"] = df["SEXO"].map({"FEMENINO": GENERO_SCORE_MUJER, "MASCULINO": GENERO_SCORE_HOMBRE}).fillna(
        GENERO_SCORE_HOMBRE
    )

    df["SCORE"] = (
        100
        * (
            PESO_ENTIDAD * df["ENTIDAD_SCORE"]
            + PESO_DIVERSIDAD * df["DIVERSIDAD_SCORE"]
            + PESO_GENERO * df["GENERO_SCORE"]
        )
    ).round(1)

    return df


TABLA_B = pd.DataFrame(
    [
        ("EntidadScore", "Instituto de investigación", ENTIDAD_SCORE_INSTITUTO),
        ("EntidadScore", "Universidad nacional / pública", ENTIDAD_SCORE_UNIV_NACIONAL),
        ("EntidadScore", "Universidad (otra)", ENTIDAD_SCORE_UNIV_OTRA),
        ("EntidadScore", "Empresa, ONG, organización u otro", ENTIDAD_SCORE_OTRO),
        ("DiversidadScore", "Inverso de la frecuencia de la entidad en la muestra", None),
        ("GeneroScore", "Investigador principal mujer", GENERO_SCORE_MUJER),
        ("GeneroScore", "Investigador principal hombre", GENERO_SCORE_HOMBRE),
    ],
    columns=["Criterio", "Categoría", "Valor asignado"],
)
