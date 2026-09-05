"""
Resumen por convocatoria: universo de decisión seleccionable por el usuario.

Cada convocatoria define su propio presupuesto de referencia como la suma de
los montos (ya normalizados a soles) de TODOS sus proyectos -- no solo de la
muestra -- porque esa es la magnitud real de la demanda que PROCIENCIA
enfrentó en esa convocatoria.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from data.loader import es_universidad_nacional

MIN_PROYECTOS_RECOMENDADO = 5  # por debajo de esto, advertir sobre el tamaño de la convocatoria


@st.cache_data(show_spinner=False)
def resumen_convocatorias(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por convocatoria con las estadísticas necesarias para el selector
    y para el chequeo de factibilidad de las restricciones de equidad."""

    def _n_institutos(s: pd.Series) -> int:
        return int((s == "INSTITUTO DE INVESTIGACIÓN").sum())

    def _n_mujeres(s: pd.Series) -> int:
        return int((s == "FEMENINO").sum())

    g = (
        df.groupby("CONVOCATORIA")
        .agg(
            n_proyectos=("CODIGO_ORDEN", "count"),
            presupuesto_total_soles=("MONTO_SOLES", "sum"),
            anio=("ANIO", "first"),
            esquema_financiero=("ESQUEMA_FINANCIERO", "first"),
            n_institutos=("TIPO_ENTIDAD", _n_institutos),
            n_mujeres=("SEXO", _n_mujeres),
            n_entidades_unicas=("ENTIDAD_EJECUTORA_SUBVENCIONADO", "nunique"),
        )
        .reset_index()
        .sort_values("n_proyectos", ascending=False)
        .reset_index(drop=True)
    )

    g["presupuesto_total_soles"] = g["presupuesto_total_soles"].round(2)
    g["pct_mujeres"] = (100 * g["n_mujeres"] / g["n_proyectos"]).round(1)
    g["aviso_pocos_proyectos"] = g["n_proyectos"] < MIN_PROYECTOS_RECOMENDADO
    g["aviso_sin_institutos"] = g["n_institutos"] == 0
    return g


def universo_convocatoria(df: pd.DataFrame, convocatoria: str) -> pd.DataFrame:
    """Todos los proyectos (población completa) de una convocatoria."""
    return df[df["CONVOCATORIA"] == convocatoria].copy()


def etiqueta_convocatoria(fila: pd.Series) -> str:
    """Texto para el selectbox: nombre + tamaño + avisos si corresponde."""
    avisos = []
    if fila["aviso_pocos_proyectos"]:
        avisos.append("pocos proyectos")
    if fila["aviso_sin_institutos"]:
        avisos.append("sin institutos")
    sufijo = f"  ⚠ {', '.join(avisos)}" if avisos else ""
    return f"{fila['CONVOCATORIA']}  ·  {fila['anio']}  ·  {fila['n_proyectos']} proyectos{sufijo}"
