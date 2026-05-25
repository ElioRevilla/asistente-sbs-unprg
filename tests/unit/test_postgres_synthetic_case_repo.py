import json

from sbs_assistant.infrastructure.persistence.postgres_synthetic_case_repo import (
    PostgresSyntheticCaseRepository,
)


def test_description_parses_jsonb_string() -> None:
    repository = PostgresSyntheticCaseRepository(pool=None)

    description = repository._description(json.dumps({"dias_atraso": 45}))

    assert description == {"dias_atraso": 45}


def test_description_accepts_dict() -> None:
    repository = PostgresSyntheticCaseRepository(pool=None)

    description = repository._description({"dias_atraso": 45})

    assert description == {"dias_atraso": 45}
