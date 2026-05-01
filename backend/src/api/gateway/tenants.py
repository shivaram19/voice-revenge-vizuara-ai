"""
Gateway Tenant Routes
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from src.api.gateway.db import GatewayDB, Tenant
from src.api.gateway.models import TenantCreate, TenantOut

router = APIRouter(prefix="/gateway/v1/tenants", tags=["gateway-tenants"])
_db = GatewayDB()


@router.post("", response_model=TenantOut)
async def create_tenant(body: TenantCreate):
    existing = _db.get_tenant_by_id(body.tenant_id)
    if existing:
        raise HTTPException(status_code=409, detail="Tenant already exists")

    tenant = Tenant(
        id=None,
        tenant_id=body.tenant_id,
        name=body.name,
        district=body.district,
        admin_email=body.admin_email,
        student_count_range=body.student_count_range,
    )
    tid = _db.create_tenant(tenant)
    # Fetch back to get created_at
    created = _db.get_tenant_by_id(body.tenant_id)
    if created is None:
        raise HTTPException(status_code=500, detail="Failed to create tenant")
    return _to_out(created)


@router.get("/me", response_model=TenantOut)
async def get_my_tenant(tenant_id: str = "lincoln-high"):
    tenant = _db.get_tenant_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _to_out(tenant)


def _to_out(t: Tenant) -> TenantOut:
    return TenantOut(
        id=t.id,
        tenant_id=t.tenant_id,
        name=t.name,
        district=t.district,
        admin_email=t.admin_email,
        student_count_range=t.student_count_range,
        created_at=t.created_at,
    )
