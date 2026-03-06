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
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    CustomerDB,
    LoanFacilityDB,
    PortfolioSnapshotDB,
    RiskPredictionDB,
)
from app.db.session import Base

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


def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for v in values:
        k = (v or "").strip()
        if not k:
            continue
        lk = k.lower()
        if lk in seen:
            continue
        seen.add(lk)
        out.append(k)
    return out


def _extract_names_from_rows(rows: List[dict], kind: str) -> List[str]:
    keywords = ("table", "name") if kind == "table" else ("column", "name")
    out: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            if not isinstance(value, str):
                continue
            k = (key or "").lower()
            if any(w in k for w in keywords):
                out.append(value.strip())
    return _dedupe_keep_order(out)


def _extract_table_names(payload: Dict[str, Any]) -> List[str]:
    out: List[str] = []

    # Push dataset shape: {"value":[{"name":"..."}, ...]}
    for item in (payload.get("value") or []):
        if isinstance(item, dict):
            name = (item.get("name") or item.get("tableName") or "").strip()
            if name:
                out.append(name)

    rows = _extract_execute_queries_rows(payload)
    out.extend(_extract_names_from_rows(rows, kind="table"))

    # Skip technical auto date tables.
    out = [n for n in _dedupe_keep_order(out) if not n.lower().startswith("localdatetable_")]
    return out


def _extract_column_names(payload: Dict[str, Any]) -> List[str]:
    out: List[str] = []

    for item in (payload.get("value") or []):
        if isinstance(item, dict):
            name = (item.get("name") or item.get("columnName") or "").strip()
            if name:
                out.append(name)

    rows = _extract_execute_queries_rows(payload)
    out.extend(_extract_names_from_rows(rows, kind="column"))
    return _dedupe_keep_order(out)


def _extract_manual_table_names_from_settings() -> List[str]:
    raw = (getattr(settings, "power_bi_ai_context_tables", "") or "").strip()
    if not raw:
        return []
    return _dedupe_keep_order([x.strip() for x in raw.split(",") if x.strip()])


def _build_auto_table_candidates() -> List[str]:
    """
    Build table-name candidates from SQLAlchemy models so deployment doesn't
    require manual POWER_BI_AI_CONTEXT_TABLES maintenance.
    """
    names: List[str] = []
    try:
        for mapper in Base.registry.mappers:
            model = mapper.class_
            table_name = getattr(model, "__tablename__", None)
            if not isinstance(table_name, str) or not table_name.strip():
                continue
            t = table_name.strip()
            names.append(t)

            # Add common variant forms often seen in Power BI model naming.
            names.append(t.replace("_", " "))
            names.append(t.replace(" ", "_"))
            names.append(t.lower())
            names.append(t.upper())
    except Exception:
        return []
    return _dedupe_keep_order(names)


def _escape_dax_table_name(name: str) -> str:
    return (name or "").replace("'", "''")


def _escape_dax_col_name(name: str) -> str:
    return (name or "").replace("]", "]]")


