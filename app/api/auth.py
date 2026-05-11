import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user, require_user
from app.core.config import settings
from app.db import models
from app.db.session import get_session

router = APIRouter()


def _require_oauth_settings() -> None:
    if not settings.GITHUB_OAUTH_CLIENT_ID or not settings.GITHUB_OAUTH_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth is not configured.")


def _get_redirect_uri(request: Request) -> str:
    if settings.GITHUB_OAUTH_REDIRECT_URI:
        return settings.GITHUB_OAUTH_REDIRECT_URI
    return str(request.url_for("github_callback"))


def _fetch_access_token(code: str, redirect_uri: str) -> dict[str, Any]:
    response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _fetch_github_user(access_token: str) -> dict[str, Any]:
    response = requests.get(
        "https://api.github.com/user",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


@router.get("/auth/github/authorize")
def github_authorize(request: Request, db: Session = Depends(get_session)):
    _require_oauth_settings()
    state = secrets.token_urlsafe(32)
    db.add(models.OAuthState(state=state))
    db.commit()

    redirect_uri = _get_redirect_uri(request)
    params = urlencode(
        {
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": settings.GITHUB_OAUTH_SCOPES,
            "state": state,
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/auth/github/callback", name="github_callback")
def github_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_session),
):
    _require_oauth_settings()
    oauth_state = (
        db.query(models.OAuthState).filter(models.OAuthState.state == state).first()
    )
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    db.delete(oauth_state)
    db.commit()

    redirect_uri = _get_redirect_uri(request)
    token_data = _fetch_access_token(code, redirect_uri)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="OAuth token exchange failed.")

    user_data = _fetch_github_user(access_token)
    github_id = user_data.get("id")
    login = user_data.get("login")
    if not github_id or not login:
        raise HTTPException(status_code=400, detail="GitHub user data missing.")

    user = (
        db.query(models.AppUser).filter(models.AppUser.github_id == github_id).first()
    )
    if not user:
        user = models.AppUser(
            github_id=github_id,
            login=login,
            name=user_data.get("name"),
            avatar_url=user_data.get("avatar_url"),
            email=user_data.get("email"),
        )
        db.add(user)
    else:
        user.login = login
        user.name = user_data.get("name")
        user.avatar_url = user_data.get("avatar_url")
        user.email = user_data.get("email")
    db.commit()

    session_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.SESSION_EXPIRES_DAYS
    )
    db.add(
        models.UserSession(
            token=session_token,
            user_id=user.id,
            expires_at=expires_at,
        )
    )
    db.commit()

    response = RedirectResponse(settings.WEB_BASE_URL)
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=int(timedelta(days=settings.SESSION_EXPIRES_DAYS).total_seconds()),
    )
    return response


@router.get("/auth/session")
def auth_session(user=Depends(get_optional_user)):
    if not user:
        return {
            "authenticated": False,
            "user": None,
            "app_slug": settings.GITHUB_APP_SLUG,
        }
    return {
        "authenticated": True,
        "user": {
            "login": user.login,
            "name": user.name,
            "avatar_url": user.avatar_url,
        },
        "app_slug": settings.GITHUB_APP_SLUG,
    }


@router.post("/auth/logout")
def auth_logout(
    request: Request,
    user=Depends(require_user),
    db: Session = Depends(get_session),
):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    session = (
        db.query(models.UserSession).filter(models.UserSession.token == token).first()
    )
    if session:
        db.delete(session)
        db.commit()
    response = RedirectResponse(settings.WEB_BASE_URL)
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return response
