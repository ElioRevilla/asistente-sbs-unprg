from enum import StrEnum


class PedagogicalMode(StrEnum):
    """Pedagogical interaction modes supported by the product vision."""

    EXPLICAME = "explicame"
    EJEMPLIFICA = "ejemplifica"
    COMPARA = "compara"
    EVALUAME = "evaluame"
    APLICA = "aplica"
    AUTOMATICO = "automatico"
