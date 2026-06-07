from sbs_assistant.application.services.retrieval_planner import (
    PlannedAnswer,
    RetrievalPlanner,
)


def test_planner_expands_top_k_for_credit_types_question() -> None:
    plan = RetrievalPlanner().plan(
        question="¿Cuántos tipos de crédito existen y cuáles son?",
        requested_top_k=5,
    )

    assert plan.top_k == 10
    assert plan.answer_strategy == PlannedAnswer.CREDIT_TYPES


def test_planner_tolerates_malformed_accent_input() -> None:
    plan = RetrievalPlanner().plan(
        question="¿Cu?ntos tipos de cr?dito existen?",
        requested_top_k=5,
    )

    assert plan.top_k == 10
    assert plan.answer_strategy == PlannedAnswer.CREDIT_TYPES


def test_planner_detects_long_stay_risk_category_question() -> None:
    plan = RetrievalPlanner().plan(
        question=(
            "¿Qué pasa con un deudor que permanece mucho tiempo en categoría "
            "Pérdida? ¿Hay alguna regla especial?"
        ),
        requested_top_k=5,
    )

    assert plan.top_k == 10
    assert plan.query is not None
    assert "Pérdida más de 24 meses" in plan.query
    assert plan.answer_strategy == PlannedAnswer.LONG_STAY_RISK_CATEGORY


def test_planner_detects_minorist_deficient_days_question() -> None:
    plan = RetrievalPlanner().plan(
        question=(
            "Para un credito a pequena empresa, microempresa o de consumo, "
            "que rango de dias de atraso corresponde a la categoria Deficiente?"
        ),
        requested_top_k=5,
    )

    assert plan.top_k == 10
    assert plan.query is not None
    assert "3.3 categoria deficiente" in plan.query
    assert "microempresas consumo" in plan.query
    assert plan.answer_strategy == PlannedAnswer.MINORIST_DEFICIENT_DAYS


def test_planner_does_not_use_minorist_days_strategy_for_provision_question() -> None:
    plan = RetrievalPlanner().plan(
        question=(
            "Un credito a pequena empresa de S/ 50,000 esta clasificado en "
            "categoria Deficiente, sin garantias preferidas, y debe "
            "provisionarse segun la Tabla 1. Cuanto debe provisionar?"
        ),
        requested_top_k=5,
    )

    assert plan.answer_strategy is None


def test_planner_keeps_default_for_general_question() -> None:
    plan = RetrievalPlanner().plan(
        question="¿Qué significa categoría Dudoso?",
        requested_top_k=5,
    )

    assert plan.top_k == 5
    assert plan.answer_strategy is None
