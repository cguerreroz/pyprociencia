"""
Estado de sesión compartido entre las 6 páginas del panel.

Cada página de Streamlit corre como un script independiente en cada
interacción; lo que las mantiene coordinadas es `st.session_state` (los
parámetros que el usuario elige: convocatoria, % de muestra, semilla,
presupuesto, restricciones) más `st.cache_data` (que evita releer o
reprocesar el CSV y la lista de convocatorias en cada rerun).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from data.caso_base import CODIGOS_CASO_BASE, PRESUPUESTO_CASO_BASE
from data.convocatorias import resumen_convocatorias, universo_convocatoria, etiqueta_convocatoria
from data.loader import load_clean_dataset
from data.scoring import calcular_score
from data.sampling import muestra_estratificada, resumen_reduccion
from solvers.base import RestriccionesEquidad
from solvers.feasibility import chequear_factibilidad
from solvers.cbc_backend import resolver_portafolio

CONVOCATORIA_POR_DEFECTO_N = 190  # la convocatoria 2018-01 usada en el informe tiene 190 proyectos
PCT_MUESTRA_POR_DEFECTO = 30 / 190  # 15.8%, el tamaño de muestra del informe
SEMILLA_POR_DEFECTO = 42
PCT_PRESUPUESTO_POR_DEFECTO = 0.40


def get_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_clean_dataset()
    resumen = resumen_convocatorias(df)
    return df, resumen


def _default_convocatoria(resumen: pd.DataFrame) -> str:
    coincidencia = resumen[resumen["n_proyectos"] == CONVOCATORIA_POR_DEFECTO_N]
    if len(coincidencia):
        return coincidencia.iloc[0]["CONVOCATORIA"]
    return resumen.iloc[0]["CONVOCATORIA"]


def ensure_defaults(resumen: pd.DataFrame) -> None:
    ss = st.session_state
    ss.setdefault("convocatoria", _default_convocatoria(resumen))
    ss.setdefault("pct_muestra", PCT_MUESTRA_POR_DEFECTO)
    ss.setdefault("semilla", SEMILLA_POR_DEFECTO)
    ss.setdefault("pct_presupuesto", PCT_PRESUPUESTO_POR_DEFECTO)
    ss.setdefault("presupuesto_manual", None)  # si el usuario escribe un monto exacto, sobreescribe el %
    ss.setdefault("modo_caso_base", False)  # ver activar_caso_base() / desactivar_caso_base()
    ss.setdefault(
        "restricciones",
        RestriccionesEquidad(
            diversidad_activa=True,
            max_por_entidad=1,
            institutos_activa=True,
            min_institutos=2,
            # Apagada por defecto: es una restricción NUEVA que el informe original no tenía.
            # Actívala desde el Panel de decisión cuando quieras explorarla -- pero entonces
            # los resultados dejarán de coincidir con el informe, por diseño.
            genero_activa=False,
            min_pct_mujeres=0.30,
        ),
    )


def get_universo(df: pd.DataFrame) -> pd.DataFrame:
    return universo_convocatoria(df, st.session_state["convocatoria"])


def get_muestra_scored(universo: pd.DataFrame) -> pd.DataFrame:
    if st.session_state.get("modo_caso_base"):
        muestra = universo[universo["CODIGO_ORDEN"].isin(CODIGOS_CASO_BASE)].copy()
        muestra = muestra.sort_values("CODIGO_ORDEN").reset_index(drop=True)
    else:
        muestra = muestra_estratificada(universo, st.session_state["pct_muestra"], st.session_state["semilla"])
    return calcular_score(muestra)


def activar_caso_base(resumen: pd.DataFrame) -> None:
    """Fuerza la convocatoria, la muestra (los 30 códigos exactos del Anexo A),
    el presupuesto y las restricciones al caso base del informe, para que el
    panel reproduzca bit a bit su resultado publicado (score 1171.7, 14
    proyectos). Útil para validar que el modelo es correcto antes de explorar
    otras convocatorias, muestras o restricciones."""
    st.session_state["modo_caso_base"] = True
    st.session_state["convocatoria"] = _default_convocatoria(resumen)
    st.session_state["presupuesto_manual"] = PRESUPUESTO_CASO_BASE
    st.session_state["restricciones"] = RestriccionesEquidad(
        diversidad_activa=True, max_por_entidad=1,
        institutos_activa=True, min_institutos=2,
        genero_activa=False, min_pct_mujeres=0.0,
    )


def desactivar_caso_base() -> None:
    st.session_state["modo_caso_base"] = False
    st.session_state["presupuesto_manual"] = None


def presupuesto_actual(universo: pd.DataFrame) -> float:
    if st.session_state.get("presupuesto_manual"):
        return float(st.session_state["presupuesto_manual"])
    total_convocatoria = float(universo["MONTO_SOLES"].sum())
    return round(total_convocatoria * st.session_state["pct_presupuesto"], 2)


def diagnostico_y_resultado(muestra_scored: pd.DataFrame, presupuesto: float):
    restricciones = st.session_state["restricciones"]
    diag = chequear_factibilidad(muestra_scored, restricciones)
    if not diag.factible:
        return diag, None
    resultado = resolver_portafolio(
        costos=muestra_scored["MONTO_SOLES"].tolist(),
        scores=muestra_scored["SCORE"].tolist(),
        presupuesto=presupuesto,
        entidades=muestra_scored["ENTIDAD_EJECUTORA_SUBVENCIONADO"].tolist(),
        tipo_entidad=muestra_scored["TIPO_ENTIDAD"].tolist(),
        sexo=muestra_scored["SEXO"].tolist(),
        restricciones=restricciones,
    )
    return diag, resultado


def sidebar_contexto(df: pd.DataFrame, resumen: pd.DataFrame) -> None:
    """Bloque de contexto visible en toda página: convocatoria activa + atajo
    para cambiarla sin tener que volver a la página 02."""
    ensure_defaults(resumen)
    with st.sidebar:
        st.caption("CONVOCATORIA ACTIVA")
        opciones = resumen["CONVOCATORIA"].tolist()
        etiquetas = {row["CONVOCATORIA"]: etiqueta_convocatoria(row) for _, row in resumen.iterrows()}
        seleccion = st.selectbox(
            "Convocatoria",
            opciones,
            index=opciones.index(st.session_state["convocatoria"]),
            format_func=lambda c: etiquetas[c],
            label_visibility="collapsed",
            key="selector_convocatoria_sidebar",
        )
        if seleccion != st.session_state["convocatoria"]:
            st.session_state["convocatoria"] = seleccion
            st.rerun()

        universo = get_universo(df)
        muestra = get_muestra_scored(universo)
        red = resumen_reduccion(len(df), len(universo), len(muestra))
        st.caption(
            f"{red['dataset_completo']} → {red['convocatoria']} ({red['pct_convocatoria']}%) → "
            f"{red['muestra']} en la muestra ({red['pct_muestra_de_convocatoria']}%)"
        )
        st.divider()
