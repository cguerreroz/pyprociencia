"""
Muestreo aleatorio estratificado por tipo de entidad, con un tamaño de
muestra fijo (número de proyectos, ajustable por el usuario) y una semilla
también ajustable (Sección 3.2 del informe generaliza aquí los 30 proyectos
fijos usados originalmente sobre la convocatoria 2018-01).
"""

from __future__ import annotations

import pandas as pd


def muestra_estratificada(df_convocatoria: pd.DataFrame, n: int, semilla: int) -> pd.DataFrame:
    """Devuelve una muestra de exactamente `n` proyectos (o todos los
    disponibles si `n` es mayor o igual al tamaño de la convocatoria),
    conservando la proporción real de cada TIPO_ENTIDAD.

    La asignación por estrato usa el método del mayor residuo: primero se
    reparte `n` proporcionalmente al tamaño de cada estrato (parte entera),
    y el remanente se asigna, de a uno, a los estratos con mayor residuo
    fraccionario -- así el total siempre suma exactamente `n` sin sesgar
    sistemáticamente al mismo estrato como haría "el último estrato absorbe
    el redondeo".
    """
    n_total = len(df_convocatoria)
    n_objetivo = max(1, int(n))

    if n_objetivo >= n_total:
        return df_convocatoria.sort_values("CODIGO_ORDEN").reset_index(drop=True)

    estratos = list(df_convocatoria.groupby("TIPO_ENTIDAD"))
    tamanos = [len(grupo) for _, grupo in estratos]

    cuotas_exactas = [n_objetivo * t / n_total for t in tamanos]
    asignacion = [min(tamanos[i], int(cuotas_exactas[i])) for i in range(len(estratos))]
    restante = n_objetivo - sum(asignacion)

    # Reparte el remanente a los estratos con mayor residuo fraccionario
    # (y que todavía tengan proyectos disponibles), uno por uno.
    residuos = sorted(
        range(len(estratos)),
        key=lambda i: cuotas_exactas[i] - int(cuotas_exactas[i]),
        reverse=True,
    )
    idx = 0
    while restante > 0 and any(asignacion[i] < tamanos[i] for i in range(len(estratos))):
        i = residuos[idx % len(residuos)]
        if asignacion[i] < tamanos[i]:
            asignacion[i] += 1
            restante -= 1
        idx += 1

    partes = []
    for (_, grupo), n_estrato in zip(estratos, asignacion):
        if n_estrato > 0:
            partes.append(grupo.sample(n=n_estrato, random_state=semilla))

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
