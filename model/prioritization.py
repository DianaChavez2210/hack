"""
Módulo de Clasificación de Prioridad Clínica Determinista.
Mapea el risk_score calibrado continuo en [0.0, 1.0] a niveles de prioridad oficial.
"""


def classify_priority(risk_score: float) -> str:
    """
    Retorna el nivel de prioridad clínica determinista según la especificación oficial:
      - CRITICAL: >= 0.80
      - HIGH:     [0.60, 0.80)
      - MEDIUM:   [0.35, 0.60)
      - LOW:      < 0.35
    """
    score = float(risk_score) if risk_score is not None else 0.0

    if score >= 0.80:
        return "CRITICAL"
    elif score >= 0.60:
        return "HIGH"
    elif score >= 0.35:
        return "MEDIUM"
    else:
        return "LOW"
