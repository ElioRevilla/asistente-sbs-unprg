from dataclasses import dataclass, field

from sbs_assistant.domain.value_objects.risk_category import RiskCategory


@dataclass(frozen=True, slots=True)
class ClienteTurnDTO:
    """Structured client narrative returned by the client agent."""

    narrative: str


@dataclass(frozen=True, slots=True)
class SupervisorTurnDTO:
    """Structured grounded challenge returned by the supervisor agent."""

    challenge: str
    objection_remaining: bool
    cited_articles: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BancoTurnDTO:
    """Structured pressure message returned by the bank agent."""

    pressure: str
    suggested_category: RiskCategory
