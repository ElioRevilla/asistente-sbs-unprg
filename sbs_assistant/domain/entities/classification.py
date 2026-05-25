from dataclasses import dataclass
from decimal import Decimal

from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Deterministic classification and provisioning result."""

    category: Category
    credit_type: CreditType
    guarantee_type: str | None
    provision_percentage: Decimal
    provision_amount: Decimal
    source_article: str
