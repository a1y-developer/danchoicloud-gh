from datetime import datetime, timezone
from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.session import get_session


def get_db() -> Generator[Session, None, None]:
    yield from get_session()


def _load_session(token: str | None, db: Session) -> Optional[models.UserSession]:
    if not token:
        return None
    return (
        db.query(models.UserSession).filter(models.UserSession.token == token).first()
    )


def get_optional_user(
    request: Request, db: Session = Depends(get_session)
) -> Optional[models.AppUser]:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    session = _load_session(token, db)
    if not session:
        return None
    if session.expires_at < datetime.now(timezone.utc):
        return None
    return session.user


def require_user(
    request: Request, db: Session = Depends(get_session)
) -> models.AppUser:
    user = get_optional_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
