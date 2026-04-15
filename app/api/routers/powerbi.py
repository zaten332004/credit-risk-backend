"""
Power BI Integration API Endpoints
Manage user Power BI workspaces and fetch data
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.core.config import settings
from app.services.powerbi_service import powerbi_service
from app.services.analytics_data_service import (
    _dedupe_keep_order,
    _extract_table_names,
    _extract_column_names,
    _extract_execute_queries_rows,
    _infer_column_names_from_sample_rows,
    _scalar_int_from_first_row,
    _safe_int,
    _strip_table_prefix,
)

router = APIRouter(prefix="/powerbi", tags=["Power BI Integration"])


def _runtime_user(current_user: Any):
    return powerbi_service.get_runtime_user(current_user)


# =========================================================================
# Pydantic Models
# =========================================================================

class PowerBIConfigRequest(BaseModel):
    """Request to configure Power BI workspace"""
    workspace_id: str
    dataset_id: str
    tenant_id: Optional[str] = None
    workspace_name: Optional[str] = None
    dataset_name: Optional[str] = None

    class Config:
        # Chi OpenAPI/Swagger — khong phai default runtime, khong luu san cho user.
        json_schema_extra = {
            "example": {
                "workspace_id": "<workspace-guid>",
                "dataset_id": "<dataset-guid>",
                "tenant_id": "<azure-tenant-guid>",
                "workspace_name": "<ten hien thi trong Power BI>",
                "dataset_name": "<ten dataset trong Power BI>",
            }
        }


class PowerBIWorkspaceResponse(BaseModel):
    """Power BI Workspace information"""
    id: str
    name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class PowerBIDatasetResponse(BaseModel):
    """Power BI Dataset information"""
    id: str
    name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class PowerBIConnectionResponse(BaseModel):
    """Power BI connection status"""
    connected: bool
    tenant_id: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    table_names: Optional[List[str]] = None
    last_sync: Optional[str] = None
    message: str


class PowerBIRiskDataResponse(BaseModel):
    """Risk data from Power BI"""
    high_risk_customers: int
    medium_risk_customers: int
    low_risk_customers: int
    avg_risk_score: float
    total_exposure: float
    default_rate: float
    
    class Config:
        from_attributes = True


class PowerBITableSchema(BaseModel):
    """Schema + sample rows cho một bảng Power BI"""

    name: str
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
    # Tổng số dòng trong model (COUNTROWS); sample_rows có thể ngắn hơn.
    row_count: Optional[int] = None
    column_count: Optional[int] = None


class PowerBITableHintsRequest(BaseModel):
    table_names: List[str] = []


# =========================================================================
# API Endpoints
# =========================================================================

@router.post("/configure", response_model=dict)
async def configure_powerbi(
    config: PowerBIConfigRequest,
    current_user: Any = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Configure Power BI workspace for current user
    
    Each user can have their own Power BI workspace
    """
    try:
        success = powerbi_service.update_user_powerbi_config(
            db=db,
            user=current_user,
            workspace_id=config.workspace_id,
            dataset_id=config.dataset_id,
            tenant_id=config.tenant_id,
            workspace_name=config.workspace_name,
            dataset_name=config.dataset_name,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist Power BI config"
            )
        return {
            "success": True,
            "message": "Power BI workspace configured successfully",
            "workspace_id": config.workspace_id,
            "dataset_id": config.dataset_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error configuring Power BI: {str(e)}"
        )


@router.get("/status", response_model=PowerBIConnectionResponse)
async def get_powerbi_status(
    current_user: Any = Depends(get_current_active_user),
):
    runtime_user = _runtime_user(current_user)
    connected = bool(
        runtime_user.power_bi_enabled
        and runtime_user.power_bi_workspace_id
        and runtime_user.power_bi_dataset_id
    )
    return PowerBIConnectionResponse(
        connected=connected,
        tenant_id=runtime_user.power_bi_tenant_id,
        workspace_id=runtime_user.power_bi_workspace_id,
        workspace_name=getattr(runtime_user, "power_bi_workspace_name", None),
        dataset_id=runtime_user.power_bi_dataset_id,
        dataset_name=getattr(runtime_user, "power_bi_dataset_name", None),
        table_names=getattr(runtime_user, "power_bi_table_names", None) or [],
        last_sync=runtime_user.power_bi_last_sync.isoformat() if runtime_user.power_bi_last_sync else None,
        message="Power BI da duoc cau hinh cho tai khoan nay." if connected else "Power BI chua duoc cau hinh.",
    )


