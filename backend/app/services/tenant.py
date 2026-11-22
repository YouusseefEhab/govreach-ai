from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Membership
from app.services.auth import lock_live_session


_ROLE_LEVEL = {"viewer": 1, "editor": 2, "owner": 3}


@dataclass(frozen=True)
class TenantContext:
    business_id: UUID
    user_id: UUID
    session_id: UUID
    role: str


class BusinessNotFound(Exception):
    pass


class PermissionDenied(Exception):
    pass


def require_role(tenant: TenantContext, minimum: str) -> None:
    if _ROLE_LEVEL.get(tenant.role, 0) < _ROLE_LEVEL[minimum]:
        raise PermissionDenied


def get_tenant(db: Session, business_id: UUID, user_id: UUID, session_id: UUID, *, for_write=False) -> TenantContext:
    membership = select(Membership.role).where(Membership.business_id == business_id, Membership.user_id == user_id)
    if for_write:
        # Lock user, session and membership before the caller locks its resource.
        # The caller rechecks session expiry after those resource locks.
        lock_live_session(db, user_id, session_id)
        membership = membership.with_for_update(read=True)
    role = db.scalar(membership)
    if role not in _ROLE_LEVEL:
        raise BusinessNotFound
    return TenantContext(business_id, user_id, session_id, role)
