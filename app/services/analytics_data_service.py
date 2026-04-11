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
    LoanApplicationDB,
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
        lines.append(f"[WARN] Missing required keys on {table_name}: {', '.join(missing)}")

    if not kv:
        lines.append(f"({table_name} contract query returned 0 rows)")
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
            k = (key or "").lower()
            if not any(w in k for w in keywords):
                continue
            if value is None:
                continue
            s = value.strip() if isinstance(value, str) else str(value).strip()
            if s:
                out.append(s)
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


def _extract_manual_table_names(runtime_user: Optional[Any] = None) -> List[str]:
    runtime_names = [
        str(item).strip()
        for item in (getattr(runtime_user, "power_bi_table_names", None) or [])
        if str(item).strip()
    ]

    configured: List[str] = []
    raw = (getattr(settings, "power_bi_ai_context_tables", "") or "").strip()
    if raw:
        configured.extend([x.strip() for x in raw.split(",") if x.strip()])

    default_table = (getattr(settings, "power_bi_ai_context_table", "") or "").strip()
    if default_table:
        configured.append(default_table)

    return _dedupe_keep_order(runtime_names + configured)


def _manual_table_names_for_probe(runtime_user: Optional[Any] = None) -> List[str]:
    """
    When sampling a user's workspace/dataset, only use UI hints (power_bi_table_names).
    Do not merge global POWER_BI_AI_CONTEXT_TABLES / POWER_BI_AI_CONTEXT_TABLE — those
    may refer to another semantic model and cause wrong probes or AI_Context-style fallbacks.
    """
    if runtime_user is not None:
        return _dedupe_keep_order(
            [
                str(item).strip()
                for item in (getattr(runtime_user, "power_bi_table_names", None) or [])
                if str(item).strip()
            ]
        )
    return _extract_manual_table_names(None)


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
    deduped_samples: List[Tuple[str, List[dict], List[Tuple[str, str]]]] = []
    seen_tables: set[str] = set()
    for table_name, rows, aliases in all_samples:
        normalized = (table_name or "").strip().lower()
        if not normalized or normalized in seen_tables:
            continue
        seen_tables.add(normalized)
        deduped_samples.append((table_name, rows, aliases))

    lines: List[str] = ["--- Power BI (all tables) ---"]
    if deduped_samples:
        lines.append("Tables available: " + ", ".join(table_name for table_name, _, _ in deduped_samples))
    if not deduped_samples:
        lines.append("(No readable table samples found)")
        return "\n".join(lines)

    for table_name, rows, aliases in deduped_samples:
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
    runtime_user: Optional[Any],
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
    if runtime_user is not None:
        resp = powerbi_service.execute_dax_query_verbose(runtime_user, dax)
    else:
        resp = powerbi_service.execute_dax_query_global_verbose(dax)
    if resp.get("ok"):
        rows = _extract_execute_queries_rows(resp.get("result") or {})
        rows = _limit_row_columns(rows, max_columns=max_columns)
        aliases = [(k, k) for k in (rows[0].keys() if rows else [])]
        return True, rows, aliases, None

    # Strategy 2: discover columns, then SELECTCOLUMNS with deterministic aliases.
    if runtime_user is not None:
        columns_resp = powerbi_service.get_table_columns_verbose(runtime_user, table_name)
    else:
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

    if runtime_user is not None:
        resp2 = powerbi_service.execute_dax_query_verbose(runtime_user, dax2)
    else:
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


def _powerbi_schema_attempt_hints(tables_resp: Dict[str, Any]) -> str:
    """Lấy message/body từ từng bước DAX/REST để AI và admin thấy lỗi thật từ Power BI."""
    lines: List[str] = []
    for att in (tables_resp.get("attempts") or [])[:8]:
        if not isinstance(att, dict):
            continue
        stage = att.get("stage") or "?"
        body = att.get("body") or att.get("error")
        if body and str(body).strip():
            lines.append(f"- {stage}: {str(body).strip()[:500]}")
    return "\n".join(lines) if lines else ""


