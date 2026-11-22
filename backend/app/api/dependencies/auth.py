from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import User
from app.services.auth import AuthContext, InvalidSession, resolve_session


SESSION_COOKIE_NAME = "__Host-marketpilot_session"
_session_cookie = APIKeyCookie(name=SESSION_COOKIE_NAME, scheme_name="MarketPilotSession", auto_error=False)
DatabaseSession = Annotated[Session, Depends(get_db)]


def _require_https(request: Request) -> None:
    if request.url.scheme != "https":
        raise HTTPException(403, "Authentication requires HTTPS.")


def _require_trusted_origin(request: Request, origin: str | None) -> None:
    _require_https(request)
    if (
        settings.auth_trusted_origin is None or origin != settings.auth_trusted_origin
        or len(request.headers.getlist("origin")) != 1
    ):
        raise HTTPException(403, "Origin is not allowed.")


def require_login_origin(
    request: Request,
    origin: Annotated[str | None, Header()] = None,
    login_header: Annotated[str | None, Header(alias="X-MarketPilot-Login")] = None,
) -> None:
    _require_trusted_origin(request, origin)
    if login_header != "1" or len(request.headers.getlist("X-MarketPilot-Login")) != 1:
        raise HTTPException(403, "Login header is required.")
    content_types = request.headers.getlist("content-type")
    if len(content_types) != 1 or content_types[0].partition(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "Login requires JSON.")


def get_current_session(
    request: Request,
    db: DatabaseSession,
    token: Annotated[str | None, Security(_session_cookie)],
    origin: Annotated[str | None, Header()] = None,
) -> AuthContext:
    _require_https(request)
    if origin is not None:
        _require_trusted_origin(request, origin)
    try:
        return resolve_session(db, token)
    except InvalidSession:
        raise HTTPException(401, "Authentication required.") from None


CurrentSession = Annotated[AuthContext, Depends(get_current_session)]


def get_current_user(session: CurrentSession) -> User:
    return session.user


def require_csrf(
    request: Request,
    session: CurrentSession,
    origin: Annotated[str | None, Header()] = None,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthContext:
    _require_trusted_origin(request, origin)
    if (
        csrf_token is None or len(csrf_token) != 64 or not csrf_token.isascii()
        or len(request.headers.getlist("X-CSRF-Token")) != 1
        or not compare_digest(csrf_token, session.csrf_token)
    ):
        raise HTTPException(403, "Invalid CSRF token.")
    return session
