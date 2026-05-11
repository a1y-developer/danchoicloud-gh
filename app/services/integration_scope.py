import asyncio
import logging

from app.core.config import settings
from app.db import models
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _get_env_scope() -> tuple[str | None, str | None]:
    if settings.INTEGRATION_SCOPE_TYPE and settings.INTEGRATION_SCOPE_NAME:
        return settings.INTEGRATION_SCOPE_TYPE, settings.INTEGRATION_SCOPE_NAME
    return None, None


def _get_scope_sync() -> tuple[str | None, str | None]:
    env_type, env_name = _get_env_scope()
    if env_type and env_name:
        return env_type, env_name

    with SessionLocal() as session:
        scope = (
            session.query(models.IntegrationScope)
            .order_by(models.IntegrationScope.id.desc())
            .first()
        )
        if scope and scope.scope_type and scope.scope_name:
            return scope.scope_type, scope.scope_name
    return None, None


async def get_integration_scope() -> tuple[str | None, str | None]:
    return await asyncio.to_thread(_get_scope_sync)


async def is_payload_allowed(payload: dict) -> bool:
    scope_type, scope_name = await get_integration_scope()
    if not scope_type or not scope_name:
        return True

    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login")
    full_name = repo.get("full_name")

    if scope_type == "org":
        return owner == scope_name
    if scope_type == "repo":
        return full_name == scope_name
    logger.warning("Unknown integration scope type: %s", scope_type)
    return True


def enforce_scope(scope_type: str, scope_name: str) -> None:
    env_type, env_name = _get_env_scope()
    if env_type and env_name:
        if scope_type != env_type or scope_name != env_name:
            raise ValueError("Scope is restricted by environment configuration.")
        return

    with SessionLocal() as session:
        scope = (
            session.query(models.IntegrationScope)
            .order_by(models.IntegrationScope.id.desc())
            .first()
        )
        if scope and scope.scope_type and scope.scope_name:
            if scope.scope_type != scope_type or scope.scope_name != scope_name:
                raise ValueError("Scope is restricted by integration settings.")
