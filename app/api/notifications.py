from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db import models
from app.db.session import get_session
from app.services.integration_scope import enforce_scope

router = APIRouter()


class NotificationChannelBase(BaseModel):
    scope_type: Literal["org", "repo"]
    scope_name: str
    channel_type: Literal["telegram", "discord", "slack", "webhook"]
    config: dict = Field(default_factory=dict)
    is_active: bool = True


class NotificationChannelUpdate(BaseModel):
    config: dict | None = None
    is_active: bool | None = None


class NotificationChannelResponse(NotificationChannelBase):
    id: int


def _serialize_channel(
    channel: models.NotificationChannel,
) -> NotificationChannelResponse:
    return NotificationChannelResponse(
        id=channel.id,
        scope_type=channel.scope_type,
        scope_name=channel.scope_name,
        channel_type=channel.channel_type,
        config=channel.config or {},
        is_active=channel.is_active,
    )


@router.get("/notifications/channels", response_model=list[NotificationChannelResponse])
def list_channels(
    scope_type: Literal["org", "repo"] = Query(...),
    scope_name: str = Query(...),
    db: Session = Depends(get_session),
    user=Depends(require_user),
):
    try:
        enforce_scope(scope_type, scope_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    channels = (
        db.query(models.NotificationChannel)
        .filter(models.NotificationChannel.scope_type == scope_type)
        .filter(models.NotificationChannel.scope_name == scope_name)
        .order_by(models.NotificationChannel.id.desc())
        .all()
    )
    return [_serialize_channel(channel) for channel in channels]


@router.post(
    "/notifications/channels",
    response_model=NotificationChannelResponse,
    status_code=201,
)
def create_channel(
    payload: NotificationChannelBase,
    db: Session = Depends(get_session),
    user=Depends(require_user),
):
    try:
        enforce_scope(payload.scope_type, payload.scope_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    channel = models.NotificationChannel(
        scope_type=payload.scope_type,
        scope_name=payload.scope_name,
        channel_type=payload.channel_type,
        config=payload.config,
        is_active=payload.is_active,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return _serialize_channel(channel)


@router.put(
    "/notifications/channels/{channel_id}", response_model=NotificationChannelResponse
)
def update_channel(
    channel_id: int,
    payload: NotificationChannelUpdate,
    db: Session = Depends(get_session),
    user=Depends(require_user),
):
    channel = (
        db.query(models.NotificationChannel)
        .filter(models.NotificationChannel.id == channel_id)
        .first()
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found.")

    try:
        enforce_scope(channel.scope_type, channel.scope_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    if payload.config is not None:
        channel.config = payload.config
    if payload.is_active is not None:
        channel.is_active = payload.is_active
    db.commit()
    db.refresh(channel)
    return _serialize_channel(channel)


@router.delete("/notifications/channels/{channel_id}", status_code=204)
def delete_channel(
    channel_id: int,
    db: Session = Depends(get_session),
    user=Depends(require_user),
):
    channel = (
        db.query(models.NotificationChannel)
        .filter(models.NotificationChannel.id == channel_id)
        .first()
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found.")

    try:
        enforce_scope(channel.scope_type, channel.scope_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    db.delete(channel)
    db.commit()
