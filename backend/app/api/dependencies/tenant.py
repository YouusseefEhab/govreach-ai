from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.dependencies.auth import CurrentSession, DatabaseSession, require_csrf
from app.models import Campaign
from app.repositories import campaign as campaigns
from app.services.auth import AuthContext, InvalidSession
from app.services.tenant import BusinessNotFound, PermissionDenied, TenantContext, get_tenant, require_role


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        handle = super().get_route_handler()

        async def handle_private(request):
            no_store = {"Cache-Control": "no-store"}
            try:
                response = await handle(request)
            except RequestValidationError as exc:
                response = await request_validation_exception_handler(request, exc)
            except InvalidSession:
                raise HTTPException(401, "Authentication required.", headers=no_store) from None
            except BusinessNotFound:
                raise HTTPException(404, "Business not found", headers=no_store) from None
            except PermissionDenied:
                raise HTTPException(403, "Permission denied", headers=no_store) from None
            except SQLAlchemyError:
                raise HTTPException(503, "Database unavailable", headers=no_store) from None
            except StarletteHTTPException as exc:
                exc.headers = {**(exc.headers or {}), **no_store}
                raise
            response.headers.update(no_store)
            return response

        return handle_private


BUSINESS_ERRORS = {
    401: {"description": "Authentication required"},
    403: {"description": "Permission denied or invalid origin or CSRF token"},
    404: {"description": "Resource not found in the accessible business"},
    503: {"description": "Database unavailable"},
}
TENANT_ERRORS = {**BUSINESS_ERRORS, 400: {"description": "Missing or malformed X-Business-ID"}}
CsrfSession = Annotated[AuthContext, Depends(require_csrf)]


def business_selector(
    request: Request,
    value: Annotated[str | None, Header(alias="X-Business-ID", description="Required business UUID for scoped routes.")] = None,
) -> UUID:
    if value is not None and len(request.headers.getlist("X-Business-ID")) == 1:
        try:
            business_id = UUID(value)
        except ValueError:
            pass
        else:
            if str(business_id) == value.lower():
                return business_id
    raise HTTPException(400, "A valid X-Business-ID is required")


BusinessSelector = Annotated[UUID, Depends(business_selector)]


def read_tenant(session: CurrentSession, business_id: BusinessSelector, db: DatabaseSession) -> TenantContext:
    return get_tenant(db, business_id, session.user.id, session.session_id)


def write_tenant(session: CsrfSession, business_id: BusinessSelector, db: DatabaseSession) -> TenantContext:
    return get_tenant(db, business_id, session.user.id, session.session_id, for_write=True)


ReadTenant = Annotated[TenantContext, Depends(read_tenant)]
WriteTenant = Annotated[TenantContext, Depends(write_tenant)]


def readable_campaign(campaign_id: int, tenant: ReadTenant, db: DatabaseSession) -> Campaign:
    campaign = campaigns.get_campaign(db, tenant.business_id, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    return campaign


def campaign_for_write(db: DatabaseSession, tenant: TenantContext, campaign_id: int, role: str) -> Campaign:
    campaign = campaigns.get_campaign_for_update(db, tenant.business_id, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    require_role(tenant, role)
    return campaign


def editable_campaign(campaign_id: int, tenant: WriteTenant, db: DatabaseSession) -> Campaign:
    return campaign_for_write(db, tenant, campaign_id, "editor")


def deletable_campaign(campaign_id: int, tenant: WriteTenant, db: DatabaseSession) -> Campaign:
    return campaign_for_write(db, tenant, campaign_id, "owner")


def editor_tenant(tenant: WriteTenant) -> TenantContext:
    require_role(tenant, "editor")
    return tenant


ReadableCampaign = Annotated[Campaign, Depends(readable_campaign)]
EditableCampaign = Annotated[Campaign, Depends(editable_campaign)]
DeletableCampaign = Annotated[Campaign, Depends(deletable_campaign)]
EditorTenant = Annotated[TenantContext, Depends(editor_tenant)]
