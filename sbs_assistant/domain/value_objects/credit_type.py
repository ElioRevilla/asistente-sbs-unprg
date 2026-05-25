from enum import StrEnum


class CreditType(StrEnum):
    """Credit types handled by the SBS regulation."""

    CONSUMO = "consumo"
    HIPOTECARIO = "hipotecario"
    MES = "MES"
    CORPORATIVO = "corporativo"
    GRAN_EMPRESA = "gran_empresa"
    MEDIANA_EMPRESA = "mediana_empresa"
    PEQUENA_EMPRESA = "pequena_empresa"
