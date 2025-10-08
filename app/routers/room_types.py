from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from decimal import Decimal

from ..db import get_session
from ..models.user import User
from ..models.room_type import RoomType
from ..schemas.room_type import RoomTypeCreate, RoomTypeUpdate, RoomTypeOut
from ..repositories.room_type_repo import RoomTypeRepository
from ..dependencies import get_current_user, require_manager, require_receptionist

router = APIRouter()

@router.get("", response_model=List[RoomTypeOut])
async def list_room_types(
    skip: int = Query(0, ge=0, description="Số bản ghi bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số bản ghi tối đa"),
    code: Optional[str] = Query(None, description="Lọc theo mã loại phòng"),
    name: Optional[str] = Query(None, description="Lọc theo tên loại phòng"),
    base_occupancy: Optional[int] = Query(None, ge=1, description="Lọc theo sức chứa cơ bản"),
    max_occupancy: Optional[int] = Query(None, ge=1, description="Lọc theo sức chứa tối đa"),
    min_base_rate: Optional[Decimal] = Query(None, ge=0, description="Lọc theo giá cơ bản tối thiểu"),
    max_base_rate: Optional[Decimal] = Query(None, ge=0, description="Lọc theo giá cơ bản tối đa"),
    current_user: User = Depends(require_receptionist),
    session: AsyncSession = Depends(get_session)
):
    room_type_repo = RoomTypeRepository(session)
    
    filters = {}
    if code:
        filters["code"] = code
    if name:
        filters["name"] = name
    if base_occupancy is not None:
        filters["base_occupancy"] = base_occupancy
    if max_occupancy is not None:
        filters["max_occupancy"] = max_occupancy
    if min_base_rate is not None:
        filters["min_base_rate"] = min_base_rate
    if max_base_rate is not None:
        filters["max_base_rate"] = max_base_rate
    
    room_types = await room_type_repo.list(skip=skip, limit=limit, filters=filters)
    return room_types

@router.get("/{room_type_id}", response_model=RoomTypeOut)
async def get_room_type(
    room_type_id: int,
    current_user: User = Depends(require_receptionist),
    session: AsyncSession = Depends(get_session)
):
    """Lấy thông tin chi tiết loại phòng."""
    room_type_repo = RoomTypeRepository(session)
    
    room_type = await room_type_repo.get(room_type_id)
    if not room_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy loại phòng"
        )
    
    return room_type

@router.post("", response_model=RoomTypeOut, status_code=status.HTTP_201_CREATED)
async def create_room_type(
    room_type_data: RoomTypeCreate,
    current_user: User = Depends(require_manager),
    session: AsyncSession = Depends(get_session)
):
    """Tạo loại phòng mới."""
    room_type_repo = RoomTypeRepository(session)
    
    # Kiểm tra mã code đã tồn tại chưa
    existing_room_type = await room_type_repo.get_by_code(room_type_data.code)
    if existing_room_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã loại phòng đã tồn tại"
        )
    
    # Kiểm tra sức chứa hợp lệ
    if room_type_data.max_occupancy < room_type_data.base_occupancy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sức chứa tối đa phải lớn hơn hoặc bằng sức chứa cơ bản"
        )
    
    # Tạo loại phòng mới
    room_type_dict = room_type_data.model_dump()
    room_type_dict["created_by"] = current_user.id
    
    room_type = await room_type_repo.create(room_type_dict)
    return room_type

@router.put("/{room_type_id}", response_model=RoomTypeOut)
async def update_room_type(
    room_type_id: int,
    room_type_data: RoomTypeUpdate,
    current_user: User = Depends(require_manager),
    session: AsyncSession = Depends(get_session)
):
    room_type_repo = RoomTypeRepository(session)
    
    existing_room_type = await room_type_repo.get(room_type_id)
    if not existing_room_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy loại phòng"
        )
    
    if room_type_data.code and room_type_data.code != existing_room_type.code:
        code_exists = await room_type_repo.get_by_code(room_type_data.code)
        if code_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã loại phòng đã tồn tại"
            )
    
    base_occupancy = room_type_data.base_occupancy or existing_room_type.base_occupancy
    max_occupancy = room_type_data.max_occupancy or existing_room_type.max_occupancy
    
    if max_occupancy < base_occupancy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sức chứa tối đa phải lớn hơn hoặc bằng sức chứa cơ bản"
        )
    
    update_data = room_type_data.model_dump(exclude_unset=True)
    update_data["updated_by"] = current_user.id
    
    updated_room_type = await room_type_repo.update(room_type_id, update_data)
    return updated_room_type

@router.delete("/{room_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_type(
    room_type_id: int,
    current_user: User = Depends(require_manager),
    session: AsyncSession = Depends(get_session)
):
    room_type_repo = RoomTypeRepository(session)
    
    existing_room_type = await room_type_repo.get(room_type_id)
    if not existing_room_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy loại phòng"
        )
    
    try:
        success = await room_type_repo.delete(room_type_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể xóa loại phòng"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{room_type_id}/rooms", response_model=List[dict])
async def get_room_type_rooms(
    room_type_id: int,
    current_user: User = Depends(require_receptionist),
    session: AsyncSession = Depends(get_session)
):
    room_type_repo = RoomTypeRepository(session)
    
    room_type = await room_type_repo.get(room_type_id)
    if not room_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy loại phòng"
        )
    
    from ..repositories.room_repo import RoomRepository
    room_repo = RoomRepository(session)
    rooms = await room_repo.list(filters={"room_type_id": room_type_id})
    
    return [
        {
            "id": room.id,
            "name": room.name,
            "status": room.status.value,
            "housekeeping_status": room.housekeeping_status.value,
            "description": room.description
        }
        for room in rooms
    ]

@router.get("/{room_type_id}/bookings", response_model=List[dict])
async def get_room_type_bookings(
    room_type_id: int,
    current_user: User = Depends(require_receptionist),
    session: AsyncSession = Depends(get_session)
):
    room_type_repo = RoomTypeRepository(session)
    
    # Kiểm tra loại phòng tồn tại
    room_type = await room_type_repo.get(room_type_id)
    if not room_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy loại phòng"
        )
    
    from ..repositories.booking_repo import BookingRepository
    booking_repo = BookingRepository(session)
    bookings = await booking_repo.list(filters={"room_type_id": room_type_id})
    
    return [
        {
            "id": booking.id,
            "booking_no": booking.booking_no,
            "status": booking.status.value,
            "payment_status": booking.payment_status.value,
            "checkin": booking.checkin,
            "checkout": booking.checkout,
            "num_adults": booking.num_adults,
            "num_children": booking.num_children
        }
        for booking in bookings
    ]