# api/routes/orders.py
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models import User
from repositories.order_repository import OrderRepository
from schemas.order import (
    InitiateReturnRequest,
    LockerShipmentResponse,
    MessageResponse,
    OrderResponse,
)

router = APIRouter(tags=["Orders"])


@router.get("", response_model=List[OrderResponse])
async def get_user_orders(
    status: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ✅ GET /api/orders

    Zwraca listę zamówień użytkownika (aktywne + historia).
    Opcjonalne filtrowanie po statusie.
    """
    orders = await OrderRepository.get_user_orders(db, user.id, status)
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_details(
    order_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ✅ GET /api/orders/{order_id}

    Zwraca szczegóły zamówienia ze shipmentem.
    """
    order = await OrderRepository.get_order_by_id(db, order_id, user.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/confirm-pickup", response_model=MessageResponse)
async def confirm_pickup(
    order_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ✅ POST /api/orders/{order_id}/confirm-pickup

    Potwierdza odbiór książek z książkomatu.
    Zmienia status: ready_for_pickup → picked_up
    """
    await OrderRepository.confirm_pickup(db, order_id, user.id)
    return MessageResponse(message="Pickup confirmed successfully")


@router.post("/{order_id}/initiate-return", response_model=LockerShipmentResponse)
async def initiate_return(
    order_id: UUID,
    request: InitiateReturnRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ✅ POST /api/orders/{order_id}/initiate-return

    Inicjuje zwrot książek:
    1. Sprawdza czy order ma status 'picked_up'
    2. Znajduje dostępną skrytkę w wybranym lockerze
    3. Tworzy shipment typu 'return' z pickup_code
    4. Zmienia status: picked_up → return_in_progress
    """
    shipment = await OrderRepository.initiate_return(db, order_id, user.id, request.locker_id)
    return shipment


@router.post("/{order_id}/confirm-return", response_model=MessageResponse)
async def confirm_return(
    order_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ✅ POST /api/orders/{order_id}/confirm-return

    Potwierdza umieszczenie książek w książkomacie (zwrot).
    Zmienia status shipmentu: created → placed_in_locker
    """
    await OrderRepository.confirm_return(db, order_id, user.id)
    return MessageResponse(message="Return confirmed successfully")