def _build_table_sample_dax(table_name: str, columns: List[str], max_rows: int) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Build DAX to get a small sample from arbitrary table with deterministic aliases.
    Returns (dax, alias->column mapping).
    """
    t = _escape_dax_table_name(table_name)
    cols = [c for c in columns if c.strip()]
    if not cols:
        raise ValueError("No columns provided")

    aliases: List[Tuple[str, str]] = []
    parts: List[str] = []
    for i, col in enumerate(cols, start=1):
        alias = f"c{i}"
        ec = _escape_dax_col_name(col)
        aliases.append((alias, col))
        parts.append(f'"{alias}", \'{t}\'[{ec}]')

    order_alias = aliases[0][0]
    rows = max(1, int(max_rows))
    dax = (
        f"EVALUATE TOPN({rows}, "
        f"SELECTCOLUMNS('{t}', {', '.join(parts)}), "
        f"[{order_alias}], ASC)"
    )
    return dax, aliases


def _format_all_tables_context(
    all_samples: List[Tuple[str, List[dict], List[Tuple[str, str]]]],
    max_chars: int,
) -> str:
    lines: List[str] = ["--- Power BI (all tables) ---"]
    if not all_samples:
        lines.append("(No readable table samples found)")
        return "\n".join(lines)

    for table_name, rows, aliases in all_samples:
        lines.append(f"\nTable: {table_name} (sample_rows={len(rows)})")
        if not rows:
            lines.append("- (no rows)")
            continue

        for row in rows:
            fields: List[str] = []
            for alias, col in aliases:
                value = row.get(alias)
                sval = _format_number(value)
                if sval:
                    fields.append(f"{col}={sval}")
            if fields:
                lines.append("- " + ", ".join(fields))
            else:
                lines.append("- (empty row)")

    out = "\n".join(lines)
    if max_chars and len(out) > max_chars:
        out = out[: max_chars - 3] + "..."
    return out


def _strip_table_prefix(key: str) -> str:
    """
    Convert "Table[Column]" -> "Column" for prompt readability.
    """
    s = (key or "").strip()
    if "[" in s and s.endswith("]"):
        return s.split("[", 1)[1][:-1]
    return s


def _sample_table_rows(
    powerbi_service,
    table_name: str,
    max_rows: int,
    max_columns: int,
) -> Tuple[bool, List[dict], List[Tuple[str, str]], Optional[str]]:
    """
    Try to sample table rows with progressively more compatible strategies.
    Returns:
    - ok
    - rows
    - alias mapping (alias -> display column name)
    - error summary (when ok=False)
    """
    t = _escape_dax_table_name(table_name)

    # Strategy 1: direct table sampling (works for many models).
    dax = f"EVALUATE TOPN({max_rows}, '{t}')"
    resp = powerbi_service.execute_dax_query_global_verbose(dax)
    if resp.get("ok"):
        rows = _extract_execute_queries_rows(resp.get("result") or {})
        rows = _limit_row_columns(rows, max_columns=max_columns)
        aliases = [(k, k) for k in (rows[0].keys() if rows else [])]
        return True, rows, aliases, None

    # Strategy 2: discover columns, then SELECTCOLUMNS with deterministic aliases.
    columns_resp = powerbi_service.get_table_columns_global_verbose(table_name)
    if not columns_resp.get("ok"):
        reason = str(resp.get("error") or resp.get("body") or "table sample failed")
        reason2 = str(columns_resp.get("error") or columns_resp.get("body") or "column discovery failed")
        return False, [], [], f"{reason}; {reason2}"

    columns = _extract_column_names(columns_resp.get("result") or {})
    if not columns:
        reason = str(resp.get("error") or resp.get("body") or "table sample failed")
        return False, [], [], f"{reason}; no readable columns discovered"

    limited_columns = columns[:max_columns]
    try:
        dax2, aliases = _build_table_sample_dax(table_name=table_name, columns=limited_columns, max_rows=max_rows)
    except Exception as e:
        return False, [], [], f"cannot build sample query: {str(e)}"

    resp2 = powerbi_service.execute_dax_query_global_verbose(dax2)
    if not resp2.get("ok"):
        reason = str(resp2.get("error") or resp2.get("body") or "SELECTCOLUMNS sample failed")
        return False, [], [], reason

    rows2 = _extract_execute_queries_rows(resp2.get("result") or {})
    return True, rows2, aliases, None


def _limit_row_columns(rows: List[dict], max_columns: int) -> List[dict]:
    if not rows:
        return rows
    trimmed: List[dict] = []
    for row in rows:
        out: Dict[str, Any] = {}
        for i, (k, v) in enumerate(row.items()):
            if i >= max_columns:
                break
            out[_strip_table_prefix(k)] = v
        trimmed.append(out)
    return trimmed


def _get_all_tables_context_from_powerbi(powerbi_service) -> str:
    max_chars = _safe_int(getattr(settings, "power_bi_ai_context_max_chars", 4000)) or 4000
    max_tables = _safe_int(getattr(settings, "power_bi_ai_context_max_tables", 12)) or 12
    max_columns = _safe_int(getattr(settings, "power_bi_ai_context_max_columns", 8)) or 8
    max_rows = _safe_int(getattr(settings, "power_bi_ai_context_max_rows", 200)) or 200

    max_tables = max(1, max_tables)
    max_columns = max(1, max_columns)
    max_rows = max(1, min(max_rows, 50))  # avoid oversized prompt/query

    tables_resp = powerbi_service.get_dataset_tables_global_verbose()
    table_names: List[str] = []
    if tables_resp.get("ok"):
        table_names = _extract_table_names(tables_resp.get("result") or {})
    else:
        table_names = _extract_manual_table_names_from_settings()
        if not table_names:
            table_names = _build_auto_table_candidates()
            if not table_names:
                table_name = (settings.power_bi_ai_context_table or "AI_Context").strip() or "AI_Context"
                escaped_table = table_name.replace("'", "''")
                fallback_dax = f"EVALUATE TOPN({max_rows}, '{escaped_table}', '{escaped_table}'[Key], ASC)"
                fallback_result = powerbi_service.execute_dax_query_global_verbose(fallback_dax)
                if fallback_result.get("ok"):
                    required_raw = (settings.power_bi_ai_context_required_keys or "").strip()
                    required_keys = [k.strip() for k in required_raw.split(",") if k.strip()]
                    rows = _extract_execute_queries_rows(fallback_result.get("result") or {})
                    if rows:
                        return _format_ai_context_rows(
                            rows=rows,
                            table_name=table_name,
                            required_keys=required_keys,
                            max_chars=max_chars,
                        )
                return (
                    "--- Power BI (all tables) ---\n"
                    "Cannot discover tables and no automatic candidates available.\n"
                    "Checked AI_Context contract fallback automatically.\n"
                    "Optional override only if needed: POWER_BI_AI_CONTEXT_TABLES=TableA,TableB,...\n"
                    + json.dumps(tables_resp, ensure_ascii=False)[:1200]
                )

    if not table_names:
        return "--- Power BI (all tables) ---\n(No tables discovered from dataset)"

    samples: List[Tuple[str, List[dict], List[Tuple[str, str]]]] = []
    failed_tables: List[Tuple[str, str]] = []
    for table_name in table_names:
        if len(samples) >= max_tables:
            break
        ok, rows, aliases, error = _sample_table_rows(
            powerbi_service,
            table_name=table_name,
            max_rows=max_rows,
            max_columns=max_columns,
        )
        if not ok:
            if error:
                failed_tables.append((table_name, error))
            continue
        samples.append((table_name, rows, aliases))

    if not samples:
        # Automatic fallback: try contract table before requiring manual table list.
        table_name = (settings.power_bi_ai_context_table or "AI_Context").strip() or "AI_Context"
        escaped_table = table_name.replace("'", "''")
        fallback_dax = f"EVALUATE TOPN({max_rows}, '{escaped_table}', '{escaped_table}'[Key], ASC)"
        fallback_result = powerbi_service.execute_dax_query_global_verbose(fallback_dax)
        if fallback_result.get("ok"):
            required_raw = (settings.power_bi_ai_context_required_keys or "").strip()
            required_keys = [k.strip() for k in required_raw.split(",") if k.strip()]
            rows = _extract_execute_queries_rows(fallback_result.get("result") or {})
            if rows:
                return _format_ai_context_rows(
                    rows=rows,
                    table_name=table_name,
                    required_keys=required_keys,
                    max_chars=max_chars,
                )

        debug_lines: List[str] = []
        if failed_tables:
            for name, reason in failed_tables[:5]:
                debug_lines.append(f"- {name}: {reason[:180]}")
        return (
            "--- Power BI (all tables) ---\n"
            "Auto-probe did not find readable tables.\n"
            "Checked direct table sampling, column-based fallback, and AI_Context contract fallback automatically.\n"
            + ("\n".join(debug_lines) if debug_lines else "No detailed diagnostics available.")
        )

    return _format_all_tables_context(samples, max_chars=max_chars)


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
            mode = (getattr(settings, "power_bi_ai_context_mode", "all_tables") or "all_tables").strip().lower()
            if mode in {"all_tables", "all"}:
                return _get_all_tables_context_from_powerbi(powerbi_service)

            # contract_table mode: use fixed AI_Context contract table
            table_name = (settings.power_bi_ai_context_table or "AI_Context").strip() or "AI_Context"
            max_rows = int(getattr(settings, "power_bi_ai_context_max_rows", 200) or 200)
            if max_rows <= 0:
                max_rows = 200
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
            "Hint: set POWER_BI_AI_CONTEXT_MODE=all_tables to sample all dataset tables, "
            "or POWER_BI_AI_CONTEXT_MODE=contract_table to use fixed AI_Context."
        )
    except Exception as e:
        logger.warning("get_analysis_context_powerbi failed: %s", e)
        return f"Power BI direct context error: {str(e)}"

