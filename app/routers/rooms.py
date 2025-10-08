# app/routers/rooms.py
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models.room import RoomStatus, HousekeepingStatus
from ..repositories.room_repo import RoomRepository
from ..schemas.room import (
    RoomCreate,
    RoomUpdate,
    RoomOut,
    PagedRoomOut,
    RoomStatusUpdate,
    HousekeepingStatusUpdate,
)

router = APIRouter()


def get_repo(session: AsyncSession = Depends(get_session)) -> RoomRepository:
    return RoomRepository(session)


@router.get("", response_model=PagedRoomOut)
async def list_rooms(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    name: Optional[str] = None,
    room_type_id: Optional[int] = None,
    status: Optional[RoomStatus] = None,
    housekeeping_status: Optional[HousekeepingStatus] = None,
    repo: RoomRepository = Depends(get_repo),
):
    filters: Dict[str, Any] = {
        "name": name,
        "room_type_id": room_type_id,
        "status": status,
        "housekeeping_status": housekeeping_status,
    }
    total = await repo.count(filters)
    items = await repo.list(skip=skip, limit=limit, filters=filters)
    return PagedRoomOut(total=total, skip=skip, limit=limit, items=items)


@router.get("/{room_id}", response_model=RoomOut)
async def get_room(room_id: int, repo: RoomRepository = Depends(get_repo)):
    room = await repo.get(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return room


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, repo: RoomRepository = Depends(get_repo)):
    existed = await repo.get_by_name(payload.name)
    if existed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Room name already exists"
        )
    room = await repo.create(payload.model_dump(exclude_unset=True))
    return room


@router.put("/{room_id}", response_model=RoomOut)
async def update_room(
    room_id: int, payload: RoomUpdate, repo: RoomRepository = Depends(get_repo)
):
    data = payload.model_dump(exclude_unset=True)
    new_name = data.get("name")
    if new_name:
        existed = await repo.get_by_name(new_name)
        if existed and existed.id != room_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Room name already exists"
            )
    updated = await repo.update(room_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return updated


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(room_id: int, repo: RoomRepository = Depends(get_repo)):
    try:
        ok = await repo.delete(room_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return None


@router.get("/_available/list", response_model=List[RoomOut])
async def list_available_rooms(
    room_type_id: Optional[int] = None, repo: RoomRepository = Depends(get_repo)
):
    return await repo.get_available_rooms(room_type_id=room_type_id)


@router.get("/status/{status}", response_model=List[RoomOut])
async def list_by_status(status: RoomStatus, repo: RoomRepository = Depends(get_repo)):
    return await repo.get_rooms_by_status(status)


@router.get("/housekeeping/{housekeeping_status}", response_model=List[RoomOut])
async def list_by_housekeeping(
    housekeeping_status: HousekeepingStatus, repo: RoomRepository = Depends(get_repo)
):
    return await repo.get_rooms_by_housekeeping_status(housekeeping_status)


@router.patch("/{room_id}/status", response_model=RoomOut)
async def update_room_status(
    room_id: int, payload: RoomStatusUpdate, repo: RoomRepository = Depends(get_repo)
):
    updated = await repo.update_status(room_id, payload.status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return updated


@router.patch("/{room_id}/housekeeping", response_model=RoomOut)
async def update_room_housekeeping(
    room_id: int,
    payload: HousekeepingStatusUpdate,
    repo: RoomRepository = Depends(get_repo),
):
    updated = await repo.update_housekeeping_status(
        room_id, payload.housekeeping_status
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return updated