@router.post("/table-hints", response_model=dict)
async def save_powerbi_table_hints(
    request: PowerBITableHintsRequest,
    current_user: Any = Depends(get_current_active_user),
):
    runtime_user = _runtime_user(current_user)
    if not runtime_user.power_bi_workspace_id or not runtime_user.power_bi_dataset_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI workspace/dataset not configured for this user",
        )

    saved = powerbi_service.update_user_powerbi_table_names(current_user, request.table_names)
    return {"success": True, "table_names": saved}


@router.get("/test-connection", response_model=PowerBIConnectionResponse)
async def test_powerbi_connection(
    current_user: Any = Depends(get_current_active_user),
):
    """
    Test Power BI connection using the backend's configured workspace/dataset.

    Lưu ý:
    - Không phụ thuộc các cột PowerBI trên bảng User (power_bi_enabled, ...),
      để tránh lỗi 500 trên các DB chưa migrate.
    - Vẫn yêu cầu người dùng đã đăng nhập (Bearer token) để bảo vệ endpoint.
    """
    ping = powerbi_service.execute_dax_query_global_verbose('EVALUATE ROW("Ping", 1)')

    connected = bool(ping.get("ok"))
    # Các thông tin cấu hình global được ẩn phía server; chỉ trả workspace/dataset id nếu cần debug.
    workspace_id = getattr(powerbi_service, "POWER_BI_API_BASE", None)  # placeholder, giữ field không null-safe

    # Vì execute_dax_query_global_verbose đã đóng gói lỗi, ánh xạ lại message ngắn gọn hơn cho UI.
    if connected:
        message = "✅ Connected (global Power BI config)"
    else:
        stage = ping.get("stage") or "unknown"
        error = (ping.get("error") or ping.get("body") or "Connection test failed").strip()
        message = f"❌ Connection failed (stage={stage}): {error}"

    return PowerBIConnectionResponse(
        connected=connected,
        workspace_id=None,
        workspace_name=None,
        dataset_id=None,
        dataset_name=None,
        last_sync=None,
        message=message,
    )


@router.get("/workspaces", response_model=list)
async def get_powerbi_workspaces(
    current_user: Any = Depends(get_current_active_user)
):
    """
    Get all Power BI workspaces accessible to current user
    """
    workspaces = powerbi_service.get_workspaces(_runtime_user(current_user))
    
    if workspaces is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch workspaces from Power BI"
        )
    
    return [
        PowerBIWorkspaceResponse(
            id=w.get("id"),
            name=w.get("name"),
            description=w.get("description")
        ).model_dump()
        for w in workspaces
    ]


@router.get("/datasets", response_model=list)
async def get_powerbi_datasets(
    current_user: Any = Depends(get_current_active_user)
):
    """
    Get all datasets in user's configured workspace
    """
    runtime_user = _runtime_user(current_user)
    if not runtime_user.power_bi_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI workspace not configured"
        )
    
    datasets = powerbi_service.get_datasets(runtime_user)
    
    if datasets is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch datasets from Power BI"
        )
    
    return [
        PowerBIDatasetResponse(
            id=d.get("id"),
            name=d.get("name"),
            description=d.get("description")
        ).model_dump()
        for d in datasets
    ]


@router.get("/risk-data", response_model=dict)
async def get_powerbi_risk_data(
    current_user: Any = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get risk analysis data from Power BI
    - High/Medium/Low risk customer counts
    - Average risk score
    - Default rate
    - Portfolio exposure
    """
    runtime_user = _runtime_user(current_user)
    if not runtime_user.power_bi_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI not configured for this user"
        )
    
    risk_data = powerbi_service.get_risk_data(runtime_user)
    
    if risk_data is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch risk data from Power BI"
        )
    
    # Update last sync timestamp
    last_sync = powerbi_service.update_runtime_user_last_sync(current_user)
    
    return {
        "success": True,
        "data": risk_data,
        "timestamp": last_sync
    }


@router.get("/portfolio-metrics", response_model=dict)
async def get_powerbi_portfolio_metrics(
    current_user: Any = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get portfolio metrics from Power BI
    - Total loans count
    - Total portfolio amount
    - Average interest rate
    - Default rate percentage
    - Average risk score
    """
    runtime_user = _runtime_user(current_user)
    if not runtime_user.power_bi_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI not configured for this user"
        )
    
    metrics = powerbi_service.get_portfolio_metrics(runtime_user)
    
    if metrics is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch portfolio metrics from Power BI"
        )
    
    # Update last sync timestamp
    last_sync = powerbi_service.update_runtime_user_last_sync(current_user)
    
    return {
        "success": True,
        "metrics": metrics,
        "timestamp": last_sync
    }


