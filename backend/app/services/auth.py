from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from hashlib import sha256
import hmac
import re
from secrets import token_bytes, token_urlsafe
from uuid import UUID

from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, password_needs_rehash, verify_password
from app.models import AuthSession, User


_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")


class SessionFailure(StrEnum):
    MISSING = "missing"
    MALFORMED = "malformed"
    UNKNOWN = "unknown"
    EXPIRED = "expired"
    DISABLED = "disabled"
    REVOKED = "revoked"
    CHANGED = "changed"


class InvalidSession(Exception):
    def __init__(self, reason: SessionFailure):
        self.reason = reason
        super().__init__(reason)


class InvalidCredentials(Exception):
    pass


@dataclass(frozen=True)
class AuthContext:
    session_id: UUID
    user: User
    absolute_expires_at: datetime
    csrf_token: str = field(repr=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive values for DateTime(timezone=True). Session timestamps are written in UTC.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _context(session: AuthSession, user: User, token: str) -> AuthContext:
    # Both the cookie and the per-session seed are required to derive the CSRF proof.
    csrf_token = hmac.digest(token.encode("ascii"), session.csrf_seed, "sha256").hex()
    return AuthContext(session.id, user, _as_utc(session.absolute_expires_at), csrf_token)


def start_session(db: Session, email: str, password: str) -> tuple[str, AuthContext]:
    candidate = db.execute(
        select(User.id, User.password_hash).where(User.email_normalized == email.strip().casefold())
    ).one_or_none()
    stored_hash = candidate.password_hash if candidate is not None else None
    if not verify_password(password, stored_hash) or candidate is None:
        raise InvalidCredentials
    new_hash = hash_password(password) if password_needs_rehash(stored_hash) else None

    # Recheck under the user row lock before issuing a session or replacing a hash.
    user = db.scalar(
        select(User).where(User.id == candidate.id).with_for_update().execution_options(populate_existing=True)
    )
    if user is None or user.disabled_at is not None or user.password_hash != stored_hash:
        raise InvalidCredentials
    if new_hash is not None:
        user.password_hash = new_hash

    now = utc_now()
    token = token_urlsafe(32)
    session = AuthSession(
        user_id=user.id,
        token_digest=sha256(token.encode("ascii")).digest(),
        csrf_seed=token_bytes(32),
        created_at=now,
        idle_expires_at=now + timedelta(seconds=settings.auth_idle_timeout_seconds),
        absolute_expires_at=now + timedelta(seconds=settings.auth_absolute_timeout_seconds),
    )
    db.add(session)
    db.flush()
    context = _context(session, user, token)
    db.commit()
    return token, context


def resolve_session(db: Session, token: str | None) -> AuthContext:
    if token is None:
        raise InvalidSession(SessionFailure.MISSING)
    if not _TOKEN.fullmatch(token):
        raise InvalidSession(SessionFailure.MALFORMED)

    row = db.execute(
        select(AuthSession, User).join(User, User.id == AuthSession.user_id)
        .where(AuthSession.token_digest == sha256(token.encode("ascii")).digest())
        .execution_options(populate_existing=True)
    ).one_or_none()
    if row is None:
        raise InvalidSession(SessionFailure.UNKNOWN)

    session, user = row
    if user.disabled_at is not None:
        raise InvalidSession(SessionFailure.DISABLED)
    _require_live_session(session)
    return _context(session, user, token)


def _require_live_session(session: AuthSession) -> None:
    if session.revoked_at is not None:
        raise InvalidSession(SessionFailure.REVOKED)
    if utc_now() >= min(_as_utc(session.idle_expires_at), _as_utc(session.absolute_expires_at)):
        raise InvalidSession(SessionFailure.EXPIRED)


def lock_live_session(db: Session, user_id: UUID, session_id: UUID, *, exclusive=False) -> AuthSession:
    # Protect the user and session until the caller commits or rolls back its write.
    user = db.scalar(select(User.id).where(User.id == user_id, User.disabled_at.is_(None)).with_for_update(read=True))
    if user is None:
        raise InvalidSession(SessionFailure.DISABLED)
    session = db.scalar(
        select(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == user_id)
        .with_for_update(read=not exclusive).execution_options(populate_existing=True)
    )
    if session is None:
        raise InvalidSession(SessionFailure.UNKNOWN)
    _require_live_session(session)
    return session


def recheck_locked_session(db: Session, user_id: UUID, session_id: UUID) -> None:
    """Recheck after resource lock waits while the earlier user/session locks are still held."""
    row = db.execute(
        select(AuthSession, User.disabled_at).join(User, User.id == AuthSession.user_id)
        .where(AuthSession.id == session_id, AuthSession.user_id == user_id)
        .execution_options(populate_existing=True)
    ).one_or_none()
    if row is None:
        raise InvalidSession(SessionFailure.UNKNOWN)
    session, disabled_at = row
    if disabled_at is not None:
        raise InvalidSession(SessionFailure.DISABLED)
    # Sample wall time after the read and all row-lock waits.
    _require_live_session(session)


def _write_live_session(db: Session, session: AuthContext, now: datetime, **values) -> None:
    # Recheck the live row in the write itself. A concurrent logout cannot be overwritten.
    statement = (
        update(AuthSession)
        .where(
            AuthSession.id == session.session_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.idle_expires_at > now,
            AuthSession.absolute_expires_at > now,
            select(User.id).where(User.id == AuthSession.user_id, User.disabled_at.is_(None)).exists(),
        )
        .values(**values)
        .returning(AuthSession.id)
        .execution_options(synchronize_session=False)
    )
    if db.scalar(statement) is None:
        raise InvalidSession(SessionFailure.CHANGED)
    db.commit()


def refresh_session(db: Session, session: AuthContext) -> None:
    locked_session = lock_live_session(db, session.user.id, session.session_id, exclusive=True)
    now = utc_now()
    idle_until = min(now + timedelta(seconds=settings.auth_idle_timeout_seconds), _as_utc(locked_session.absolute_expires_at))
    _write_live_session(db, session, now, idle_expires_at=case(
        (AuthSession.idle_expires_at < idle_until, idle_until),
        else_=AuthSession.idle_expires_at,
    ))


def revoke_session(db: Session, session: AuthContext) -> None:
    lock_live_session(db, session.user.id, session.session_id, exclusive=True)
    now = utc_now()
    _write_live_session(db, session, now, revoked_at=now)
