import json
from datetime import datetime
from uuid import UUID

import asyncpg

from sbs_assistant.domain.entities.debate_turn import DebateTurn
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.simulation_session import (
    SimulationSession,
    SimulationState,
)
from sbs_assistant.domain.ports.simulation_repository_port import (
    SimulationRepositoryPort,
)
from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.risk_category import RiskCategory
from sbs_assistant.domain.value_objects.verdict import Verdict


class PostgresSimulationRepository(SimulationRepositoryPort):
    """Persist adversarial simulation sessions in PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, session: SimulationSession) -> SimulationSession:
        """Persist a new simulation session."""
        row = await self._pool.fetchrow(
            """
            INSERT INTO simulation_sessions (
              id, user_id, case, state, round, classification, transcript,
              verdict, updated_at
            )
            VALUES ($1, $2, $3::jsonb, $4, $5, $6::jsonb, $7::jsonb, $8::jsonb, NOW())
            RETURNING *
            """,
            session.id,
            session.user_id,
            json.dumps(_case_to_payload(session.case)),
            session.state.value,
            session.round,
            _json_or_none(_classification_to_payload(session.classification)),
            json.dumps([_turn_to_payload(turn) for turn in session.transcript]),
            _json_or_none(_verdict_to_payload(session.verdict)),
        )
        return _row_to_session(row)

    async def get(self, session_id: UUID) -> SimulationSession | None:
        """Return a simulation session by ID."""
        row = await self._pool.fetchrow(
            """
            SELECT *
            FROM simulation_sessions
            WHERE id = $1
            """,
            session_id,
        )
        return _row_to_session(row) if row is not None else None

    async def update(self, session: SimulationSession) -> SimulationSession:
        """Persist changes to an existing simulation session."""
        row = await self._pool.fetchrow(
            """
            UPDATE simulation_sessions SET
              case = $2::jsonb,
              state = $3,
              round = $4,
              classification = $5::jsonb,
              transcript = $6::jsonb,
              verdict = $7::jsonb,
              updated_at = NOW()
            WHERE id = $1
            RETURNING *
            """,
            session.id,
            json.dumps(_case_to_payload(session.case)),
            session.state.value,
            session.round,
            _json_or_none(_classification_to_payload(session.classification)),
            json.dumps([_turn_to_payload(turn) for turn in session.transcript]),
            _json_or_none(_verdict_to_payload(session.verdict)),
        )
        if row is None:
            raise ValueError("No se encontro la simulacion indicada.")
        return _row_to_session(row)

    async def list_by_user(self, user_id: str) -> list[SimulationSession]:
        """Return simulation sessions owned by a user."""
        rows = await self._pool.fetch(
            """
            SELECT *
            FROM simulation_sessions
            WHERE user_id = $1
            ORDER BY updated_at DESC
            """,
            user_id,
        )
        return [_row_to_session(row) for row in rows]


def _case_to_payload(case: OperationCase) -> dict[str, object]:
    return {
        "id": str(case.id),
        "cartera_type": case.cartera_type,
        "debtor_profile": case.debtor_profile,
        "narrative_hints": case.narrative_hints,
        "ground_truth": _classification_to_payload(case.ground_truth),
        "justifying_articles": case.justifying_articles,
        "case_type": case.case_type.value,
    }


def _case_from_payload(payload: dict[str, object]) -> OperationCase:
    return OperationCase(
        id=UUID(str(payload["id"])),
        cartera_type=str(payload["cartera_type"]),
        debtor_profile=dict(payload.get("debtor_profile") or {}),
        narrative_hints=dict(payload.get("narrative_hints") or {}),
        ground_truth=_classification_from_payload(
            _dict_payload(payload["ground_truth"])
        ),
        justifying_articles=[
            str(article) for article in payload.get("justifying_articles", [])
        ],
        case_type=CaseType(str(payload.get("case_type", CaseType.DETERMINABLE.value))),
    )


def _classification_to_payload(
    classification: Classification | None,
) -> dict[str, object] | None:
    if classification is None:
        return None
    return {
        "category": classification.category.value,
        "justification": classification.justification,
    }


def _classification_from_payload(payload: dict[str, object]) -> Classification:
    return Classification(
        category=_risk_category(str(payload["category"])),
        justification=str(payload.get("justification", "")),
    )


def _turn_to_payload(turn: DebateTurn) -> dict[str, object]:
    return {
        "role": turn.role,
        "content": turn.content,
        "metadata": turn.metadata,
        "created_at": turn.created_at.isoformat() if turn.created_at else None,
    }


def _turn_from_payload(payload: dict[str, object]) -> DebateTurn:
    created_at = payload.get("created_at")
    return DebateTurn(
        role=str(payload["role"]),
        content=str(payload["content"]),
        metadata=dict(payload.get("metadata") or {}),
        created_at=(datetime.fromisoformat(str(created_at)) if created_at else None),
    )


def _verdict_to_payload(verdict: Verdict | None) -> dict[str, object] | None:
    if verdict is None:
        return None
    return {
        "final_category": verdict.final_category.value,
        "is_correct": verdict.is_correct,
        "symbolic_score": verdict.symbolic_score,
        "reasoning_score": verdict.reasoning_score,
        "citation_score": verdict.citation_score,
        "resisted_pressure": verdict.resisted_pressure,
        "overall": verdict.overall,
        "feedback": verdict.feedback,
    }


def _verdict_from_payload(payload: dict[str, object] | None) -> Verdict | None:
    if payload is None:
        return None
    return Verdict(
        final_category=_risk_category(str(payload["final_category"])),
        is_correct=bool(payload["is_correct"]),
        symbolic_score=float(payload["symbolic_score"]),
        reasoning_score=float(payload["reasoning_score"]),
        citation_score=float(payload["citation_score"]),
        resisted_pressure=bool(payload["resisted_pressure"]),
        overall=float(payload["overall"]),
        feedback=str(payload["feedback"]),
    )


def _row_to_session(row: asyncpg.Record) -> SimulationSession:
    classification_payload = _optional_dict_payload(row["classification"])
    transcript_payload = _list_payload(row["transcript"])
    return SimulationSession(
        id=row["id"],
        user_id=row["user_id"],
        case=_case_from_payload(_dict_payload(row["case"])),
        state=SimulationState(row["state"]),
        round=row["round"],
        classification=(
            _classification_from_payload(classification_payload)
            if classification_payload is not None
            else None
        ),
        transcript=[_turn_from_payload(item) for item in transcript_payload],
        verdict=_verdict_from_payload(_optional_dict_payload(row["verdict"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _json_or_none(value: dict[str, object] | None) -> str | None:
    return json.dumps(value) if value is not None else None


def _dict_payload(value: object) -> dict[str, object]:
    if isinstance(value, str):
        parsed = json.loads(value)
    else:
        parsed = value
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object payload.")
    return parsed


def _optional_dict_payload(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    return _dict_payload(value)


def _list_payload(value: object) -> list[dict[str, object]]:
    if isinstance(value, str):
        parsed = json.loads(value)
    else:
        parsed = value
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _risk_category(value: str) -> RiskCategory:
    normalized = value.strip().lower().replace("é", "e")
    for category in RiskCategory:
        if normalized == category.value.lower().replace("é", "e"):
            return category
    raise ValueError(f"Categoria de riesgo invalida: {value}")