def _get_all_tables_context_from_powerbi(powerbi_service, runtime_user: Optional[Any] = None) -> str:
    max_chars = _safe_int(getattr(settings, "power_bi_ai_context_max_chars", 4000)) or 4000
    max_tables = _safe_int(getattr(settings, "power_bi_ai_context_max_tables", 12)) or 12
    max_columns = _safe_int(getattr(settings, "power_bi_ai_context_max_columns", 8)) or 8
    max_rows = _safe_int(getattr(settings, "power_bi_ai_context_max_rows", 200)) or 200

    max_tables = max(1, max_tables)
    max_columns = max(1, max_columns)
    max_rows = max(1, min(max_rows, 50))  # avoid oversized prompt/query

    if runtime_user is not None:
        tables_resp = powerbi_service.get_dataset_tables_verbose(runtime_user)
    else:
        tables_resp = powerbi_service.get_dataset_tables_global_verbose()
    table_names: List[str] = []
    if tables_resp.get("ok"):
        table_names = _extract_table_names(tables_resp.get("result") or {})
        if not table_names:
            tables_resp = {
                **tables_resp,
                "ok": False,
                "error": "Không parse được tên bảng từ phản hồi Power BI.",
            }

    if not tables_resp.get("ok"):
        if runtime_user is not None:
            table_names = _manual_table_names_for_probe(runtime_user)
            if not table_names:
                hints = _powerbi_schema_attempt_hints(tables_resp)
                detail = (tables_resp.get("body") or tables_resp.get("error") or "").strip()
                msg = (
                    "--- Power BI (all tables) ---\n"
                    "Không đọc được danh sách bảng từ dataset (workspace/dataset của người dùng). "
                    "Kiểm tra: Service Principal là thành viên workspace, quyền Build trên dataset, "
                    "và app registration có quyền Dataset.Read.All (hoặc tương đương).\n"
                )
                if detail:
                    msg += f"Tóm tắt lỗi: {detail[:600]}\n"
                if hints:
                    msg += "Chi tiết từng bước schema:\n" + hints + "\n"
                return msg + json.dumps(tables_resp, ensure_ascii=False)[:1200]
        else:
            table_names = _extract_manual_table_names(None)
            if not table_names:
                table_names = _build_auto_table_candidates()
            if not table_names:
                table_name = (settings.power_bi_ai_context_table or "LoanPortfolio").strip() or "LoanPortfolio"
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
                    f"Checked contract-table fallback ({table_name}) automatically.\n"
                    "Optional override: POWER_BI_AI_CONTEXT_TABLES=CustomerMaster,LoanPortfolio,...\n"
                    + json.dumps(tables_resp, ensure_ascii=False)[:1200]
                )

    if not table_names:
        return "--- Power BI (all tables) ---\n(No tables discovered from dataset)"
    table_names = _dedupe_keep_order(table_names)

    samples: List[Tuple[str, List[dict], List[Tuple[str, str]]]] = []
    failed_tables: List[Tuple[str, str]] = []
    for table_name in table_names:
        if len(samples) >= max_tables:
            break
        ok, rows, aliases, error = _sample_table_rows(
            powerbi_service,
            runtime_user,
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
        if runtime_user is not None:
            debug_lines: List[str] = []
            if failed_tables:
                for name, reason in failed_tables[:10]:
                    debug_lines.append(f"- {name}: {reason[:180]}")
            preview = ", ".join(table_names[:40])
            if len(table_names) > 40:
                preview += f" … (+{len(table_names) - 40} bảng)"
            return (
                "--- Power BI (all tables) ---\n"
                f"Dataset có {len(table_names)} bảng nhưng không lấy được mẫu dòng (DAX/cột). "
                "Không dùng bảng contract (Key/TextValue) từ .env vì có thể không thuộc dataset này.\n"
                f"Tên bảng: {preview}\n"
                + ("Lỗi theo bảng:\n" + "\n".join(debug_lines) if debug_lines else "")
            )

        table_name = (settings.power_bi_ai_context_table or "LoanPortfolio").strip() or "LoanPortfolio"
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

        debug_lines_global: List[str] = []
        if failed_tables:
            for name, reason in failed_tables[:5]:
                debug_lines_global.append(f"- {name}: {reason[:180]}")
        return (
            "--- Power BI (all tables) ---\n"
            "Auto-probe did not find readable tables.\n"
            f"Checked direct sampling, column fallback, and contract table ({table_name}) fallback.\n"
            + ("\n".join(debug_lines_global) if debug_lines_global else "No detailed diagnostics available.")
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


def get_customer_focus_context(session: Session, customer_id: int) -> str:
    """
    Snapshot một khách hàng (hồ sơ + khoản vay/ứng dụng + dự báo rủi ro gần nhất) cho AI chat.
    """
    cid = _safe_int(customer_id)
    if cid is None or cid <= 0:
        return "Không có mã khách hàng hợp lệ."

    cust = session.query(CustomerDB).filter(CustomerDB.customer_id == cid).first()
    if not cust:
        return f"Không tìm thấy khách hàng với ID {cid}."

    lines: List[str] = []
    lines.append(f"--- HỒ SƠ KHÁCH HÀNG (customer_id={cid}) ---")
    lines.append(f"Họ tên: {cust.full_name or '—'}")
    if cust.external_customer_ref:
        lines.append(f"Mã tham chiếu: {cust.external_customer_ref}")
    if cust.age is not None:
        lines.append(f"Tuổi: {cust.age}")
    if cust.monthly_income is not None:
        lines.append(f"Thu nhập/tháng (VND): {_format_number(_decimal_to_float(cust.monthly_income))}")
    if cust.credit_score is not None:
        lines.append(f"Điểm tín dụng (nội bộ): {cust.credit_score}")
    if cust.employment_status:
        lines.append(f"Việc làm: {cust.employment_status}")
    if cust.email:
        lines.append(f"Email: {cust.email}")
    if cust.phone_number:
        lines.append(f"SĐT: {cust.phone_number}")

    facs = (
        session.query(LoanFacilityDB)
        .filter(LoanFacilityDB.customer_id == cid)
        .order_by(LoanFacilityDB.created_at.desc())
        .limit(25)
        .all()
    )
    lines.append("\n--- Facility / khoản vay ---")
    if facs:
        for i, f in enumerate(facs, 1):
            lines.append(
                f"  {i}. facility_id={f.facility_id}, loại={f.facility_type or '—'}, "
                f"duyệt={_format_number(_decimal_to_float(f.approved_amount))} VND, "
                f"trạng thái={f.status}, lãi suất={f.interest_rate if f.interest_rate is not None else '—'}"
            )
    else:
        lines.append("  (Chưa có facility)")

    apps = (
        session.query(LoanApplicationDB)
        .filter(LoanApplicationDB.customer_id == cid)
        .order_by(LoanApplicationDB.created_at.desc())
        .limit(15)
        .all()
    )
    lines.append("\n--- Đơn xin vay (ứng dụng) ---")
    if apps:
        for i, a in enumerate(apps, 1):
            lines.append(
                f"  {i}. application_id={a.application_id}, số tiền={_format_number(_decimal_to_float(a.loan_amount))} VND, "
                f"kỳ={a.loan_term} tháng, trạng thái={a.loan_status}, loại vay={a.loan_type or '—'}"
            )
    else:
        lines.append("  (Chưa có đơn)")

    preds = (
        session.query(RiskPredictionDB)
        .filter(RiskPredictionDB.customer_id == cid)
        .order_by(RiskPredictionDB.predicted_at.desc())
        .limit(5)
        .all()
    )
    lines.append("\n--- Dự báo rủi ro (gần nhất) ---")
    if preds:
        for i, p in enumerate(preds, 1):
            lines.append(
                f"  {i}. risk_score={float(p.risk_score):.6f}, mức={p.risk_level or '—'}, "
                f"thời điểm={p.predicted_at.isoformat() if p.predicted_at else '—'}"
            )
    else:
        lines.append("  (Chưa có bản ghi dự báo)")

    return "\n".join(lines)


def get_customers_focus_context(session: Session, customer_ids: List[int], *, max_customers: int = 40) -> str:
    """
    Nhiều khách hàng cho AI chat: ghép snapshot từng khách (giới hạn độ dài prompt).
    """
    seen: set[int] = set()
    ids: List[int] = []
    for raw in customer_ids or []:
        cid = _safe_int(raw)
        if cid is None or cid <= 0 or cid in seen:
            continue
        seen.add(cid)
        ids.append(cid)

    if not ids:
        return "Không có mã khách hàng hợp lệ."

    original_count = len(ids)
    if len(ids) > max_customers:
        ids = ids[:max_customers]

    blocks: List[str] = []
    for cid in ids:
        blocks.append(get_customer_focus_context(session, cid))

    footer: List[str] = []
    if original_count > max_customers:
        footer.append(
            f"(Giới hạn AI: chỉ nạp {max_customers}/{original_count} khách hàng đầu tiên trong danh sách đã chọn.)"
        )
    elif len(ids) > 1:
        footer.append(f"(Tổng {len(ids)} khách hàng được đưa vào ngữ cảnh.)")

    out = "\n\n".join(blocks)
    if footer:
        out = out + "\n\n" + "\n".join(footer)
    return out


def get_analysis_context_powerbi(runtime_user: Optional[Any] = None) -> str:
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

        # Tenant may come from .env when user file has empty tenant_id; token resolution handles that.
        has_runtime_user = bool(
            runtime_user
            and (getattr(runtime_user, "power_bi_workspace_id", None) or "").strip()
            and (getattr(runtime_user, "power_bi_dataset_id", None) or "").strip()
        )
        has_global_config = bool(
            (settings.power_bi_tenant_id or "").strip()
            and (settings.power_bi_client_id or "").strip()
            and (settings.power_bi_client_secret or "").strip()
            and (settings.power_bi_workspace_id or "").strip()
            and (settings.power_bi_dataset_id or "").strip()
        )
        if not has_runtime_user and not has_global_config:
            return (
                "Power BI chưa được cấu hình cho backend. "
                "Hãy set POWER_BI_TENANT_ID/CLIENT_ID/CLIENT_SECRET/WORKSPACE_ID/DATASET_ID trong .env."
            )

        mode = (getattr(settings, "power_bi_ai_context_mode", "all_tables") or "all_tables").strip().lower()
        # all_tables: always sample the configured dataset; ignore POWER_BI_AI_CONTEXT_DAX so a stale
        # AI_Context DAX in .env cannot bypass real table sampling.
        if mode in {"all_tables", "all"}:
            return _get_all_tables_context_from_powerbi(powerbi_service, runtime_user=runtime_user)

        dax = (settings.power_bi_ai_context_dax or "").strip()
        if not dax:
            # contract_table mode: fixed hub table (default LoanPortfolio, override via POWER_BI_AI_CONTEXT_TABLE)
            table_name = (settings.power_bi_ai_context_table or "LoanPortfolio").strip() or "LoanPortfolio"
            max_rows = int(getattr(settings, "power_bi_ai_context_max_rows", 200) or 200)
            if max_rows <= 0:
                max_rows = 200
            escaped_table = table_name.replace("'", "''")
            dax = f"EVALUATE TOPN({max_rows}, '{escaped_table}', '{escaped_table}'[Key], ASC)"

        if runtime_user is not None:
            result = powerbi_service.execute_dax_query_verbose(runtime_user, dax)
        else:
            result = powerbi_service.execute_dax_query_global_verbose(dax)
        if result.get("ok"):
            table_name = (settings.power_bi_ai_context_table or "LoanPortfolio").strip() or "LoanPortfolio"
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
            "or POWER_BI_AI_CONTEXT_MODE=contract_table to use POWER_BI_AI_CONTEXT_TABLE (e.g. LoanPortfolio)."
        )
    except Exception as e:
        logger.warning("get_analysis_context_powerbi failed: %s", e)
        return f"Power BI direct context error: {str(e)}"

