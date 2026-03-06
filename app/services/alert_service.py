"""
Alert service: business logic for alerts & notifications
"""
from typing import Dict, List, Optional

from app.models.models import Alert
from app.schemas.schemas import AlertRead, AlertResolveBody, AlertSubscriptionCreate, AlertSubscriptionRead

# In-memory "repositories" cho demo
_alerts: Dict[int, Alert] = {}
_alert_subscriptions: List[AlertSubscriptionRead] = []
_id_counters: Dict[str, int] = {"alert": 0, "subscription": 0}


def _next_id(key: str) -> int:
    _id_counters[key] = _id_counters.get(key, 0) + 1
    return _id_counters[key]


def list_alerts(status: Optional[str], type_: Optional[str]) -> List[AlertRead]:
    alerts = list(_alerts.values())
    if status:
        alerts = [a for a in alerts if a.status == status]
    if type_:
        alerts = [a for a in alerts if a.type == type_]
    return [
        AlertRead(
            id=a.id,
            type=a.type,
            status=a.status,
            message=a.message,
            created_at=a.created_at,
        )
        for a in alerts
    ]


def subscribe_alerts(body: AlertSubscriptionCreate) -> AlertSubscriptionRead:
    sid = _next_id("subscription")
    sub = AlertSubscriptionRead(subscription_id=sid)
    _alert_subscriptions.append(sub)
    return sub


def resolve_alert(alert_id: int, body: AlertResolveBody) -> Optional[AlertRead]:
    alert = _alerts.get(alert_id)
    if not alert:
        return None
    alert.status = "resolved"
    return AlertRead(
        id=alert.id,
        type=alert.type,
        status=alert.status,
        message=f"{alert.message} (resolved: {body.reason})",
        created_at=alert.created_at,
    )
