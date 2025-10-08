# app/routers/services.py
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models.service import ServiceStatus
from ..repositories.service_repo import ServiceRepository
from ..schemas.service import ServiceCreate, ServiceUpdate, ServiceOut, PagedServiceOut

router = APIRouter()

def get_repo(session: AsyncSession = Depends(get_session)) -> ServiceRepository:
    return ServiceRepository(session)


@router.get("", response_model=PagedServiceOut)
async def list_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    name: Optional[str] = None,
    unit: Optional[str] = None,
    status: Optional[ServiceStatus] = None,
    min_price: Optional[Decimal] = Query(None, ge=0),
    max_price: Optional[Decimal] = Query(None, ge=0),
    repo: ServiceRepository = Depends(get_repo),
):
    filters: Dict[str, Any] = {
        "name": name,
        "unit": unit,
        "status": status,
        "min_price": min_price,
        "max_price": max_price,
    }
    total = await repo.count(filters)
    items = await repo.list(skip=skip, limit=limit, filters=filters)
    return PagedServiceOut(total=total, skip=skip, limit=limit, items=items)


@router.get("/_active/list", response_model=List[ServiceOut])
async def list_active_services(repo: ServiceRepository = Depends(get_repo)):
    return await repo.get_active_services()


@router.get("/{service_id}", response_model=ServiceOut)
async def get_service(service_id: int, repo: ServiceRepository = Depends(get_repo)):
    svc = await repo.get(service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return svc


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
async def create_service(payload: ServiceCreate, repo: ServiceRepository = Depends(get_repo)):
    existed = await repo.get_by_name(payload.name)
    if existed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Service name already exists")
    service = await repo.create(payload.model_dump(exclude_unset=True))
    return service


@router.put("/{service_id}", response_model=ServiceOut)
async def update_service(service_id: int, payload: ServiceUpdate, repo: ServiceRepository = Depends(get_repo)):
    data = payload.model_dump(exclude_unset=True)
    new_name = data.get("name")
    if new_name:
        existed = await repo.get_by_name(new_name)
        if existed and existed.id != service_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Service name already exists")
    updated = await repo.update(service_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return updated


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(service_id: int, repo: ServiceRepository = Depends(get_repo)):
    try:
        ok = await repo.delete(service_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return None
