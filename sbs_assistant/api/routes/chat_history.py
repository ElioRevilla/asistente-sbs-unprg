from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.api.schemas.request_schemas import ChatConversationUpsertRequest
from sbs_assistant.api.schemas.response_schemas import (
    ChatConversationListResponse,
    ChatConversationResponse,
)
from sbs_assistant.config.settings import Settings, get_settings
from sbs_assistant.infrastructure.persistence.connection import (
    close_cloud_sql_connectors,
    create_pool,
)
from sbs_assistant.infrastructure.persistence.postgres_chat_history_repo import (
    ChatConversationRecord,
    PostgresChatHistoryRepository,
)

router = APIRouter(prefix="/chat/conversations", tags=["chat"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
CurrentUserDependency = Annotated[FirebaseUser | None, Depends(get_current_user)]


async def get_chat_history_repository(
    settings: SettingsDependency,
) -> AsyncIterator[PostgresChatHistoryRepository]:
    """Build the chat history repository for API requests."""
    pool = await create_pool(settings)
    try:
        yield PostgresChatHistoryRepository(pool=pool)
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


@router.get("", response_model=ChatConversationListResponse)
async def list_conversations(
    repository: Annotated[
        PostgresChatHistoryRepository,
        Depends(get_chat_history_repository),
    ],
    current_user: CurrentUserDependency,
) -> ChatConversationListResponse:
    """List persisted conversations for the authenticated Firebase user."""
    user = _require_user(current_user)
    records = await repository.list_by_user(user.uid)
    return ChatConversationListResponse(
        conversations=[_to_response(record) for record in records]
    )


@router.put("/{conversation_id}", response_model=ChatConversationResponse)
async def upsert_conversation(
    conversation_id: UUID,
    request: ChatConversationUpsertRequest,
    repository: Annotated[
        PostgresChatHistoryRepository,
        Depends(get_chat_history_repository),
    ],
    current_user: CurrentUserDependency,
) -> ChatConversationResponse:
    """Create or update a conversation for the authenticated Firebase user."""
    user = _require_user(current_user)
    try:
        record = await repository.upsert(
            conversation_id=conversation_id,
            firebase_uid=user.uid,
            title=request.title,
            mode=request.mode,
            messages=request.messages,
        )
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    return _to_response(record)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    repository: Annotated[
        PostgresChatHistoryRepository,
        Depends(get_chat_history_repository),
    ],
    current_user: CurrentUserDependency,
) -> None:
    """Delete a persisted conversation owned by the authenticated Firebase user."""
    user = _require_user(current_user)
    await repository.delete(conversation_id=conversation_id, firebase_uid=user.uid)


def _require_user(current_user: FirebaseUser | None) -> FirebaseUser:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase authentication is required for chat history.",
        )
    return current_user


def _to_response(record: ChatConversationRecord) -> ChatConversationResponse:
    return ChatConversationResponse(
        id=str(record.id),
        title=record.title,
        mode=record.mode,
        messages=record.messages,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )
