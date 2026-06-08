from typing import Protocol

from sbs_assistant.domain.entities.operation_case import OperationCase


class CaseSelectorPort(Protocol):
    """Port for deterministic selection of adversarial simulation cases."""

    async def next_case(
        self,
        user_id: str,
        focus: str | None = None,
    ) -> OperationCase:
        """Return the next operation case with its hidden ground truth."""
