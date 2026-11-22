from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.dependencies.auth import (
    SESSION_COOKIE_NAME,
    CurrentSession,
    DatabaseSession,
    require_csrf,
    require_login_origin,
)
from app.core.config import settings
from app.schemas.auth import LoginRequest, SessionRead, UserRead
from app.services.auth import AuthContext, InvalidCredentials, InvalidSession, refresh_session, revoke_session, start_session


class AuthRoute(APIRoute):
    def get_route_handler(self):
        handle = super().get_route_handler()

        async def handle_auth(request):
            no_store = {"Cache-Control": "no-store"}
            try:
                response = await handle(request)
            except RequestValidationError:
                raise HTTPException(422, "Invalid authentication request.", headers=no_store) from None
            except InvalidSession:
                raise HTTPException(401, "Authentication required.", headers=no_store) from None
            except SQLAlchemyError:
                raise HTTPException(503, "Authentication unavailable.", headers=no_store) from None
            except StarletteHTTPException as error:
                error.headers = {**(error.headers or {}), **no_store}
                raise
            response.headers.update(no_store)
            return response

        return handle_auth


router = APIRouter(prefix="/auth", tags=["Authentication"], route_class=AuthRoute)
_cookie_flags = {"path": "/", "secure": True, "httponly": True, "samesite": "lax"}


@router.post(
    "/login", response_model=SessionRead, dependencies=[Depends(require_login_origin)],
    description="Sign in over HTTPS. Supply the trusted Origin and X-MarketPilot-Login: 1. The response sets a session cookie.",
    responses={401: {"description": "Invalid credentials"}, 403: {"description": "Untrusted login request"},
               415: {"description": "JSON required"}, 422: {"description": "Invalid authentication request"},
               503: {"description": "Authentication unavailable"}},
)
def login(data: LoginRequest, db: DatabaseSession, response: Response):
    try:
        token, session = start_session(db, data.email, data.password.get_secret_value())
    except InvalidCredentials:
        raise HTTPException(401, "Invalid email or password.") from None
    response.set_cookie(SESSION_COOKIE_NAME, token, max_age=settings.auth_absolute_timeout_seconds, **_cookie_flags)
    return SessionRead(user=UserRead.model_validate(session.user), csrf_token=session.csrf_token)


@router.get(
    "/me", response_model=SessionRead,
    description="Return the signed-in user and session-bound CSRF token over HTTPS, and renew the idle deadline.",
    responses={401: {"description": "Authentication required"}, 403: {"description": "HTTPS required"},
               503: {"description": "Authentication unavailable"}},
)
def me(session: CurrentSession, db: DatabaseSession):
    payload = SessionRead(user=UserRead.model_validate(session.user), csrf_token=session.csrf_token)
    refresh_session(db, session)
    return payload


@router.post(
    "/logout", status_code=204,
    description="Revoke the current session and clear the cookie. Requires the trusted Origin and session-bound X-CSRF-Token.",
    responses={401: {"description": "Authentication required"}, 403: {"description": "Invalid origin or CSRF token"},
               503: {"description": "Authentication unavailable"}},
)
def logout(session: Annotated[AuthContext, Depends(require_csrf)], db: DatabaseSession):
    revoke_session(db, session)
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE_NAME, **_cookie_flags)
    return response
