"""
Analytics data service: đọc dữ liệu từ cùng database mà Power BI dùng,
tổng hợp thành context cho AI (Gemini) phân tích theo yêu cầu người dùng.

Dữ liệu: portfolio, risk, customers, facilities — từ CreditRiskDB (hoặc DB
được cấu hình trong app.db.session).
"""

from __future__ import annotations

import logging
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    CustomerDB,
    LoanFacilityDB,
    PortfolioSnapshotDB,
    RiskPredictionDB,
)

logger = logging.getLogger(__name__)


def _safe_int(val: object) -> Optional[int]:
    try:
        if val is None:
            return None
        if isinstance(val, bool):
            return int(val)
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        return int(str(val).strip())
    except Exception:
        return None


def _format_number(val: object) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, int):
        return f"{val:,}"
    if isinstance(val, float):
        # Keep a few decimals only when needed
        if abs(val - round(val)) < 1e-9:
            return f"{int(round(val)):,}"
        return f"{val:,.4f}".rstrip("0").rstrip(".")
    s = str(val).strip()
    return s


def _extract_execute_queries_rows(result: dict) -> List[dict]:
    """
    Extract rows from Power BI executeQueries response.
    Expected shape: {"results":[{"tables":[{"rows":[...]}]}]}
    """
    try:
        results = result.get("results") or []
        if not results:
            return []
        tables = (results[0] or {}).get("tables") or []
        if not tables:
            return []
        rows = (tables[0] or {}).get("rows") or []
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
        return []
    except Exception:
        return []


def _format_ai_context_rows(
    rows: List[dict],
    table_name: str,
    required_keys: List[str],
    max_chars: int,
) -> str:
    prefix = f"{table_name}["
    key_col = f"{prefix}Key]"
    text_col = f"{prefix}TextValue]"
    number_col = f"{prefix}NumberValue]"
    updated_col = f"{prefix}UpdatedAt]"

    kv: dict[str, str] = {}
    updated_at: Optional[str] = None
    for r in rows:
        k = r.get(key_col)
        if not isinstance(k, str) or not k.strip():
            continue
        key = k.strip()
        tv = r.get(text_col)
        nv = r.get(number_col)
        if isinstance(tv, str) and tv.strip():
            value = tv.strip()
        elif nv is not None:
            value = _format_number(nv)
        else:
            value = ""
        kv[key] = value

        if updated_at is None:
            ua = r.get(updated_col)
            if isinstance(ua, str) and ua.strip():
                updated_at = ua.strip()

    missing = [k for k in required_keys if k and k not in kv]

    lines: List[str] = []
    lines.append("--- Power BI (direct) ---")
    if updated_at:
        lines.append(f"UpdatedAt: {updated_at}")
    if missing:
        lines.append(f"[WARN] Missing AI_Context keys: {', '.join(missing)}")

    if not kv:
        lines.append("(AI_Context returned 0 rows)")
        return "\n".join(lines)

    lines.append("Context:")
    for k in sorted(kv.keys()):
        v = kv[k]
        if v == "":
            lines.append(f"- {k}")
        else:
            lines.append(f"- {k}: {v}")

    out = "\n".join(lines)
    if max_chars and len(out) > max_chars:
        out = out[: max_chars - 3] + "..."
    return out


def _decimal_to_float(val: Any) -> Any:
    if isinstance(val, Decimal):
        return float(val)
    return val


