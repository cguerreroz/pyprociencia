"""
Caso base del informe académico: los 30 proyectos exactos del Anexo A,
sobre la convocatoria "Proyecto de Investigación Aplicada y Desarrollo
Tecnológico 2018-01" (190 proyectos), presupuesto S/ 3,600,000, y las
restricciones originales del informe (diversidad institucional y fomento a
institutos).

Este NO es el resultado de correr `muestra_estratificada()`: el informe
nunca publicó el código exacto de su muestreo aleatorio estratificado
(ni el orden de los estratos, ni el método de redondeo de la asignación
proporcional), así que dos implementaciones distintas de "estratificado,
semilla=42" pueden -- y en la práctica lo hacen -- producir 30 proyectos
distintos. Por eso esta lista se declara explícitamente en vez de
regenerarse: es la única forma de reproducir bit a bit el resultado
publicado (score 1171.7, 14 proyectos, costo S/ 3,563,522.87).
"""

from __future__ import annotations

PRESUPUESTO_CASO_BASE = 3_600_000.0

CODIGOS_CASO_BASE = [
    "02589-2018", "02621-2018", "02630-2018", "02639-2018", "02642-2018",
    "02654-2018", "02656-2018", "02666-2018", "02676-2018", "02678-2018",
    "02724-2018", "02732-2018", "02754-2018", "02774-2018", "02794-2018",
    "02818-2018", "02832-2018", "02842-2018", "02868-2018", "02886-2018",
    "02906-2018", "02908-2018", "02910-2018", "02914-2018", "02918-2018",
    "02920-2018", "02942-2018", "02944-2018", "02958-2018", "02970-2018",
]

# Resultado esperado, para que la página de metodología pueda mostrar
# "obtenido en este panel" junto a "publicado en el informe" y compararlos.
RESULTADO_ESPERADO = {
    "score_total": 1171.7,
    "n_proyectos": 14,
    "costo_total": 3_563_522.87,
}
