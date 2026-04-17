"""
Power BI Integration Service
Handles multi-workspace Power BI connections and data retrieval
"""
import os
import json
import logging
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from functools import lru_cache

import requests
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)
GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)


class PowerBIConfigValidationError(Exception):
    """Known validation failures for account-scoped Power BI config."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class PowerBIService:
    """Service to interact with Power BI REST API for multi-workspace support"""
    
    # Power BI API endpoints
    POWER_BI_API_BASE = "https://api.powerbi.com/v1.0/myorg"
    POWER_BI_AUTH_URL_V2 = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    POWER_BI_AUTH_URL_V1 = "https://login.microsoftonline.com/{tenant_id}/oauth2/token"
    
    # Cache TTL (5 minutes)
    CACHE_TTL = 300
    
    def __init__(self):
        """Initialize Power BI Service"""
        self.base_url = self.POWER_BI_API_BASE
        self.token_cache: Dict[str, tuple] = {}  # {user_id: (token, expiry)}
        self._config_dir = Path(__file__).resolve().parents[2] / ".powerbi_user_configs"

    def _get_user_id(self, user: Any) -> str:
        value = getattr(user, "user_id", None) or getattr(user, "id", None)
        if value is None:
            raise ValueError("Missing user id for Power BI config")
        return str(value)

    def _safe_user_id(self, user: Any) -> str:
        try:
            return self._get_user_id(user)
        except Exception:
            return "unknown"

    def _config_path(self, user: Any) -> Path:
        return self._config_dir / f"{self._get_user_id(user)}.json"

    def _load_user_config(self, user: Any) -> Dict[str, Any]:
        path = self._config_path(user)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def get_runtime_user(self, user: Any) -> Any:
        config = self._load_user_config(user)
        last_sync = None
        raw_last_sync = config.get("power_bi_last_sync")
        if isinstance(raw_last_sync, str) and raw_last_sync.strip():
            try:
                last_sync = datetime.fromisoformat(raw_last_sync)
            except Exception:
                last_sync = None

        return SimpleNamespace(
            user_id=getattr(user, "user_id", None) or getattr(user, "id", None),
            id=getattr(user, "id", None) or getattr(user, "user_id", None),
            email=getattr(user, "email", None),
            full_name=getattr(user, "full_name", None),
            role=getattr(user, "role", None),
            is_admin=getattr(user, "is_admin", False),
            is_active=getattr(user, "is_active", True),
            power_bi_enabled=bool(config.get("power_bi_enabled")),
            power_bi_workspace_id=str(config.get("power_bi_workspace_id") or "").strip() or None,
            power_bi_dataset_id=str(config.get("power_bi_dataset_id") or "").strip() or None,
            power_bi_tenant_id=str(config.get("power_bi_tenant_id") or "").strip() or None,
            power_bi_last_sync=last_sync,
            power_bi_table_names=[
                str(item).strip()
                for item in (config.get("power_bi_table_names") or [])
                if str(item).strip()
            ],
            power_bi_workspace_name=str(config.get("power_bi_workspace_name") or "").strip() or None,
            power_bi_dataset_name=str(config.get("power_bi_dataset_name") or "").strip() or None,
        )

    def clear_user_powerbi_config(self, user: Any) -> None:
        path = self._config_path(user)
        if path.exists():
            path.unlink()

    def update_runtime_user_last_sync(self, user: Any) -> str:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        path = self._config_path(user)
        payload = self._load_user_config(user)
        now = datetime.utcnow().isoformat()
        if payload:
            payload["power_bi_last_sync"] = now
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return now

    def update_user_powerbi_table_names(self, user: Any, table_names: List[str]) -> List[str]:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        normalized: List[str] = []
        seen: set[str] = set()
        for item in table_names:
            value = str(item or "").strip()
            if not value:
                continue
            lowered = value.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(value)

        payload = self._load_user_config(user)
        payload["power_bi_table_names"] = normalized
        path = self._config_path(user)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return normalized
    
    # =========================================================================
    # Authentication & Token Management
    # =========================================================================
    
    def get_access_token(
        self,
        user: Any,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> Optional[str]:
        """
        Get access token for Power BI API using Service Principal
        
        Args:
            user: User database object
            tenant_id: Azure AD Tenant ID
            client_id: Service Principal Client ID
            client_secret: Service Principal Client Secret
        
        Returns:
            Access token string or None if authentication fails
        """
        user_id = self._safe_user_id(user)
        try:
            # Use provided credentials, then user fields (if present), then settings/env vars
            tenant = (
                tenant_id
                or getattr(user, "power_bi_tenant_id", None)
                or settings.power_bi_tenant_id
                or os.getenv("POWER_BI_TENANT_ID")
            )
            client = client_id or os.getenv("POWER_BI_CLIENT_ID") or settings.power_bi_client_id
            secret = client_secret or os.getenv("POWER_BI_CLIENT_SECRET") or settings.power_bi_client_secret
            
            if not all([tenant, client, secret]):
                logger.warning("Missing Power BI credentials for user %s", user_id)
                return None
            
            # Check cache first
            cache_key = f"{user_id}_{tenant}"
            if cache_key in self.token_cache:
                token, expiry = self.token_cache[cache_key]
                if datetime.utcnow() < expiry:
                    logger.debug("Using cached token for user %s", user_id)
                    return token
            
            token, expires_in = self._request_token(tenant=tenant, client_id=client, client_secret=secret)
            if not token:
                return None
            
            # Cache token
            expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
            self.token_cache[cache_key] = (token, expiry)
            
            logger.info("✅ New access token obtained for user %s", user_id)
            return token
            
        except Exception as e:
            logger.error(f"❌ Failed to get Power BI access token: {str(e)}")
            return None
    
    def _request_token(self, tenant: str, client_id: str, client_secret: str) -> tuple[Optional[str], int]:
        """
        Request Azure AD token for Power BI.
        Prefer OAuth v2.0 with `scope`, fallback to v1 with `resource` for legacy flows.
        """
        # v2.0 (recommended)
        try:
            auth_url = self.POWER_BI_AUTH_URL_V2.format(tenant_id=tenant)
            payload = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://analysis.windows.net/powerbi/api/.default",
            }
            response = requests.post(auth_url, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("access_token"), int(data.get("expires_in", 3600))
        except Exception as e:
            logger.warning("Power BI token v2 failed: %s", str(e))

        # v1 fallback
        try:
            auth_url = self.POWER_BI_AUTH_URL_V1.format(tenant_id=tenant)
            payload = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "resource": "https://analysis.windows.net/powerbi/api",
            }
            response = requests.post(auth_url, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("access_token"), int(data.get("expires_in", 3600))
        except Exception as e:
            logger.error("Power BI token v1 failed: %s", str(e))
            return None, 3600

    def execute_dax_query_global(self, dax_query: str) -> Optional[Dict[str, Any]]:
        """
        Execute DAX query using backend-level Power BI config from env/settings:
        POWER_BI_TENANT_ID, POWER_BI_CLIENT_ID, POWER_BI_CLIENT_SECRET, POWER_BI_WORKSPACE_ID, POWER_BI_DATASET_ID.
        """
        tenant = settings.power_bi_tenant_id or os.getenv("POWER_BI_TENANT_ID") or ""
        workspace_id = settings.power_bi_workspace_id or os.getenv("POWER_BI_WORKSPACE_ID") or ""
        dataset_id = settings.power_bi_dataset_id or os.getenv("POWER_BI_DATASET_ID") or ""
        if not (tenant and workspace_id and dataset_id):
            logger.warning("Power BI global config missing (tenant/workspace/dataset)")
            return None

        user = SimpleNamespace(
            user_id="global",
            power_bi_tenant_id=tenant,
            power_bi_workspace_id=workspace_id,
            power_bi_dataset_id=dataset_id,
        )
        return self.execute_dax_query(user, dax_query=dax_query, dataset_id=dataset_id)

    def execute_dax_query_global_verbose(self, dax_query: str) -> Dict[str, Any]:
        """
        Like `execute_dax_query_global`, but returns structured diagnostics instead of swallowing errors.
        Does not include secrets.
        """
        tenant = (settings.power_bi_tenant_id or os.getenv("POWER_BI_TENANT_ID") or "").strip()
        workspace_id = (settings.power_bi_workspace_id or os.getenv("POWER_BI_WORKSPACE_ID") or "").strip()
        dataset_id = (settings.power_bi_dataset_id or os.getenv("POWER_BI_DATASET_ID") or "").strip()
        if not (tenant and workspace_id and dataset_id):
            return {"ok": False, "stage": "config", "error": "Missing POWER_BI_TENANT_ID/WORKSPACE_ID/DATASET_ID"}

        user = SimpleNamespace(
            user_id="global",
            power_bi_tenant_id=tenant,
            power_bi_workspace_id=workspace_id,
            power_bi_dataset_id=dataset_id,
        )

        token = self.get_access_token(user)
        if not token:
            return {
                "ok": False,
                "stage": "auth",
                "error": "Failed to obtain access token (check tenant/app credentials & Power BI tenant settings)",
            }

        headers = self._get_headers(token)
        url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
        payload = {
            "queries": [{"query": dax_query, "maxRows": 100000}],
            "serializerSettings": {"includeNulls": True},
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
        except Exception as e:
            return {"ok": False, "stage": "request", "error": str(e)}

        if response.status_code >= 400:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            return {"ok": False, "stage": "executeQueries", "status_code": response.status_code, "body": body}

        try:
            data = response.json()
        except Exception:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            return {"ok": True, "stage": "ok", "result": body}
        err_msg = PowerBIService._execute_queries_error_message(data)
        if err_msg:
            return {
                "ok": False,
                "stage": "executeQueries",
                "status_code": response.status_code,
                "body": err_msg,
                "result": data,
            }
        return {"ok": True, "stage": "ok", "result": data}

    def execute_dax_query_verbose(
        self,
        user: Any,
        dax_query: str,
        dataset_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        dataset = (dataset_id or getattr(user, "power_bi_dataset_id", None) or "").strip()
        workspace_id = (getattr(user, "power_bi_workspace_id", None) or "").strip()
        if not workspace_id or not dataset:
            return {"ok": False, "stage": "config", "error": "Missing user Power BI workspace_id/dataset_id"}

        token = self.get_access_token(user)
        if not token:
            return {"ok": False, "stage": "auth", "error": "Failed to obtain access token"}

        headers = self._get_headers(token)
        url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset}/executeQueries"
        payload = {
            "queries": [{"query": dax_query, "maxRows": 100000}],
            "serializerSettings": {"includeNulls": True},
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
        except Exception as e:
            return {"ok": False, "stage": "request", "error": str(e)}

        if response.status_code >= 400:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            return {"ok": False, "stage": "executeQueries", "status_code": response.status_code, "body": body}

        try:
            data = response.json()
        except Exception:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            return {"ok": True, "stage": "ok", "result": body}
        err_msg = PowerBIService._execute_queries_error_message(data)
        if err_msg:
            return {
                "ok": False,
                "stage": "executeQueries",
                "status_code": response.status_code,
                "body": err_msg,
                "result": data,
            }
        return {"ok": True, "stage": "ok", "result": data}

    def _merge_odata_tables_pages(self, headers: dict, first_data: dict) -> dict:
        """
        Power BI REST OData có thể phân trang `value` qua `@odata.nextLink` (GET /datasets/.../tables).
        """
        all_values: List[Any] = []
        chunk = first_data.get("value")
        if isinstance(chunk, list):
            all_values.extend(chunk)
        merged: Dict[str, Any] = {
            k: v
            for k, v in first_data.items()
            if k not in ("value", "@odata.nextLink") and not (isinstance(k, str) and "nextlink" in k.lower())
        }
        next_url = first_data.get("@odata.nextLink")
        if not next_url:
            for k in first_data:
                if isinstance(k, str) and "nextlink" in k.lower():
                    next_url = first_data.get(k)
                    break
        pages = 1
        while isinstance(next_url, str) and next_url.strip() and pages < 100:
            rsp = requests.get(next_url.strip(), headers=headers, timeout=45)
            if rsp.status_code >= 400:
                break
            try:
                data = rsp.json()
            except Exception:
                break
            if not isinstance(data, dict):
                break
            more = data.get("value")
            if isinstance(more, list):
                all_values.extend(more)
            next_url = data.get("@odata.nextLink")
            if not next_url:
                for k in data:
                    if isinstance(k, str) and "nextlink" in k.lower():
                        next_url = data.get(k)
                        break
            pages += 1
        merged["value"] = all_values
        return merged

    @staticmethod
    def _execute_queries_error_message(data: Any) -> Optional[str]:
        """
        executeQueries often returns HTTP 200 with logical failure in results[0].error.
        """
        if not isinstance(data, dict):
            return None
        results = data.get("results")
        if not isinstance(results, list) or not results:
            return None
        r0 = results[0]
        if not isinstance(r0, dict):
            return None
        err = r0.get("error")
        if not isinstance(err, dict):
            return None
        code = (err.get("code") or "").strip()
        msg = (err.get("message") or "").strip()
        parts = [p for p in (code, msg) if p]
        if parts:
            return ": ".join(parts)
        try:
            return json.dumps(err, ensure_ascii=False)[:1200]
        except Exception:
            return str(err)[:1200]

    @staticmethod
    def _should_try_dax_for_dataset_tables_error(status_code: int, body: str) -> bool:
        """REST GET .../tables thường lỗi với semantic/import model; thử DAX thay vì chỉ khớp 404 + chuỗi cố định."""
        if status_code in (401, 403):
            return False
        if status_code in (400, 404, 405):
            return True
        bl = (body or "").lower()
        if "not push api" in bl or "not a push" in bl:
            return True
        return False

    def _dataset_tables_dax_fallback_user(self, user: Any, dataset_id: str) -> Dict[str, Any]:
        from app.services.analytics_data_service import _extract_table_names

        attempts: list[Dict[str, Any]] = []
        queries: list[tuple[str, str]] = [
            ("EVALUATE INFO.TABLES()", "info.tables"),
            (
                'EVALUATE SELECTCOLUMNS(INFO.TABLES(), "TableName", [Name])',
                "info.tables.selectcolumns",
            ),
            (
                'EVALUATE DISTINCT(SELECTCOLUMNS(INFO.COLUMNS(), "TableName", [Table]))',
                "info.columns.distinct_tables",
            ),
            ("EVALUATE $SYSTEM.TMSCHEMA_TABLES", "dmv.tmschema_tables"),
        ]
        for dax_query, stage in queries:
            info = self.execute_dax_query_verbose(user, dax_query, dataset_id=dataset_id)
            info["stage"] = stage
            attempts.append(info)
            if not info.get("ok"):
                continue
            res = info.get("result")
            if isinstance(res, dict) and _extract_table_names(res):
                info["attempts"] = attempts
                return info

        return {"ok": False, "stage": "schema", "error": "Schema discovery failed", "attempts": attempts}

    def _dataset_tables_dax_fallback_global(self, user: Any) -> Dict[str, Any]:
        from app.services.analytics_data_service import _extract_table_names

        attempts: list[Dict[str, Any]] = []
        queries: list[tuple[str, str]] = [
            ("EVALUATE INFO.TABLES()", "info.tables"),
            (
                'EVALUATE SELECTCOLUMNS(INFO.TABLES(), "TableName", [Name])',
                "info.tables.selectcolumns",
            ),
            (
                'EVALUATE DISTINCT(SELECTCOLUMNS(INFO.COLUMNS(), "TableName", [Table]))',
                "info.columns.distinct_tables",
            ),
            ("EVALUATE $SYSTEM.TMSCHEMA_TABLES", "dmv.tmschema_tables"),
        ]
        for dax_query, stage in queries:
            info = self.execute_dax_query_global_verbose(dax_query)
            info["stage"] = stage
            attempts.append(info)
            if not info.get("ok"):
                continue
            res = info.get("result")
            if isinstance(res, dict) and _extract_table_names(res):
                info["attempts"] = attempts
                return info

        return {"ok": False, "stage": "schema", "error": "Schema discovery failed", "attempts": attempts}

    def dataset_tables_dax_fallback(self, user: Any, dataset_id: str) -> Dict[str, Any]:
        """API công khai cho router: thử INFO.TABLES / DMV khi REST không parse được tên bảng."""
        return self._dataset_tables_dax_fallback_user(user, dataset_id)

    def get_dataset_tables_global_verbose(self) -> Dict[str, Any]:
        tenant = (settings.power_bi_tenant_id or os.getenv("POWER_BI_TENANT_ID") or "").strip()
        workspace_id = (settings.power_bi_workspace_id or os.getenv("POWER_BI_WORKSPACE_ID") or "").strip()
        dataset_id = (settings.power_bi_dataset_id or os.getenv("POWER_BI_DATASET_ID") or "").strip()
        if not (tenant and workspace_id and dataset_id):
            return {"ok": False, "stage": "config", "error": "Missing POWER_BI_TENANT_ID/WORKSPACE_ID/DATASET_ID"}

        user = SimpleNamespace(
            user_id="global",
            power_bi_tenant_id=tenant,
            power_bi_workspace_id=workspace_id,
            power_bi_dataset_id=dataset_id,
        )

        token = self.get_access_token(user)
        if not token:
            return {"ok": False, "stage": "auth", "error": "Failed to obtain access token"}

        headers = self._get_headers(token)
        url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}/tables"
        try:
            response = requests.get(url, headers=headers, timeout=20)
        except Exception as e:
            return {"ok": False, "stage": "request", "error": str(e)}

        if response.status_code >= 400:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            if self._should_try_dax_for_dataset_tables_error(response.status_code, body):
                return self._dataset_tables_dax_fallback_global(user)
            return {"ok": False, "stage": "tables", "status_code": response.status_code, "body": body}

        try:
            first_data = response.json()
            result: Any = first_data
            if isinstance(first_data, dict):
                nl = first_data.get("@odata.nextLink")
                if not nl:
                    for k in first_data:
                        if isinstance(k, str) and "nextlink" in k.lower():
                            nl = first_data.get(k)
                            break
                if isinstance(nl, str) and nl.strip():
                    result = self._merge_odata_tables_pages(headers, first_data)
            val = result.get("value") if isinstance(result, dict) else None
            if isinstance(val, list) and len(val) > 0:
                return {"ok": True, "stage": "ok", "result": result}
            return self._dataset_tables_dax_fallback_global(user)
        except Exception:
            return {"ok": True, "stage": "ok", "result": (response.text or "")[:2000]}

    def get_table_columns_global_verbose(self, table_name: str) -> Dict[str, Any]:
        tenant = (settings.power_bi_tenant_id or os.getenv("POWER_BI_TENANT_ID") or "").strip()
        workspace_id = (settings.power_bi_workspace_id or os.getenv("POWER_BI_WORKSPACE_ID") or "").strip()
        dataset_id = (settings.power_bi_dataset_id or os.getenv("POWER_BI_DATASET_ID") or "").strip()
        table = (table_name or "").strip()
        if not table:
            return {"ok": False, "stage": "input", "error": "table_name is required"}
        if not (tenant and workspace_id and dataset_id):
            return {"ok": False, "stage": "config", "error": "Missing POWER_BI_TENANT_ID/WORKSPACE_ID/DATASET_ID"}

        user = SimpleNamespace(
            user_id="global",
            power_bi_tenant_id=tenant,
            power_bi_workspace_id=workspace_id,
            power_bi_dataset_id=dataset_id,
        )

        token = self.get_access_token(user)
        if not token:
            return {"ok": False, "stage": "auth", "error": "Failed to obtain access token"}

        headers = self._get_headers(token)
        # Power BI REST uses table name in the URL (not table id).
        url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}/tables/{table}/columns"
        try:
            response = requests.get(url, headers=headers, timeout=20)
        except Exception as e:
            return {"ok": False, "stage": "request", "error": str(e)}

        if response.status_code >= 400:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            # The /columns endpoint only works for Push API datasets. Fall back to INFO.COLUMNS().
            if response.status_code == 404 and "not Push API dataset" in body:
                attempts: list[Dict[str, Any]] = []

                escaped = table.replace('"', '""')
                dax = f'EVALUATE FILTER(INFO.COLUMNS(), [Table] = "{escaped}")'
                info = self.execute_dax_query_global_verbose(dax)
                info["stage"] = "info.columns"
                info["table"] = table
                attempts.append(info)
                if info.get("ok"):
                    info["attempts"] = attempts
                    return info

                # Try DMV-style access to columns; filter by table name if possible.
                dmv_dax = (
                    "EVALUATE "
                    f'FILTER($SYSTEM.TMSCHEMA_COLUMNS, [TableName] = "{escaped}")'
                )
                dmv = self.execute_dax_query_global_verbose(dmv_dax)
                dmv["stage"] = "dmv.tmschema_columns"
                dmv["table"] = table
                attempts.append(dmv)
                if dmv.get("ok"):
                    dmv["attempts"] = attempts
                    return dmv

                return {"ok": False, "stage": "schema", "error": "Schema discovery failed", "table": table, "attempts": attempts}
            return {"ok": False, "stage": "columns", "status_code": response.status_code, "body": body}

        try:
            return {"ok": True, "stage": "ok", "result": response.json()}
        except Exception:
            return {"ok": True, "stage": "ok", "result": (response.text or "")[:2000]}

    def get_dataset_tables_verbose(self, user: Any) -> Dict[str, Any]:
        workspace_id = (getattr(user, "power_bi_workspace_id", None) or "").strip()
        dataset_id = (getattr(user, "power_bi_dataset_id", None) or "").strip()
        if not workspace_id or not dataset_id:
            return {"ok": False, "stage": "config", "error": "Missing user Power BI workspace_id/dataset_id"}

        token = self.get_access_token(user)
        if not token:
            return {"ok": False, "stage": "auth", "error": "Failed to obtain access token"}

        headers = self._get_headers(token)
        url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}/tables"
        try:
            response = requests.get(url, headers=headers, timeout=20)
        except Exception as e:
            return {"ok": False, "stage": "request", "error": str(e)}

        if response.status_code >= 400:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            if self._should_try_dax_for_dataset_tables_error(response.status_code, body):
                return self._dataset_tables_dax_fallback_user(user, dataset_id)
            return {"ok": False, "stage": "tables", "status_code": response.status_code, "body": body}

        try:
            first_data = response.json()
            result: Any = first_data
            if isinstance(first_data, dict):
                nl = first_data.get("@odata.nextLink")
                if not nl:
                    for k in first_data:
                        if isinstance(k, str) and "nextlink" in k.lower():
                            nl = first_data.get(k)
                            break
                if isinstance(nl, str) and nl.strip():
                    result = self._merge_odata_tables_pages(headers, first_data)
            val = result.get("value") if isinstance(result, dict) else None
            if isinstance(val, list) and len(val) > 0:
                return {"ok": True, "stage": "ok", "result": result}
            return self._dataset_tables_dax_fallback_user(user, dataset_id)
        except Exception:
            return {"ok": True, "stage": "ok", "result": (response.text or "")[:2000]}

    def get_table_columns_verbose(self, user: Any, table_name: str) -> Dict[str, Any]:
        workspace_id = (getattr(user, "power_bi_workspace_id", None) or "").strip()
        dataset_id = (getattr(user, "power_bi_dataset_id", None) or "").strip()
        table = (table_name or "").strip()
        if not table:
            return {"ok": False, "stage": "input", "error": "table_name is required"}
        if not workspace_id or not dataset_id:
            return {"ok": False, "stage": "config", "error": "Missing user Power BI workspace_id/dataset_id"}

        token = self.get_access_token(user)
        if not token:
            return {"ok": False, "stage": "auth", "error": "Failed to obtain access token"}

        headers = self._get_headers(token)
        url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}/tables/{table}/columns"
        try:
            response = requests.get(url, headers=headers, timeout=20)
        except Exception as e:
            return {"ok": False, "stage": "request", "error": str(e)}

        if response.status_code >= 400:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            if response.status_code == 404 and "not Push API dataset" in body:
                attempts: list[Dict[str, Any]] = []
                escaped = table.replace('"', '""')
                info = self.execute_dax_query_verbose(
                    user,
                    f'EVALUATE FILTER(INFO.COLUMNS(), [Table] = "{escaped}")',
                    dataset_id=dataset_id,
                )
                info["stage"] = "info.columns"
                info["table"] = table
                attempts.append(info)
                if info.get("ok"):
                    info["attempts"] = attempts
                    return info

                dmv = self.execute_dax_query_verbose(
                    user,
                    f'EVALUATE FILTER($SYSTEM.TMSCHEMA_COLUMNS, [TableName] = "{escaped}")',
                    dataset_id=dataset_id,
                )
                dmv["stage"] = "dmv.tmschema_columns"
                dmv["table"] = table
                attempts.append(dmv)
                if dmv.get("ok"):
                    dmv["attempts"] = attempts
                    return dmv

                return {"ok": False, "stage": "schema", "error": "Schema discovery failed", "table": table, "attempts": attempts}
            return {"ok": False, "stage": "columns", "status_code": response.status_code, "body": body}

        try:
            return {"ok": True, "stage": "ok", "result": response.json()}
        except Exception:
            return {"ok": True, "stage": "ok", "result": (response.text or "")[:2000]}

    def get_portfolio_metrics_global(self) -> Optional[Dict[str, Any]]:
        """Backend-level wrapper around `get_portfolio_metrics` using global workspace/dataset."""
        dax_query = """
        EVALUATE
        {
            ("Total Loans", COUNTROWS('Loan')),
            ("Total Amount", SUM('Loan'[Amount])),
            ("Average Rate", AVERAGE('Loan'[InterestRate])),
            ("Default Rate %", DIVIDE(COUNTROWS(FILTER('Loan', 'Loan'[Status] = "Defaulted")), COUNTROWS('Loan'))*100),
            ("Avg Risk Score", AVERAGE('Customer'[RiskScore]))
        }
        """
        return self.execute_dax_query_global(dax_query)

    def get_risk_data_global(self) -> Optional[Dict[str, Any]]:
        """Backend-level wrapper around `get_risk_data` using global workspace/dataset."""
        dax_query = """
        EVALUATE
        CALCULATETABLE(
            SUMMARIZECOLUMNS(
                'Customer'[CustomerID],
                'Customer'[FullName],
                'Customer'[RiskScore],
                'Customer'[RiskLevel],
                "Total Amount", SUM('Loan'[Amount]),
                "Default Count", COUNTROWS(FILTER('Loan', 'Loan'[Status] = "Defaulted"))
            ),
            'Customer'[RiskLevel] = "High"
        )
        """
        return self.execute_dax_query_global(dax_query)

    # =========================================================================
    # Workspace & Dataset Operations
    # =========================================================================
    
    def get_workspaces(self, user: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Get all Power BI workspaces accessible to the user
        
        Args:
            user: User database object
        
        Returns:
            List of workspace objects or None
        """
        response = None
        try:
            token = self.get_access_token(user)
            if not token:
                return None
            
            headers = self._get_headers(token)
            url = f"{self.base_url}/groups"
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            workspaces = data.get("value", [])
            
            logger.info("✅ Retrieved %s workspaces for user %s", len(workspaces), self._safe_user_id(user))
            return workspaces
            
        except Exception as e:
            logger.error(f"❌ Error fetching workspaces: {str(e)}")
            return None
    
    def get_workspace_details(self, user: Any) -> Optional[Dict[str, Any]]:
        """
        Get details of user's primary workspace
        
        Args:
            user: User database object
        
        Returns:
            Workspace details or None
        """
        if not user.power_bi_workspace_id:
            logger.warning("No workspace ID configured for user %s", self._safe_user_id(user))
            return None
        
        try:
            token = self.get_access_token(user)
            if not token:
                return None
            
            headers = self._get_headers(token)
            url = f"{self.base_url}/groups/{user.power_bi_workspace_id}"
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            workspace = response.json()
            logger.info(f"✅ Retrieved workspace details: {workspace.get('name')}")
            return workspace
            
        except Exception as e:
            logger.error(f"❌ Error fetching workspace details: {str(e)}")
            return None
    
    def get_datasets(self, user: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Get all datasets in user's workspace
        
        Args:
            user: User database object
        
        Returns:
            List of datasets or None
        """
        if not user.power_bi_workspace_id:
            logger.warning("No workspace ID configured for user %s", self._safe_user_id(user))
            return None
        
        try:
            token = self.get_access_token(user)
            if not token:
                return None
            
            headers = self._get_headers(token)
            url = f"{self.base_url}/groups/{user.power_bi_workspace_id}/datasets"
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            datasets = data.get("value", [])
            
            logger.info(f"✅ Retrieved {len(datasets)} datasets from workspace {user.power_bi_workspace_id}")
            return datasets
            
        except Exception as e:
            logger.error(f"❌ Error fetching datasets: {str(e)}")
            return None
    
    def get_dataset_details(self, user: Any, dataset_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific dataset
        
        Args:
            user: User database object
            dataset_id: Dataset ID (uses user's default if not provided)
        
        Returns:
            Dataset details or None
        """
        dataset = dataset_id or user.power_bi_dataset_id
        if not dataset:
            logger.warning("No dataset ID provided for user %s", self._safe_user_id(user))
            return None
        
        if not user.power_bi_workspace_id:
            logger.warning("No workspace ID configured for user %s", self._safe_user_id(user))
            return None
        
        try:
            token = self.get_access_token(user)
            if not token:
                return None
            
            headers = self._get_headers(token)
            url = f"{self.base_url}/groups/{user.power_bi_workspace_id}/datasets/{dataset}"
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            dataset_info = response.json()
            logger.info(f"✅ Retrieved dataset details: {dataset_info.get('name')}")
            return dataset_info
            
        except Exception as e:
            logger.error(f"❌ Error fetching dataset details: {str(e)}")
            return None
    
    # =========================================================================
    # Data Query Operations (DAX/MDX)
    # =========================================================================
    
    def execute_dax_query(
        self,
        user: Any,
        dax_query: str,
        dataset_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute DAX query against user's dataset
        
        Args:
            user: User database object
            dax_query: DAX query string
            dataset_id: Dataset ID (uses user's default if not provided)
        
        Returns:
            Query results or None
        """
        dataset = dataset_id or user.power_bi_dataset_id
        if not dataset or not user.power_bi_workspace_id:
            logger.warning("Missing dataset or workspace ID for user %s", self._safe_user_id(user))
            return None
        
        try:
            token = self.get_access_token(user)
            if not token:
                return None
            
            headers = self._get_headers(token)
            url = f"{self.base_url}/groups/{user.power_bi_workspace_id}/datasets/{dataset}/executeQueries"
            
            payload = {
                "queries": [
                    {
                        "query": dax_query
                    }
                ],
                "serializerSettings": {
                    "includeNulls": True
                }
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ DAX query executed successfully")
            return result
            
        except requests.HTTPError as e:
            status_code = getattr(getattr(e, "response", None), "status_code", None) or getattr(response, "status_code", None)
            body = getattr(getattr(e, "response", None), "text", None) or getattr(response, "text", "") or ""
            body = (body or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            logger.error(f"❌ Error executing DAX query: status={status_code} body={body}")
            return None
        except Exception as e:
            logger.error(f"❌ Error executing DAX query: {str(e)}")
            return None
    
    def get_risk_data(self, user: Any) -> Optional[Dict[str, Any]]:
        """
        Get risk analysis data from Power BI
        Common query: High-risk customers, portfolio risk metrics
        
        Args:
            user: User database object
        
        Returns:
            Risk data or None
        """
        dax_query = """
        EVALUATE
        SUMMARIZECOLUMNS(
            'Customer'[CustomerID],
            'Customer'[FullName],
            'Customer'[RiskScore],
            'Customer'[RiskLevel],
            'Loan'[Status],
            "Total Amount", SUM('Loan'[Amount]),
            "Default Count", COUNTIF('Loan'[Status], "Defaulted")
        )
        WHERE 'Customer'[RiskLevel] = "High"
        """
        return self.execute_dax_query(user, dax_query)
    
    def get_portfolio_metrics(self, user: Any) -> Optional[Dict[str, Any]]:
        """
        Get portfolio metrics from Power BI
        
        Args:
            user: User database object
        
        Returns:
            Portfolio metrics or None
        """
        dax_query = """
        EVALUATE
        {
            ("Total Loans", COUNTROWS('Loan')),
            ("Total Amount", SUM('Loan'[Amount])),
            ("Average Rate", AVERAGE('Loan'[InterestRate])),
            ("Default Rate %", DIVIDE(COUNTROWS(FILTER('Loan', 'Loan'[Status] = "Defaulted")), COUNTROWS('Loan'))*100),
            ("Avg Risk Score", AVERAGE('Customer'[RiskScore]))
        }
        """
        return self.execute_dax_query(user, dax_query)
    
    def get_customer_risk_profile(
        self,
        user: Any,
        customer_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific customer's risk profile from Power BI
        
        Args:
            user: User database object
            customer_id: Customer ID to query
        
        Returns:
            Customer risk profile or None
        """
        dax_query = f"""
        EVALUATE
        SUMMARIZECOLUMNS(
            'Customer'[CustomerID],
            'Customer'[FullName],
            'Customer'[RiskScore],
            'Customer'[CreditScore],
            'Customer'[DTI],
            'Customer'[EmploymentStatus],
            "Total Loans", COUNTROWS('Loan'),
            "Total Amount", SUM('Loan'[Amount]),
            "Defaulted Loans", COUNTIF('Loan'[Status], "Defaulted"),
            "Avg Interest Rate", AVERAGE('Loan'[InterestRate])
        )
        WHERE 'Customer'[CustomerID] = {customer_id}
        """
        return self.execute_dax_query(user, dax_query)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _get_headers(self, token: str) -> Dict[str, str]:
        """Get HTTP headers with authorization"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def refresh_dataset(self, user: Any, dataset_id: Optional[str] = None) -> bool:
        """
        Trigger dataset refresh in Power BI
        
        Args:
            user: User database object
            dataset_id: Dataset ID (uses user's default if not provided)
        
        Returns:
            True if refresh triggered successfully
        """
        dataset = dataset_id or user.power_bi_dataset_id
        if not dataset or not user.power_bi_workspace_id:
            logger.warning("Missing dataset or workspace ID for user %s", self._safe_user_id(user))
            return False
        
        try:
            token = self.get_access_token(user)
            if not token:
                return False
            
            headers = self._get_headers(token)
            url = f"{self.base_url}/groups/{user.power_bi_workspace_id}/datasets/{dataset}/refreshes"
            
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"✅ Dataset refresh triggered for {dataset}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error triggering dataset refresh: {str(e)}")
            return False
    
    def test_connection(self, user: Any) -> bool:
        """
        Test Power BI connection for a user
        
        Args:
            user: User database object
        
        Returns:
            True if connection successful
        """
        try:
            token = self.get_access_token(user)
            if not token:
                return False
            
            # Try to get workspace details as a test
            workspace = self.get_workspace_details(user)
            return workspace is not None
            
        except Exception as e:
            logger.error(f"❌ Power BI connection test failed: {str(e)}")
            return False

    @staticmethod
    def _normalize_id(value: Optional[str]) -> str:
        return str(value or "").strip()

    @staticmethod
    def _is_guid(value: str) -> bool:
        return bool(GUID_RE.match(value))

    @staticmethod
    def _trim_body(text: str, limit: int = 2000) -> str:
        value = (text or "").strip()
        if len(value) > limit:
            return value[:limit] + "..."
        return value

    def _tenant_exists(self, tenant_id: str) -> Optional[bool]:
        # Lightweight existence check before trying authenticated Power BI calls.
        url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
        try:
            response = requests.get(url, timeout=8)
            return response.status_code == 200
        except Exception:
            return None

    def _validate_workspace_access(self, token: str, workspace_id: str) -> Dict[str, Any]:
        headers = self._get_headers(token)
        url = f"{self.base_url}/groups/{workspace_id}"
        try:
            response = requests.get(url, headers=headers, timeout=12)
        except Exception as exc:
            raise PowerBIConfigValidationError(
                code="POWERBI_VALIDATION_REQUEST_FAILED",
                message=f"Power BI request failed while validating workspace: {str(exc)}",
                status_code=400,
            ) from exc

        if response.status_code in (401, 403):
            raise PowerBIConfigValidationError(
                code="INSUFFICIENT_POWERBI_PERMISSION",
                message="Service principal does not have access to the requested workspace.",
                status_code=403,
            )
        if response.status_code == 404:
            raise PowerBIConfigValidationError(
                code="WORKSPACE_NOT_FOUND",
                message="Workspace was not found or is not accessible by the service principal.",
                status_code=400,
            )
        if response.status_code >= 400:
            body = self._trim_body(response.text)
            raise PowerBIConfigValidationError(
                code="POWERBI_WORKSPACE_VALIDATION_FAILED",
                message=f"Workspace validation failed: {body or f'HTTP {response.status_code}'}",
                status_code=400,
            )
        try:
            return response.json()
        except Exception:
            return {}

    def _validate_dataset_in_workspace(
        self,
        token: str,
        workspace_id: str,
        dataset_id: str,
    ) -> Dict[str, Any]:
        headers = self._get_headers(token)
        scoped_url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}"
        try:
            response = requests.get(scoped_url, headers=headers, timeout=12)
        except Exception as exc:
            raise PowerBIConfigValidationError(
                code="POWERBI_VALIDATION_REQUEST_FAILED",
                message=f"Power BI request failed while validating dataset: {str(exc)}",
                status_code=400,
            ) from exc

        if response.status_code in (401, 403):
            raise PowerBIConfigValidationError(
                code="INSUFFICIENT_POWERBI_PERMISSION",
                message="Service principal does not have permission to access the dataset.",
                status_code=403,
            )
        if response.status_code == 404:
            global_url = f"{self.base_url}/datasets/{dataset_id}"
            try:
                global_response = requests.get(global_url, headers=headers, timeout=12)
            except Exception:
                global_response = None

            if global_response is not None and global_response.status_code == 200:
                raise PowerBIConfigValidationError(
                    code="DATASET_NOT_IN_WORKSPACE",
                    message="Dataset exists but does not belong to the configured workspace.",
                    status_code=400,
                )

            raise PowerBIConfigValidationError(
                code="DATASET_NOT_FOUND",
                message="Dataset was not found.",
                status_code=400,
            )
        if response.status_code >= 400:
            body = self._trim_body(response.text)
            raise PowerBIConfigValidationError(
                code="POWERBI_DATASET_VALIDATION_FAILED",
                message=f"Dataset validation failed: {body or f'HTTP {response.status_code}'}",
                status_code=400,
            )
        try:
            return response.json()
        except Exception:
            return {}

    def validate_account_powerbi_config(
        self,
        user: Any,
        tenant_id: str,
        workspace_id: str,
        dataset_id: str,
    ) -> Dict[str, Any]:
        tenant = self._normalize_id(tenant_id)
        workspace = self._normalize_id(workspace_id)
        dataset = self._normalize_id(dataset_id)

        if not tenant or not self._is_guid(tenant):
            raise PowerBIConfigValidationError(
                code="INVALID_TENANT_ID",
                message="tenant_id is required and must be a valid GUID.",
                status_code=422,
            )
        if not workspace or not self._is_guid(workspace):
            raise PowerBIConfigValidationError(
                code="INVALID_WORKSPACE_ID",
                message="workspace_id is required and must be a valid GUID.",
                status_code=422,
            )
        if not dataset or not self._is_guid(dataset):
            raise PowerBIConfigValidationError(
                code="INVALID_DATASET_ID",
                message="dataset_id is required and must be a valid GUID.",
                status_code=422,
            )

        tenant_exists = self._tenant_exists(tenant)
        if tenant_exists is None:
            raise PowerBIConfigValidationError(
                code="POWERBI_VALIDATION_REQUEST_FAILED",
                message="Unable to verify tenant at this time. Please retry.",
                status_code=400,
            )
        if not tenant_exists:
            raise PowerBIConfigValidationError(
                code="INVALID_TENANT_ID",
                message="Tenant was not found in Azure AD.",
                status_code=400,
            )

        token = self.get_access_token(user=user, tenant_id=tenant)
        if not token:
            raise PowerBIConfigValidationError(
                code="POWERBI_TOKEN_ERROR",
                message="Failed to obtain Power BI access token for the provided tenant/service principal.",
                status_code=400,
            )

        workspace_info = self._validate_workspace_access(token=token, workspace_id=workspace)
        dataset_info = self._validate_dataset_in_workspace(
            token=token,
            workspace_id=workspace,
            dataset_id=dataset,
        )

        return {
            "tenant_id": tenant,
            "workspace_id": workspace,
            "dataset_id": dataset,
            "workspace_name": str(workspace_info.get("name") or "").strip() or None,
            "dataset_name": str(dataset_info.get("name") or "").strip() or None,
        }

    def get_account_powerbi_status(self, user: Any) -> Dict[str, Any]:
        tenant_id = self._normalize_id(getattr(user, "power_bi_tenant_id", None))
        workspace_id = self._normalize_id(getattr(user, "power_bi_workspace_id", None))
        dataset_id = self._normalize_id(getattr(user, "power_bi_dataset_id", None))
        workspace_name = self._normalize_id(getattr(user, "power_bi_workspace_name", None)) or None
        dataset_name = self._normalize_id(getattr(user, "power_bi_dataset_name", None)) or None

        if not bool(getattr(user, "power_bi_enabled", False)) or not all([tenant_id, workspace_id, dataset_id]):
            return {
                "connected": False,
                "tenant_id": tenant_id or None,
                "workspace_id": workspace_id or None,
                "workspace_name": workspace_name,
                "dataset_id": dataset_id or None,
                "dataset_name": dataset_name,
                "validation_error_code": "POWERBI_NOT_CONFIGURED",
                "message": "Power BI is not configured for this account.",
            }

        try:
            validated = self.validate_account_powerbi_config(
                user=user,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                dataset_id=dataset_id,
            )
            return {
                "connected": True,
                "tenant_id": validated["tenant_id"],
                "workspace_id": validated["workspace_id"],
                "workspace_name": validated["workspace_name"] or workspace_name,
                "dataset_id": validated["dataset_id"],
                "dataset_name": validated["dataset_name"] or dataset_name,
                "validation_error_code": None,
                "message": "Power BI configuration is valid.",
            }
        except PowerBIConfigValidationError as exc:
            return {
                "connected": False,
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "workspace_name": workspace_name,
                "dataset_id": dataset_id,
                "dataset_name": dataset_name,
                "validation_error_code": exc.code,
                "message": exc.message,
            }

    def update_user_powerbi_config(
        self,
        db: Session,
        user: Any,
        workspace_id: str,
        dataset_id: str,
        tenant_id: Optional[str] = None,
        workspace_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
    ) -> bool:
        """Persist Power BI config outside the database."""
        try:
            del db
            self._config_dir.mkdir(parents=True, exist_ok=True)
            existing = self._load_user_config(user)
            wn = str(workspace_name or "").strip() or str(existing.get("power_bi_workspace_name") or "").strip()
            dn = str(dataset_name or "").strip() or str(existing.get("power_bi_dataset_name") or "").strip()
            payload = {
                "power_bi_enabled": True,
                "power_bi_workspace_id": str(workspace_id).strip(),
                "power_bi_dataset_id": str(dataset_id).strip(),
                "power_bi_tenant_id": str(tenant_id or "").strip(),
                "power_bi_workspace_name": wn,
                "power_bi_dataset_name": dn,
                "power_bi_last_sync": datetime.utcnow().isoformat(),
                "power_bi_table_names": [
                    str(item).strip()
                    for item in (existing.get("power_bi_table_names") or [])
                    if str(item).strip()
                ],
            }
            self._config_path(user).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Updated Power BI config for user %s", self._get_user_id(user))
            return True
        except Exception as e:
            logger.error("Error updating Power BI config: %s", str(e))
            return False


# Global service instance
powerbi_service = PowerBIService()