@router.get("/customer/{customer_id}/risk-profile", response_model=dict)
async def get_customer_risk_profile(
    customer_id: int,
    current_user: Any = Depends(get_current_active_user)
):
    """
    Get specific customer's risk profile from Power BI
    - Risk score
    - Credit score
    - DTI ratio
    - Employment status
    - Loan history
    - Default history
    """
    runtime_user = _runtime_user(current_user)
    if not runtime_user.power_bi_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI not configured for this user"
        )
    
    profile = powerbi_service.get_customer_risk_profile(runtime_user, customer_id)
    
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch customer risk profile from Power BI"
        )
    
    return {
        "success": True,
        "customer_id": customer_id,
        "profile": profile
    }


@router.post("/refresh-dataset", response_model=dict)
async def refresh_powerbi_dataset(
    current_user: Any = Depends(get_current_active_user)
):
    """
    Trigger Power BI dataset refresh
    """
    runtime_user = _runtime_user(current_user)
    if not runtime_user.power_bi_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI not configured for this user"
        )
    
    success = powerbi_service.refresh_dataset(runtime_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger dataset refresh"
        )

    last_sync = powerbi_service.update_runtime_user_last_sync(current_user)
    return {
        "success": True,
        "message": "Dataset refresh triggered successfully",
        "last_sync": last_sync,
    }


