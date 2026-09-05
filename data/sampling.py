"""
Muestreo aleatorio estratificado por tipo de entidad, con tamaño y semilla
ajustables por el usuario (Sección 3.2 del informe generaliza aquí el 15.8%
fijo usado originalmente sobre la convocatoria 2018-01).
"""

from __future__ import annotations

import math

import pandas as pd


def muestra_estratificada(df_convocatoria: pd.DataFrame, pct: float, semilla: int) -> pd.DataFrame:
    """Devuelve una muestra de aproximadamente `pct` (0-1) de los proyectos de la
    convocatoria, conservando la proporción real de cada TIPO_ENTIDAD.

    Si `pct` cubre el 100% (o el resultado del redondeo por estrato iguala al
    total), se devuelve la convocatoria completa sin aleatoriedad de por medio.
    """
    pct = max(0.0, min(1.0, pct))
    n_total = len(df_convocatoria)
    n_objetivo = max(1, round(n_total * pct))

    if n_objetivo >= n_total:
        return df_convocatoria.copy()

    partes = []
    restante = n_objetivo
    estratos = list(df_convocatoria.groupby("TIPO_ENTIDAD"))
    for i, (_, grupo) in enumerate(estratos):
        es_ultimo = i == len(estratos) - 1
        if es_ultimo:
            n_estrato = restante
        else:
            n_estrato = min(len(grupo), max(0, round(len(grupo) * pct)))
        n_estrato = min(n_estrato, len(grupo), restante)
        if n_estrato > 0:
            partes.append(grupo.sample(n=n_estrato, random_state=semilla))
        restante -= n_estrato

    muestra = pd.concat(partes) if partes else df_convocatoria.iloc[0:0]
    return muestra.sort_values("CODIGO_ORDEN").reset_index(drop=True)


def resumen_reduccion(n_total_dataset: int, n_convocatoria: int, n_muestra: int) -> dict:
    """Cifras del embudo 909 -> convocatoria -> muestra, para el gráfico de la página 02."""
    return {
        "dataset_completo": n_total_dataset,
        "convocatoria": n_convocatoria,
        "pct_convocatoria": round(100 * n_convocatoria / n_total_dataset, 1) if n_total_dataset else 0.0,
        "muestra": n_muestra,
        "pct_muestra_de_convocatoria": round(100 * n_muestra / n_convocatoria, 1) if n_convocatoria else 0.0,
    }