def get_portfolio_summary(session: Session) -> Dict[str, Any]:
    """Tổng quan danh mục: exposure, NPL, số facility, số khách hàng."""
    out: Dict[str, Any] = {
        "total_exposure": 0.0,
        "npl_ratio": None,
        "total_npl": 0.0,
        "total_facilities": 0,
        "total_customers": 0,
        "active_facilities": 0,
    }
    try:
        # Portfolio_Snapshot: lấy bản ghi mới nhất (nếu có)
        latest = (
            session.query(PortfolioSnapshotDB)
            .order_by(PortfolioSnapshotDB.snapshot_date.desc())
            .limit(1)
            .first()
        )
        if latest:
            out["total_exposure"] = _decimal_to_float(latest.total_exposure) or 0.0
            out["npl_ratio"] = _decimal_to_float(latest.npl_ratio)
            out["total_npl"] = _decimal_to_float(latest.total_npl) or 0.0

        # Từ Loan_Facility: tổng dư nợ (approved_amount), đếm facility/customer
        row = (
            session.query(
                func.count(LoanFacilityDB.facility_id).label("cnt"),
                func.count(func.distinct(LoanFacilityDB.customer_id)).label("customers"),
                func.coalesce(func.sum(LoanFacilityDB.approved_amount), 0).label("total"),
            )
        ).first()
        if row and (row.total or 0) > 0:
            out["total_exposure"] = out["total_exposure"] or _decimal_to_float(row.total)
            out["total_facilities"] = row.cnt or 0
            out["total_customers"] = row.customers or 0
        active_count = (
            session.query(func.count(LoanFacilityDB.facility_id))
            .filter(LoanFacilityDB.status == "active")
            .scalar()
        )
        out["active_facilities"] = active_count or 0
    except Exception as e:
        logger.warning("get_portfolio_summary failed: %s", e)
    return out


def get_risk_overview(session: Session) -> Dict[str, Any]:
    """Phân bố rủi ro: theo risk_level (RISK_PREDICTION) và theo status facility."""
    out: Dict[str, Any] = {
        "by_risk_level": {},
        "by_facility_status": {},
        "high_risk_count": 0,
    }
    try:
        # RISK_PREDICTION: đếm theo risk_level
        rows = (
            session.query(RiskPredictionDB.risk_level, func.count(RiskPredictionDB.prediction_id))
            .filter(RiskPredictionDB.risk_level.isnot(None))
            .group_by(RiskPredictionDB.risk_level)
            .all()
        )
        for level, cnt in rows:
            out["by_risk_level"][str(level).lower()] = cnt
            if str(level).lower() == "high":
                out["high_risk_count"] = cnt

        # Loan_Facility: đếm theo status (active, closed, arrears)
        status_rows = (
            session.query(LoanFacilityDB.status, func.count(LoanFacilityDB.facility_id))
            .group_by(LoanFacilityDB.status)
            .all()
        )
        for st, cnt in status_rows:
            out["by_facility_status"][str(st)] = cnt
    except Exception as e:
        logger.warning("get_risk_overview failed: %s", e)
    return out


