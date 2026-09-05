"""
Estado de sesión compartido entre las 6 páginas del panel.

Cada página de Streamlit corre como un script independiente en cada
interacción; lo que las mantiene coordinadas es `st.session_state` (los
parámetros que el usuario elige: convocatoria, tamaño de muestra, semilla,
presupuesto, restricciones) más `st.cache_data` (que evita releer o
reprocesar el CSV y la lista de convocatorias en cada rerun).

Los selectbox de convocatoria (el de esta barra lateral y el de la página
"Datos y contexto") usan `on_change` en vez de comparar-y-llamar `st.rerun()`
a mano: el callback actualiza `st.session_state["convocatoria"]` ANTES de
que Streamlit vuelva a ejecutar el script (todo widget disparra un rerun
automático al cambiar), así que el resto de la página ya ve el valor nuevo
en esa misma pasada -- sin depender de un segundo rerun manual que podía
quedar desincronizado entre los dos selectbox.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from data.caso_base import CODIGOS_CASO_BASE, PRESUPUESTO_CASO_BASE
from data.convocatorias import resumen_convocatorias, universo_convocatoria, etiqueta_convocatoria
from data.creditos import UNIVERSIDAD, MAESTRIA, CURSO, DOCENTE, GRUPO, INTEGRANTES
from data.loader import load_clean_dataset
from data.scoring import calcular_score
from data.sampling import muestra_estratificada, resumen_reduccion
from solvers.base import RestriccionesEquidad
from solvers.feasibility import chequear_factibilidad
from solvers.cbc_backend import resolver_portafolio

CONVOCATORIA_POR_DEFECTO_N = 190  # la convocatoria 2018-01 usada en el informe tiene 190 proyectos
N_MUESTRA_POR_DEFECTO = 30  # tamaño de muestra fijo del informe (30 proyectos)
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
    ss.setdefault("n_muestra", N_MUESTRA_POR_DEFECTO)
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
        n = min(int(st.session_state["n_muestra"]), len(universo))
        muestra = muestra_estratificada(universo, n, st.session_state["semilla"])
    return calcular_score(muestra)


def activar_caso_base(resumen: pd.DataFrame) -> None:
    """Fuerza la convocatoria, la muestra (los 30 códigos exactos del Anexo A),
    el presupuesto y las restricciones al caso base del informe, para que el
    panel reproduzca bit a bit su resultado publicado (score 1171.7, 14
    proyectos). Útil para validar que el modelo es correcto antes de explorar
    otras convocatorias, muestras o restricciones."""
    st.session_state["modo_caso_base"] = True
    st.session_state["convocatoria"] = _default_convocatoria(resumen)
    st.session_state["n_muestra"] = N_MUESTRA_POR_DEFECTO
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


def _aplicar_seleccion_sidebar() -> None:
    st.session_state["convocatoria"] = st.session_state["selector_convocatoria_sidebar"]


def sidebar_contexto(df: pd.DataFrame, resumen: pd.DataFrame) -> None:
    """Bloque de contexto visible en toda página: convocatoria activa + atajo
    para cambiarla sin tener que volver a la página 02."""
    ensure_defaults(resumen)
    with st.sidebar:
        st.caption("CONVOCATORIA ACTIVA")
        opciones = resumen["CONVOCATORIA"].tolist()
        etiquetas = {row["CONVOCATORIA"]: etiqueta_convocatoria(row) for _, row in resumen.iterrows()}
        # Sincroniza el widget con la "fuente de verdad" (session_state["convocatoria"])
        # en CADA rerun, antes de crearlo -- así reacciona también a cambios hechos
        # desde el selector de la página "Datos y contexto", el modo validación, o
        # el botón "Salir" del panel de decisión, sin depender de un rerun manual.
        st.session_state["selector_convocatoria_sidebar"] = st.session_state["convocatoria"]
        st.selectbox(
            "Convocatoria",
            opciones,
            format_func=lambda c: etiquetas[c],
            label_visibility="collapsed",
            key="selector_convocatoria_sidebar",
            on_change=_aplicar_seleccion_sidebar,
        )

        universo = get_universo(df)
        muestra = get_muestra_scored(universo)
        red = resumen_reduccion(len(df), len(universo), len(muestra))
        st.caption(
            f"{red['dataset_completo']} → {red['convocatoria']} ({red['pct_convocatoria']}%) → "
            f"{red['muestra']} en la muestra ({red['pct_muestra_de_convocatoria']}%)"
        )
        st.divider()

        _integrantes_html = "".join(f"<li>{nombre}</li>" for nombre in INTEGRANTES)
        st.markdown(
            f"""
            <div style="
                background-color:#FBE7D2;
                border:1px solid #EFC08A;
                border-radius:10px;
                padding:14px 16px;
                text-align:center;
                color:#5A3B1E;
                line-height:1.35;
            ">
                <div style="font-weight:700; font-size:0.95rem; color:#C06A1B;">{UNIVERSIDAD}</div>
                <div style="font-size:0.82rem; margin-top:4px;">{MAESTRIA}</div>
                <div style="font-size:0.82rem;">Curso: {CURSO}</div>
                <div style="font-size:0.82rem; margin-top:8px;">Docente: {DOCENTE}</div>
                <div style="font-weight:700; font-size:0.85rem; margin-top:8px;">{GRUPO}</div>
                <div style="font-size:0.82rem; font-weight:600; margin-top:6px;">Autores</div>
                <ul style="
                    display:inline-block;
                    text-align:left;
                    margin:2px auto 0;
                    padding-left:20px;
                    font-size:0.8rem;
                ">
                    {_integrantes_html}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
