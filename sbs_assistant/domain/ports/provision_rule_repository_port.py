from typing import Protocol

from sbs_assistant.domain.entities.provision_rule import ProvisionRule


class ProvisionRuleRepositoryPort(Protocol):
    """Persistence port for structured provisioning rules."""

    async def replace_all(self, rules: list[ProvisionRule]) -> None:
        """Replace current provisioning rules with the provided rules."""

    async def find_percentage(
        self,
        category: str,
        credit_type: str,
        guarantee_type: str,
    ) -> ProvisionRule | None:
        """Find a provision percentage rule for category, credit and guarantee."""
