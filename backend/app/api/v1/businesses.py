from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.dependencies.auth import CurrentSession, DatabaseSession
from app.api.dependencies.tenant import BUSINESS_ERRORS, CsrfSession, PrivateRoute
from app.models import Business, Membership
from app.schemas.business import BusinessCreate, BusinessRead, BusinessUpdate
from app.services.auth import lock_live_session, recheck_locked_session
from app.services.tenant import BusinessNotFound, get_tenant, require_role


router = APIRouter(prefix="/businesses", tags=["Businesses"], route_class=PrivateRoute, responses=BUSINESS_ERRORS)


def business_response(business: Business, role: str) -> BusinessRead:
    return BusinessRead(
        id=business.id, display_name=business.display_name, description=business.description,
        website_url=business.website_url, default_locale=business.default_locale,
        created_at=business.created_at, updated_at=business.updated_at, role=role,
    )


def member_businesses(user_id: UUID):
    return (
        select(Business, Membership.role).join(Membership, Membership.business_id == Business.id)
        .where(Membership.user_id == user_id)
    )


@router.get("", response_model=list[BusinessRead])
def list_businesses(session: CurrentSession, db: DatabaseSession):
    rows = db.execute(member_businesses(session.user.id).order_by(Business.created_at, Business.id))
    return [business_response(business, role) for business, role in rows]


@router.post("", response_model=BusinessRead, status_code=201)
def create_business(data: BusinessCreate, session: CsrfSession, db: DatabaseSession):
    lock_live_session(db, session.user.id, session.session_id)
    business = Business(**data.model_dump(mode="json"))
    db.add(Membership(business=business, user_id=session.user.id, role="owner"))
    db.commit()
    return business_response(business, "owner")


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(business_id: UUID, session: CurrentSession, db: DatabaseSession):
    row = db.execute(member_businesses(session.user.id).where(Business.id == business_id)).one_or_none()
    if row is None:
        raise BusinessNotFound
    business, role = row
    return business_response(business, role)


def editable_business(business_id: UUID, session: CsrfSession, db: DatabaseSession) -> Business:
    tenant = get_tenant(db, business_id, session.user.id, session.session_id, for_write=True)
    require_role(tenant, "owner")
    business = db.scalar(
        member_businesses(tenant.user_id).where(Business.id == business_id)
        .with_for_update(of=Business).execution_options(populate_existing=True)
    )
    if business is None:
        raise BusinessNotFound
    return business


@router.patch("/{business_id}", response_model=BusinessRead)
def update_business(
    business: Annotated[Business, Depends(editable_business)], data: BusinessUpdate,
    session: CsrfSession, db: DatabaseSession,
):
    recheck_locked_session(db, session.user.id, session.session_id)
    for field, value in data.model_dump(mode="json", exclude_unset=True).items():
        setattr(business, field, value)
    db.commit()
    return business_response(business, "owner")
