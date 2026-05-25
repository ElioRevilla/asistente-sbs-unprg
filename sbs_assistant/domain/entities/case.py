from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType
from sbs_assistant.domain.value_objects.pedagogical_mode import PedagogicalMode


@dataclass(frozen=True, slots=True)
class SyntheticCase:
    """Synthetic debtor case generated for pedagogical exercises."""

    id: UUID | None
    credit_type: CreditType
    description: dict[str, object]
    correct_category: Category | None
    correct_provision: Decimal | None
    source_article: str | None
    mode: PedagogicalMode
