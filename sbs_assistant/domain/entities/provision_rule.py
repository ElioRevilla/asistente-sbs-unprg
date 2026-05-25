from dataclasses import dataclass
from decimal import Decimal

from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType


@dataclass(frozen=True, slots=True)
class ProvisionRule:
    """Structured provisioning rule extracted from the regulation."""

    category: Category
    credit_type: CreditType
    guarantee_type: str | None
    provision_percentage: Decimal
    source_article: str
