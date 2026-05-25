from dataclasses import dataclass, field

from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.provision_rule import ProvisionRule


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Structured output produced by a document parser."""

    chunks: list[Chunk] = field(default_factory=list)
    provision_rules: list[ProvisionRule] = field(default_factory=list)
