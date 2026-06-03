import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class ChatConversationRecord:
    """Persisted chat conversation owned by a Firebase user."""

    id: UUID
    firebase_uid: str
    title: str
    mode: str
    messages: list[dict[str, object]]
    created_at: datetime
    updated_at: datetime


class PostgresChatHistoryRepository:
    """Store and retrieve chat conversations from PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_by_user(self, firebase_uid: str) -> list[ChatConversationRecord]:
        """Return the user's conversations, newest first."""
        rows = await self._pool.fetch(
            """
            SELECT id, firebase_uid, title, mode, messages, created_at, updated_at
            FROM chat_conversations
            WHERE firebase_uid = $1
            ORDER BY updated_at DESC
            """,
            firebase_uid,
        )
        return [_to_record(row) for row in rows]

    async def upsert(
        self,
        *,
        conversation_id: UUID,
        firebase_uid: str,
        title: str,
        mode: str,
        messages: list[dict[str, object]],
    ) -> ChatConversationRecord:
        """Create or update a conversation owned by the given Firebase user."""
        row = await self._pool.fetchrow(
            """
            INSERT INTO chat_conversations (
              id, firebase_uid, title, mode, messages, updated_at
            )
            VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
            ON CONFLICT (id) DO UPDATE SET
              title = EXCLUDED.title,
              mode = EXCLUDED.mode,
              messages = EXCLUDED.messages,
              updated_at = NOW()
            WHERE chat_conversations.firebase_uid = EXCLUDED.firebase_uid
            RETURNING id, firebase_uid, title, mode, messages, created_at, updated_at
            """,
            conversation_id,
            firebase_uid,
            title,
            mode,
            json.dumps(messages),
        )
        if row is None:
            raise PermissionError("Conversation does not belong to the current user.")
        return _to_record(row)

    async def delete(self, *, conversation_id: UUID, firebase_uid: str) -> bool:
        """Delete a conversation if it belongs to the current user."""
        result = await self._pool.execute(
            """
            DELETE FROM chat_conversations
            WHERE id = $1 AND firebase_uid = $2
            """,
            conversation_id,
            firebase_uid,
        )
        return result == "DELETE 1"


def _to_record(row: asyncpg.Record) -> ChatConversationRecord:
    return ChatConversationRecord(
        id=row["id"],
        firebase_uid=row["firebase_uid"],
        title=row["title"],
        mode=row["mode"],
        messages=_parse_messages(row["messages"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _parse_messages(value: object) -> list[dict[str, object]]:
    if isinstance(value, str):
        parsed = json.loads(value)
    else:
        parsed = value
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]
