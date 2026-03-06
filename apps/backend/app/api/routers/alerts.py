"""
Alerts & notifications endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_active_user
from app.schemas.schemas import AlertRead, AlertResolveBody, AlertSubscriptionCreate, AlertSubscriptionRead, User
from app.services import alert_service

router = APIRouter()


@router.get("/alerts", response_model=List[AlertRead], tags=["alerts"])
async def alerts_list_endpoint(
    status: Optional[str] = None,
    type: Optional[str] = None,  # type: ignore[assignment]
    current_user: User = Depends(get_current_active_user),
) -> List[AlertRead]:
    return alert_service.list_alerts(status=status, type_=type)


@router.post("/alerts/subscribe", response_model=AlertSubscriptionRead, tags=["alerts"])
async def alerts_subscribe_endpoint(
    body: AlertSubscriptionCreate,
    current_user: User = Depends(get_current_active_user),
) -> AlertSubscriptionRead:
    return alert_service.subscribe_alerts(body)


@router.put("/alerts/{alert_id}/resolve", response_model=AlertRead, tags=["alerts"])
async def alerts_resolve_endpoint(
    alert_id: int,
    body: AlertResolveBody,
    current_user: User = Depends(get_current_active_user),
) -> AlertRead:
    result = alert_service.resolve_alert(alert_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result
