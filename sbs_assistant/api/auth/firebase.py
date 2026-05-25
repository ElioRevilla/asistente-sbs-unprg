from dataclasses import dataclass
from typing import Annotated

import firebase_admin
from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth, credentials

from sbs_assistant.config.settings import Settings, get_settings


@dataclass(frozen=True, slots=True)
class FirebaseUser:
    """Authenticated Firebase user extracted from an ID token."""

    uid: str
    email: str | None
    name: str | None


SettingsDependency = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    request: Request,
    settings: SettingsDependency,
) -> FirebaseUser | None:
    """Validate a Firebase ID token when present or required."""
    authorization = request.headers.get("authorization")
    if not authorization:
        if settings.firebase_auth_required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Firebase ID token.",
            )
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header.",
        )

    project_id = settings.firebase_token_project_id
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase project is not configured.",
        )

    try:
        decoded = auth.verify_id_token(
            token,
            app=_get_firebase_app(project_id),
            check_revoked=True,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token.",
        ) from error

    return FirebaseUser(
        uid=str(decoded["uid"]),
        email=decoded.get("email"),
        name=decoded.get("name"),
    )


def _get_firebase_app(project_id: str) -> firebase_admin.App:
    app_name = f"sbs-assistant-{project_id}"
    try:
        return firebase_admin.get_app(app_name)
    except ValueError:
        credential = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(
            credential=credential,
            options={"projectId": project_id},
            name=app_name,
        )
