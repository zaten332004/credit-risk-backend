"""
Customer service wrappers backed by the database intake service.
"""

from typing import List, Optional

from app.schemas.schemas import (
    CustomerCreate,
    CustomerHistoryItem,
    CustomerRead,
    CustomerSearchBody,
    CustomerUpdate,
    PaginatedCustomers,
)
from app.services import customer_intake_service


def list_customers(
    page: int = 1,
    limit: int = 20,
    search_name: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> PaginatedCustomers:
    return customer_intake_service.list_customers(
        page=page,
        limit=limit,
        search_name=search_name,
        risk_level=risk_level,
    )


def get_customer(customer_id: int) -> Optional[CustomerRead]:
    return customer_intake_service.get_customer(customer_id)


def create_customer(
    payload: CustomerCreate,
    created_by: str,
    created_by_user_id: Optional[int] = None,
) -> CustomerRead:
    return customer_intake_service.create_customer(
        payload,
        created_by=created_by,
        created_by_user_id=created_by_user_id,
    )


def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    updated_by: str,
    updated_by_user_id: Optional[int] = None,
) -> Optional[CustomerRead]:
    return customer_intake_service.update_customer(
        customer_id,
        payload,
        updated_by=updated_by,
        updated_by_user_id=updated_by_user_id,
    )


def update_customer_status(
    customer_id: int,
    application_status: str,
    updated_by: str,
    rejection_reason: Optional[str] = None,
    updated_by_user_id: Optional[int] = None,
) -> Optional[CustomerRead]:
    return customer_intake_service.update_customer(
        customer_id,
        CustomerUpdate(application_status=application_status, notes=rejection_reason),
        updated_by=updated_by,
        updated_by_user_id=updated_by_user_id,
    )


def delete_customer(customer_id: int, deleted_by_user_id: Optional[int] = None) -> bool:
    return customer_intake_service.delete_customer(customer_id, deleted_by_user_id=deleted_by_user_id)


def get_customer_history(customer_id: int) -> List[CustomerHistoryItem]:
    return customer_intake_service.get_customer_history(customer_id)


def advanced_customer_search(body: CustomerSearchBody) -> PaginatedCustomers:
    return customer_intake_service.advanced_customer_search(body)
