from enum import StrEnum


class Category(StrEnum):
    """Regulatory debtor categories."""

    NORMAL = "Normal"
    CPP = "CPP"
    DEFICIENTE = "Deficiente"
    DUDOSO = "Dudoso"
    PERDIDA = "Pérdida"
