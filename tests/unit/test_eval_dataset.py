import json
from pathlib import Path

from tests.eval.run_eval import (
    EvalCase,
    citation_score,
    keyword_score,
    load_cases,
    normalize_text,
)

DATASET_PATH = Path("tests/eval/sbs_validation_questions.json")


def test_eval_dataset_has_expected_shape() -> None:
    cases = load_cases(DATASET_PATH)

    assert len(cases) == 20
    assert len({case.id for case in cases}) == len(cases)
    assert all(case.question for case in cases)
    assert all(case.expected_answer for case in cases)
    assert all(case.expected_citations for case in cases)
    assert all(case.concepts for case in cases)


def test_eval_dataset_has_valid_utf8_text() -> None:
    raw_cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    serialized = json.dumps(raw_cases, ensure_ascii=False)

    assert "Ã" not in serialized
    assert "Â" not in serialized


def test_eval_dataset_cases_validate_with_model() -> None:
    raw_cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    cases = [EvalCase.model_validate(item) for item in raw_cases]

    assert cases[0].id == "q001"
    assert cases[0].answer_type == "factual"


def test_keyword_score_is_accent_insensitive() -> None:
    expected = "Categoría Pérdida con provisión específica."
    actual = "La categoria perdida requiere provision especifica."

    assert keyword_score(expected, actual) == 1.0


def test_citation_score_matches_numeral_labels() -> None:
    score, matched, missing = citation_score(
        ["Capítulo II, Numeral 3.3"],
        [{"label": "Numeral 3.3", "chunk_id": "sec_026_3_3"}],
        "La respuesta cita el criterio aplicable.",
    )

    assert score == 1.0
    assert matched == ["Capítulo II, Numeral 3.3"]
    assert missing == []


def test_normalize_text_removes_accents_and_punctuation() -> None:
    assert normalize_text("¿Categoría Pérdida?") == "categoria perdida"
