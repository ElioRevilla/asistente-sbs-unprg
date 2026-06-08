from enum import StrEnum


class AgentRole(StrEnum):
    """Diegetic agent roles used inside the adversarial debate."""

    CLIENTE = "cliente"
    SUPERVISOR = "supervisor"
    BANCO = "banco"
