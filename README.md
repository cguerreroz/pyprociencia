# Mochila con Equidad — Panel PROCIENCIA

Panel prescriptivo en Streamlit para el caso "Selección de Proyectos de Investigación PROCIENCIA bajo Restricción Presupuestal" (Maestría en Ciencia de Datos, Modelos Prescriptivos y Optimización).

Resuelve un problema de programación entera binaria (variante del *0-1 knapsack* con restricciones adicionales) con **CBC vía PuLP** — código abierto, sin licencia, no usa Gurobi en ningún punto del despliegue.

## Qué permite hacer

- Elegir cualquiera de las **57 convocatorias** del dataset oficial de CONCYTEC (2015–2021), no solo la de 2018-01 usada en el informe original.
- Ajustar el **% de la convocatoria** a incluir en el análisis (muestreo aleatorio estratificado por tipo de entidad) y la semilla.
- Ajustar el **presupuesto** como % del total solicitado por la convocatoria elegida (40% por defecto) o como monto exacto.
- Encender/apagar y parametrizar las **tres restricciones de equidad**: diversidad institucional (máx. proyectos por entidad), fomento a institutos de investigación (mínimo) y equidad de género (mínimo % de financiados liderados por mujeres).
- Ver el **portafolio óptimo**, exportarlo a CSV/Excel, comparar escenarios (con/sin restricciones, heurística Greedy) y correr un barrido de sensibilidad sobre el presupuesto.

El score de priorización (Sección 3.3 del informe, Tabla B) es **fijo** — no expone pesos editables — y fue verificado por ingeniería inversa contra los 30 proyectos y sus scores publicados en el Anexo A del informe: con la convocatoria 2018-01, esos mismos 30 proyectos, presupuesto S/ 3,600,000 y las restricciones originales (sin equidad de género), el panel reproduce exactamente el resultado del informe: **score 1171.7, 14 proyectos financiados, costo S/ 3,563,522.87**.

## Estructura del proyecto

```
panel_prociencia/
├── app.py                      # st.navigation() — registra las 6 páginas
├── pages/
│   ├── 1_resumen.py
│   ├── 2_datos_contexto.py     # selector de convocatoria + % de muestra
│   ├── 3_modelo.py
│   ├── 4_panel_decision.py     # núcleo prescriptivo
│   ├── 5_sensibilidad.py
│   └── 6_metodologia.py
├── core.py                     # estado de sesión compartido entre páginas
├── data/
│   ├── loader.py                # lee el CSV, normaliza moneda (EUR/GBP → soles), cachea
│   ├── convocatorias.py           # resumen por convocatoria (N, presupuesto total, institutos, mujeres)
│   ├── sampling.py                 # muestreo estratificado, % y semilla ajustables
│   ├── scoring.py                   # Score = 100·(0.40·Entidad + 0.35·Diversidad + 0.25·Género) — fijo
│   └── raw/dataset_prociencia_original.csv
├── solvers/
│   ├── base.py                       # interfaz y estructuras de datos
│   ├── cbc_backend.py                 # único motor: PuLP + CBC
│   ├── greedy.py                       # heurística de referencia (Sección 4.4 del informe)
│   └── feasibility.py                   # chequeo previo de factibilidad
├── requirements.txt
└── .streamlit/config.toml
```

## Correrlo en tu máquina

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`.

## Subirlo a GitHub

```bash
git init
git add .
git commit -m "Panel prescriptivo PROCIENCIA"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/<tu-repo>.git
git push -u origin main
```

(Crea antes el repositorio vacío en GitHub, o usa `gh repo create <tu-repo> --public --source=. --remote=origin` si tienes la CLI de GitHub instalada.)

## Desplegarlo en Streamlit Community Cloud

1. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de GitHub.
2. **New app** → elige el repositorio y la rama (`main`).
3. **Main file path:** `app.py`.
4. Deploy. No hace falta configurar ningún secreto ni licencia — todo el proyecto corre con `requirements.txt` tal cual.

No hay archivo `secrets.toml` que gestionar: al no usar Gurobi, no existen credenciales de licencia (WLS) que proteger.

## Validado contra el caso base del informe

`data/scoring.py` reproduce exactamente el score de cada uno de los 30 proyectos del Anexo A, y `solvers/cbc_backend.py` reproduce exactamente la solución óptima del informe (14 proyectos, score 1171.7, costo S/ 3,563,522.87) cuando se fija manualmente el presupuesto en S/ 3,600,000 sobre esos mismos 30 proyectos y se desactiva la restricción de género (no existía en el modelo original). El % de muestra y la convocatoria configurables son una capacidad nueva de este panel: al generar una muestra distinta a la del informe (tamaño, semilla o convocatoria distintos), los resultados cambian en consecuencia — es el comportamiento esperado de una herramienta prescriptiva interactiva, no un error.
