# app/routers/guests.py
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models.guest import Gender
from ..repositories.guest_repo import GuestRepository
from ..schemas.guest import GuestCreate, GuestUpdate, GuestOut, PagedGuestOut

router = APIRouter()


def get_repo(session: AsyncSession = Depends(get_session)) -> GuestRepository:
    return GuestRepository(session)


@router.get("", response_model=PagedGuestOut)
async def list_guests(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    gender: Optional[Gender] = None,
    nationality: Optional[str] = None,
    repo: GuestRepository = Depends(get_repo),
):
    filters: Dict[str, Any] = {
        "name": name,
        "phone": phone,
        "email": email,
        "gender": gender,
        "nationality": nationality,
    }
    total = await repo.count(filters)
    items = await repo.list(skip=skip, limit=limit, filters=filters)
    return PagedGuestOut(total=total, skip=skip, limit=limit, items=items)


@router.get("/search/name", response_model=List[GuestOut])
async def search_by_name(name: str, repo: GuestRepository = Depends(get_repo)):
    return await repo.search_by_name(name)


@router.get("/search/phone", response_model=List[GuestOut])
async def search_by_phone(phone: str, repo: GuestRepository = Depends(get_repo)):
    return await repo.search_by_phone(phone)


@router.get("/nationality/{nationality}", response_model=List[GuestOut])
async def get_by_nationality(
    nationality: str, repo: GuestRepository = Depends(get_repo)
):
    return await repo.get_guests_by_nationality(nationality)


@router.get("/{guest_id}", response_model=GuestOut)
async def get_guest(guest_id: int, repo: GuestRepository = Depends(get_repo)):
    guest = await repo.get(guest_id)
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found"
        )
    return guest


@router.post("", response_model=GuestOut, status_code=status.HTTP_201_CREATED)
async def create_guest(payload: GuestCreate, repo: GuestRepository = Depends(get_repo)):
    if payload.phone:
        existed_phone = await repo.get_by_phone(payload.phone)
        if existed_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Phone already exists"
            )
    if payload.email:
        existed_email = await repo.get_by_email(payload.email)
        if existed_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already exists"
            )
    guest = await repo.create(payload.model_dump(exclude_unset=True))
    return guest


@router.put("/{guest_id}", response_model=GuestOut)
async def update_guest(
    guest_id: int, payload: GuestUpdate, repo: GuestRepository = Depends(get_repo)
):
    data = payload.model_dump(exclude_unset=True)
    if "phone" in data:
        existed = await repo.get_by_phone(data["phone"])
        if existed and existed.id != guest_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Phone already exists"
            )
    if "email" in data:
        existed = await repo.get_by_email(data["email"])
        if existed and existed.id != guest_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already exists"
            )
    updated = await repo.update(guest_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found"
        )
    return updated


@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest(guest_id: int, repo: GuestRepository = Depends(get_repo)):
    try:
        ok = await repo.delete(guest_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found"
        )
    return None
