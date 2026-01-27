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
    CustomerUpdate,
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
    min_pd: Optional[float] = None,  # demo, chưa dùng
    current_user: User = Depends(get_current_active_user),
) -> PaginatedCustomers:
    return customer_service.list_customers(page=page, limit=limit, search_name=search_name, risk_level=risk_level)


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
    return customer_service.create_customer(body, created_by=current_user.email)


@router.put("/customers/{customer_id}", response_model=CustomerRead, tags=["customers"])
async def update_customer_endpoint(
    customer_id: int,
    body: CustomerUpdate,
    current_user: User = Depends(get_current_active_user),
) -> CustomerRead:
    updated = customer_service.update_customer(customer_id, body, updated_by=current_user.email)
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated


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
