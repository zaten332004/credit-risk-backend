"""
Customer management endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_active_user
from app.schemas.schemas import (
    CustomerCreate,
    CustomerHistoryItem,
    CustomerRead,
    CustomerSearchBody,
    CustomerStatusUpdateBody,
    CustomerUpdate,
    MessageResponse,
    PaginatedCustomers,
    User,
)
from app.services import customer_service

router = APIRouter()


@router.get("/customers", response_model=PaginatedCustomers, tags=["customers"])
async def list_customers_endpoint(
    page: int = 1,
    limit: int = 20,
    search_name: Optional[str] = None,
    risk_level: Optional[str] = None,
    application_status: Optional[str] = None,
    min_pd: Optional[float] = None,  # demo, chưa dùng
    current_user: User = Depends(get_current_active_user),
) -> PaginatedCustomers:
    return customer_service.list_customers(
        page=page,
        limit=limit,
        search_name=search_name,
        risk_level=risk_level,
        application_status=application_status,
    )


@router.get("/customers/{customer_id}", response_model=CustomerRead, tags=["customers"])
async def get_customer_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> CustomerRead:
    customer = customer_service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/customers", response_model=CustomerRead, status_code=201, tags=["customers"])
async def create_customer_endpoint(
    body: CustomerCreate,
    current_user: User = Depends(get_current_active_user),
) -> CustomerRead:
    return customer_service.create_customer(
        body,
        created_by=current_user.email,
        created_by_user_id=current_user.id,
    )


@router.put("/customers/{customer_id}", response_model=CustomerRead, tags=["customers"])
async def update_customer_endpoint(
    customer_id: int,
    body: CustomerUpdate,
    current_user: User = Depends(get_current_active_user),
) -> CustomerRead:
    updated = customer_service.update_customer(
        customer_id,
        body,
        updated_by=current_user.email,
        updated_by_user_id=current_user.id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated


@router.patch("/customers/{customer_id}/status", response_model=CustomerRead, tags=["customers"])
async def update_customer_status_endpoint(
    customer_id: int,
    body: CustomerStatusUpdateBody,
    current_user: User = Depends(get_current_active_user),
) -> CustomerRead:
    updated = customer_service.update_customer_status(
        customer_id,
        application_status=body.application_status,
        rejection_reason=body.rejection_reason,
        updated_by=current_user.email,
        updated_by_user_id=current_user.id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated


@router.delete("/customers/{customer_id}", response_model=MessageResponse, tags=["customers"])
async def delete_customer_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    deleted = customer_service.delete_customer(customer_id, deleted_by_user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return MessageResponse(message="Đã xóa hồ sơ khách hàng.")


@router.get("/customers/{customer_id}/history", response_model=List[CustomerHistoryItem], tags=["customers"])
async def customer_history_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> List[CustomerHistoryItem]:
    return customer_service.get_customer_history(customer_id)


@router.post("/customers/search", response_model=PaginatedCustomers, tags=["customers"])
async def customer_search_endpoint(
    body: CustomerSearchBody,
    current_user: User = Depends(get_current_active_user),
) -> PaginatedCustomers:
    return customer_service.advanced_customer_search(body)