def get_top_customers_by_exposure(
    session: Session,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Top khách hàng theo tổng dư nợ (approved_amount)."""
    result: List[Dict[str, Any]] = []
    try:
        rows = (
            session.query(
                CustomerDB.customer_id,
                CustomerDB.full_name,
                CustomerDB.credit_score,
                func.coalesce(func.sum(LoanFacilityDB.approved_amount), 0).label("total_exposure"),
            )
            .join(LoanFacilityDB, LoanFacilityDB.customer_id == CustomerDB.customer_id)
            .group_by(CustomerDB.customer_id, CustomerDB.full_name, CustomerDB.credit_score)
            .order_by(func.sum(LoanFacilityDB.approved_amount).desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            result.append({
                "customer_id": r.customer_id,
                "full_name": r.full_name or "",
                "credit_score": r.credit_score,
                "total_exposure": _decimal_to_float(r.total_exposure),
            })
    except Exception as e:
        logger.warning("get_top_customers_by_exposure failed: %s", e)
    return result


def get_analysis_context(
    session: Session,
    include_portfolio: bool = True,
    include_risk: bool = True,
    include_top_customers: bool = True,
    top_customers_limit: int = 10,
) -> str:
    """
    Thu thập dữ liệu từ DB (cùng nguồn Power BI), format thành đoạn text
    để đưa vào prompt cho Gemini phân tích theo câu hỏi người dùng.
    """
    parts: List[str] = []

    if include_portfolio:
        summary = get_portfolio_summary(session)
        parts.append("--- Tổng quan danh mục ---")
        parts.append(f"Tổng exposure: {summary['total_exposure']:,.0f} VND")
        if summary.get("npl_ratio") is not None:
            parts.append(f"NPL ratio: {summary['npl_ratio']:.2%}")
        parts.append(f"Tổng NPL: {summary['total_npl']:,.0f} VND")
        parts.append(f"Số facility: {summary['total_facilities']} (active: {summary['active_facilities']})")
        parts.append(f"Số khách hàng có facility: {summary['total_customers']}")

    if include_risk:
        risk = get_risk_overview(session)
        parts.append("\n--- Phân bố rủi ro ---")
        if risk["by_risk_level"]:
            for level, cnt in risk["by_risk_level"].items():
                parts.append(f"  Risk level '{level}': {cnt} dự báo")
        else:
            parts.append("  (Chưa có dữ liệu risk level)")
        if risk["by_facility_status"]:
            for st, cnt in risk["by_facility_status"].items():
                parts.append(f"  Facility status '{st}': {cnt}")
        parts.append(f"Số lượng high risk: {risk['high_risk_count']}")

    if include_top_customers:
        top = get_top_customers_by_exposure(session, limit=top_customers_limit)
        parts.append("\n--- Top khách hàng theo exposure ---")
        if top:
            for i, c in enumerate(top, 1):
                parts.append(
                    f"  {i}. {c['full_name']} (ID: {c['customer_id']}): "
                    f"{c['total_exposure']:,.0f} VND, credit_score={c['credit_score']}"
                )
        else:
            parts.append("  (Chưa có dữ liệu)")

    if not parts:
        return "Hiện chưa có dữ liệu tổng hợp từ hệ thống."
    return "\n".join(parts)


def get_analysis_context_powerbi() -> str:
    """
    Collect context directly from Power BI (via REST API + service principal).

    Requires env/.env (or settings):
    - POWER_BI_TENANT_ID
    - POWER_BI_CLIENT_ID
    - POWER_BI_CLIENT_SECRET
    - POWER_BI_WORKSPACE_ID
    - POWER_BI_DATASET_ID
    """
    try:
        from app.services.powerbi_service import powerbi_service

        if not (
            (settings.power_bi_tenant_id or "").strip()
            and (settings.power_bi_client_id or "").strip()
            and (settings.power_bi_client_secret or "").strip()
            and (settings.power_bi_workspace_id or "").strip()
            and (settings.power_bi_dataset_id or "").strip()
        ):
            return (
                "Power BI chưa được cấu hình cho backend. "
                "Hãy set POWER_BI_TENANT_ID/CLIENT_ID/CLIENT_SECRET/WORKSPACE_ID/DATASET_ID trong .env."
            )

        dax = (settings.power_bi_ai_context_dax or "").strip()
        if not dax:
            # Approach A: read from a fixed "contract" table inside the dataset
            table_name = (settings.power_bi_ai_context_table or "AI_Context").strip()
            if not table_name:
                table_name = "AI_Context"
            max_rows = int(getattr(settings, "power_bi_ai_context_max_rows", 200) or 200)
            if max_rows <= 0:
                max_rows = 200

            # Contract expectation: a table named `AI_Context` (configurable) with at least a [Key] column.
            # Recommended columns: [Key], [TextValue], [NumberValue], [UpdatedAt].
            escaped_table = table_name.replace("'", "''")
            dax = f"EVALUATE TOPN({max_rows}, '{escaped_table}', '{escaped_table}'[Key], ASC)"

        result = powerbi_service.execute_dax_query_global_verbose(dax)
        if result.get("ok"):
            table_name = (settings.power_bi_ai_context_table or "AI_Context").strip() or "AI_Context"
            required_raw = (settings.power_bi_ai_context_required_keys or "").strip()
            required_keys = [k.strip() for k in required_raw.split(",") if k.strip()]
            max_chars = _safe_int(getattr(settings, "power_bi_ai_context_max_chars", 4000)) or 4000

            rows = _extract_execute_queries_rows(result.get("result") or {})
            return _format_ai_context_rows(rows=rows, table_name=table_name, required_keys=required_keys, max_chars=max_chars)

        return (
            "--- Power BI (direct) ---\n"
            "Context error:\n"
            + json.dumps(result, ensure_ascii=False)[:1200]
            + "\n\n"
            "Gợi ý (Approach A): Tạo 1 calculated table `AI_Context` trong Power BI dataset với cột [Key] (và [TextValue]/[NumberValue]). "
            "Backend sẽ query table này mà không cần biết schema các bảng khác."
        )
    except Exception as e:
        logger.warning("get_analysis_context_powerbi failed: %s", e)
        return f"Power BI direct context error: {str(e)}"
