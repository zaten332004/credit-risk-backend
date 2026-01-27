"""
Customer service: business logic for customer management
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.models import Customer
from app.schemas.schemas import CustomerCreate, CustomerHistoryItem, CustomerRead, CustomerSearchBody, CustomerUpdate, PaginatedCustomers

# In-memory "repository" cho demo, thay bằng DB trong production
_customers: Dict[int, Customer] = {}
_customer_histories: Dict[int, List[CustomerHistoryItem]] = {}
_id_counters: Dict[str, int] = {"customer": 0}


def _next_id(key: str) -> int:
    _id_counters[key] = _id_counters.get(key, 0) + 1
    return _id_counters[key]


def list_customers(
    page: int = 1,
    limit: int = 20,
    search_name: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> PaginatedCustomers:
    items = list(_customers.values())
    if search_name:
        items = [c for c in items if search_name.lower() in c.name.lower()]
    if risk_level:
        items = [c for c in items if c.risk_level == risk_level]

    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    page_items = [CustomerRead(**c.model_dump()) for c in items[start:end]]
    return PaginatedCustomers(items=page_items, total=total, page=page, limit=limit)


def get_customer(customer_id: int) -> Optional[CustomerRead]:
    c = _customers.get(customer_id)
    return CustomerRead(**c.model_dump()) if c else None


def create_customer(payload: CustomerCreate, created_by: str) -> CustomerRead:
    now = datetime.utcnow()
    cid = _next_id("customer")
    customer = Customer(
        id=cid,
        name=payload.name,
        age=payload.age,
        income=payload.income,
        credit_score=payload.credit_score,
        risk_level="medium",
        last_updated=now,
    )
    _customers[cid] = customer
    _customer_histories.setdefault(cid, []).append(
        CustomerHistoryItem(timestamp=now, changed_by=created_by, changes=payload.model_dump())
    )
    return CustomerRead(**customer.model_dump())


def update_customer(customer_id: int, payload: CustomerUpdate, updated_by: str) -> Optional[CustomerRead]:
    if customer_id not in _customers:
        return None
    current = _customers[customer_id]
    data = current.model_dump()
    changes: Dict[str, Any] = {}
    for field, value in payload.model_dump(exclude_unset=True).items():
        data[field] = value
        changes[field] = value
    data["last_updated"] = datetime.utcnow()
    updated = Customer(**data)
    _customers[customer_id] = updated
    _customer_histories.setdefault(customer_id, []).append(
        CustomerHistoryItem(timestamp=data["last_updated"], changed_by=updated_by, changes=changes)
    )
    return CustomerRead(**updated.model_dump())


def get_customer_history(customer_id: int) -> List[CustomerHistoryItem]:
    return _customer_histories.get(customer_id, [])


def advanced_customer_search(body: CustomerSearchBody) -> PaginatedCustomers:
    # Demo: chỉ dùng list_customers, thực tế sẽ parse filters phức tạp
    return list_customers(page=body.page, limit=body.limit)
