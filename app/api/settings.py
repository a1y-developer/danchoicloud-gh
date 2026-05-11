from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.config import settings
from app.db import models
from app.db.session import get_session

router = APIRouter()


class IntegrationScopePayload(BaseModel):
    scope_type: Literal["org", "repo"] | None = None
    scope_name: str | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope_type and not self.scope_name:
            raise ValueError("scope_name is required when scope_type is set")
        if self.scope_name and not self.scope_type:
            raise ValueError("scope_type is required when scope_name is set")
        return self


def _get_env_scope() -> tuple[str | None, str | None]:
    if settings.INTEGRATION_SCOPE_TYPE and settings.INTEGRATION_SCOPE_NAME:
        return settings.INTEGRATION_SCOPE_TYPE, settings.INTEGRATION_SCOPE_NAME
    return None, None


@router.get("/settings/integration-scope")
def get_integration_scope(db: Session = Depends(get_session)):
    env_type, env_name = _get_env_scope()
    if env_type and env_name:
        return {
            "scope_type": env_type,
            "scope_name": env_name,
            "locked": True,
        }

    scope = (
        db.query(models.IntegrationScope)
        .order_by(models.IntegrationScope.id.desc())
        .first()
    )
    if not scope or not scope.scope_type or not scope.scope_name:
        return {"scope_type": None, "scope_name": None, "locked": False}
    return {
        "scope_type": scope.scope_type,
        "scope_name": scope.scope_name,
        "locked": False,
    }


@router.put("/settings/integration-scope")
def update_integration_scope(
    payload: IntegrationScopePayload,
    db: Session = Depends(get_session),
    user=Depends(require_user),
):
    env_type, env_name = _get_env_scope()
    if env_type and env_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Integration scope is locked by environment settings.",
        )

    scope = (
        db.query(models.IntegrationScope)
        .order_by(models.IntegrationScope.id.desc())
        .first()
    )
    if not scope:
        scope = models.IntegrationScope(
            scope_type=payload.scope_type, scope_name=payload.scope_name
        )
        db.add(scope)
    else:
        scope.scope_type = payload.scope_type
        scope.scope_name = payload.scope_name
    db.commit()

    return {
        "scope_type": scope.scope_type,
        "scope_name": scope.scope_name,
        "locked": False,
    }
