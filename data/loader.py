"""
Carga y limpieza del dataset oficial de PROCIENCIA.

Fuente: "Estadísticas de Proyectos de Investigación Científica por fuentes de
financiamiento de PROCIENCIA (2015-2021)", CONCYTEC, Plataforma Nacional de
Datos Abiertos del Perú.

Reglas de limpieza (Sección 3.2 del informe), aplicadas aquí a las 909 filas
completas -- no solo a una convocatoria -- porque el panel permite elegir
cualquiera de las 57 convocatorias y varias de ellas están total o
parcialmente en moneda extranjera (p. ej. ERANet-LAC, en euros).
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

RAW_CSV_PATH = os.path.join(os.path.dirname(__file__), "raw", "dataset_prociencia_original.csv")

# Tasas de cambio promedio referenciales 2015-2021 (Sección 3.2 del informe)
TASA_EUR_A_PEN = 4.15
TASA_GBP_A_PEN = 4.75

CATEGORICAL_COLUMNS = [
    "CONVENIO",
    "TIPO_SUBVENCION",
    "TIPO_CONVOCATORIA",
    "CONVOCATORIA",
    "ESQUEMA_FINANCIERO",
    "ENTIDAD_EJECUTORA_SUBVENCIONADO",
    "TIPO_ENTIDAD",
    "SEXO",
    "MONEDA",
    "DEPARTAMENTO",
    "PROVINCIA",
    "DISTRITO",
]


def _standardize_text(df: pd.DataFrame) -> pd.DataFrame:
    """Uniformiza mayúsculas y recorta espacios en columnas categóricas."""
    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df


def _normalize_currency(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte MONTO e IMPORTE_FONDECYT a soles (MONTO_SOLES / IMPORTE_FONDECYT_SOLES).

    873 registros ya estaban en soles, 23 en euros y 13 en libras esterlinas
    (Sección 3.2 del informe). Se conservan las columnas originales intactas
    y se agregan las versiones normalizadas.
    """
    tasa = df["MONEDA"].map({"S/.": 1.0, "EURO": TASA_EUR_A_PEN, "L.": TASA_GBP_A_PEN})
    tasa = tasa.fillna(1.0)  # cualquier código de moneda no previsto se asume ya en soles
    df["TASA_CAMBIO_APLICADA"] = tasa
    df["MONTO_SOLES"] = (df["MONTO"] * tasa).round(2)
    df["IMPORTE_FONDECYT_SOLES"] = (df["IMPORTE_FONDECYT"] * tasa).round(2)
    return df


@st.cache_data(show_spinner="Cargando y limpiando el dataset PROCIENCIA...")
def load_clean_dataset(path: str = RAW_CSV_PATH) -> pd.DataFrame:
    """Lee el CSV crudo (separador ';', BOM UTF-8) y aplica la limpieza completa."""
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    n_nulos = int(df.isnull().sum().sum())
    n_duplicados = int(df["CODIGO_ORDEN"].duplicated().sum())

    df = _standardize_text(df)
    df = _normalize_currency(df)

    df.attrs["n_filas_originales"] = len(df)
    df.attrs["n_nulos_originales"] = n_nulos
    df.attrs["n_duplicados_originales"] = n_duplicados
    return df


def es_universidad_nacional(nombre_entidad: str) -> bool:
    """Heurística usada en el informe para distinguir 'universidad nacional/pública'
    de 'universidad (otra)': el nombre oficial de toda universidad pública
    peruana contiene la palabra NACIONAL (p. ej. 'UNIVERSIDAD NACIONAL DE
    INGENIERIA'); las privadas no la usan ('UNIVERSIDAD DE PIURA', 'PONTIFICIA
    UNIVERSIDAD CATOLICA DEL PERU', 'UNIVERSIDAD PERUANA CAYETANO HEREDIA').
    """
    return "NACIONAL" in str(nombre_entidad).upper()