@router.delete("/disconnect", response_model=dict)
async def disconnect_powerbi(
    current_user: Any = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Power BI from user account
    """
    try:
        powerbi_service.clear_user_powerbi_config(current_user)
        
        return {
            "success": True,
            "message": "Power BI disconnected successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error disconnecting Power BI: {str(e)}"
        )


def _escape_dax_table_name(name: str) -> str:
    return (name or "").replace("'", "''")


def _normalize_schema_sample_rows(rows: List[Dict[str, Any]], columns: List[str]) -> List[Dict[str, Any]]:
    """
    Align sample row keys with schema column names for frontend rendering.
    Power BI executeQueries may return keys like `Table[Column]` while schema
    columns are often `Column`.
    """
    if not rows or not columns:
        return rows

    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        exact_map: Dict[str, Any] = {}
        folded_map: Dict[str, Any] = {}
        for raw_key, val in row.items():
            raw = str(raw_key or "").strip()
            if not raw:
                continue
            stripped = _strip_table_prefix(raw).strip()

            # Keep first occurrence for deterministic results.
            if raw not in exact_map:
                exact_map[raw] = val
            if stripped and stripped not in exact_map:
                exact_map[stripped] = val

            raw_l = raw.lower()
            stripped_l = stripped.lower() if stripped else ""
            if raw_l and raw_l not in folded_map:
                folded_map[raw_l] = val
            if stripped_l and stripped_l not in folded_map:
                folded_map[stripped_l] = val

        normalized: Dict[str, Any] = {}
        for col in columns:
            key = str(col or "").strip()
            if not key:
                continue
            if key in exact_map:
                normalized[key] = exact_map[key]
            else:
                normalized[key] = folded_map.get(key.lower())

        out.append(normalized)

    return out


def _manual_powerbi_table_names() -> List[str]:
    raw = (getattr(settings, "power_bi_ai_context_tables", "") or "").strip()
    names = [item.strip() for item in raw.split(",") if item.strip()]
    default_table = (getattr(settings, "power_bi_ai_context_table", "") or "").strip()
    if default_table:
        names.append(default_table)
    return _dedupe_keep_order(names)


def _runtime_or_manual_powerbi_table_names(runtime_user: Any) -> List[str]:
    runtime_names = [
        str(item).strip()
        for item in (getattr(runtime_user, "power_bi_table_names", None) or [])
        if str(item).strip()
    ]
    if runtime_names:
        return _dedupe_keep_order(runtime_names)
    return _manual_powerbi_table_names()


@router.get("/schema", response_model=dict)
async def get_powerbi_schema(
    current_user: Any = Depends(get_current_active_user),
):
    """
    Trả về schema của toàn bộ dataset Power BI (bảng, cột, sample rows).

    - Dùng cấu hình global từ backend (.env): TENANT / WORKSPACE / DATASET.
    - Không phụ thuộc các trường PowerBI trên bảng User.
    """
    runtime_user = _runtime_user(current_user)
    if not runtime_user.power_bi_workspace_id or not runtime_user.power_bi_dataset_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI workspace/dataset not configured for this user",
        )

    tables_resp = powerbi_service.get_dataset_tables_verbose(runtime_user)
    table_names: List[str] = []
    discovered_via_api = bool(tables_resp.get("ok"))
    if discovered_via_api:
        table_names = _extract_table_names(tables_resp.get("result") or {})
        if not table_names:
            ds = (getattr(runtime_user, "power_bi_dataset_id", None) or "").strip()
            fb = powerbi_service.dataset_tables_dax_fallback(runtime_user, ds)
            if fb.get("ok"):
                tables_resp = fb
                table_names = _extract_table_names(fb.get("result") or {})
    else:
        table_names = _runtime_or_manual_powerbi_table_names(runtime_user)
        if not table_names:
            return {
                "ok": False,
                "tables": [],
                "schemas": [],
                "errors": {},
                "requires_table_hints": True,
                "message": "Schema auto-discovery is blocked for this dataset. Save table hints to continue.",
                "discovery_stage": tables_resp.get("stage"),
                "discovery_error": (tables_resp.get("error") or tables_resp.get("body") or "unknown error"),
            }
    if not table_names:
        return {
            "ok": False,
            "tables": [],
            "message": "No tables discovered in dataset",
        }

    schemas: List[PowerBITableSchema] = []
    errors: Dict[str, str] = {}
    max_tables = 20
    sample_cap = _safe_int(getattr(settings, "power_bi_schema_sample_max_rows", 500)) or 500
    sample_cap = max(1, min(sample_cap, 100000))

    for name in table_names[:max_tables]:
        cols_resp = powerbi_service.get_table_columns_verbose(runtime_user, name)
        columns: List[str] = []
        if cols_resp.get("ok"):
            columns = _extract_column_names(cols_resp.get("result") or {})

        escaped = _escape_dax_table_name(name)

        # Total row count (lightweight; avoids returning every row in JSON).
        row_count: Optional[int] = None
        dax_count = f'EVALUATE ROW("RowCount", COUNTROWS(\'{escaped}\'))'
        count_resp = powerbi_service.execute_dax_query_verbose(runtime_user, dax_count)
        if count_resp.get("ok"):
            count_rows = _extract_execute_queries_rows(count_resp.get("result") or {})
            row_count = _scalar_int_from_first_row(count_rows)
        else:
            err_c = (count_resp.get("error") or count_resp.get("body") or "").strip()
            if err_c and name not in errors:
                errors[name] = err_c[:1200]

        # Sample rows (best-effort; bounded by sample_cap and ExecuteQueries maxRows).
        dax_sample = f"EVALUATE TOPN({sample_cap}, '{escaped}')"
        sample_resp = powerbi_service.execute_dax_query_verbose(runtime_user, dax_sample)
        rows: List[Dict[str, Any]] = []
        if sample_resp.get("ok"):
            rows = _extract_execute_queries_rows(sample_resp.get("result") or {})
        else:
            err = (sample_resp.get("error") or sample_resp.get("body") or "").strip()
            if err:
                errors[name] = err[:1200]

        if not columns and rows:
            columns = _infer_column_names_from_sample_rows(rows)
        rows = _normalize_schema_sample_rows(rows, columns)

        col_count = len(columns) if columns else None

        schemas.append(
            PowerBITableSchema(
                name=name,
                columns=columns,
                sample_rows=rows,
                row_count=row_count,
                column_count=col_count,
            )
        )

    return {
        "ok": True,
        "tables": table_names,
        "schemas": [s.model_dump() for s in schemas],
        "errors": errors,
        "table_list_source": "api" if discovered_via_api else "saved_hints",
        "schema_sample_limit": max_tables,
        "schema_row_sample_max": sample_cap,
    }
