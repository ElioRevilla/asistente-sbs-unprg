from enum import StrEnum


class RiskCategory(StrEnum):
    """Ordered SBS risk categories for adversarial simulations."""

    NORMAL = "Normal"
    CPP = "CPP"
    DEFICIENTE = "Deficiente"
    DUDOSO = "Dudoso"
    PERDIDA = "Pérdida"

    @property
    def order(self) -> int:
        """Return the regulatory risk order from lower to higher provision."""
        return _RISK_CATEGORY_ORDER[self]

    def is_higher_than(self, other: "RiskCategory") -> bool:
        """Return whether this category implies a higher risk order."""
        return self.order > other.order

    def is_lower_than(self, other: "RiskCategory") -> bool:
        """Return whether this category implies a lower risk order."""
        return self.order < other.order


_RISK_CATEGORY_ORDER: dict[RiskCategory, int] = {
    RiskCategory.NORMAL: 0,
    RiskCategory.CPP: 1,
    RiskCategory.DEFICIENTE: 2,
    RiskCategory.DUDOSO: 3,
    RiskCategory.PERDIDA: 4,
}
