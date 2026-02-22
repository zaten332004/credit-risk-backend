"""
Power BI Integration Service
Handles multi-workspace Power BI connections and data retrieval
"""
import os
import json
import logging
from types import SimpleNamespace
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from functools import lru_cache

import requests
from sqlalchemy.orm import Session

from app.db.models import UserDB
from app.core.config import settings

logger = logging.getLogger(__name__)


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
    
    # =========================================================================
    # Authentication & Token Management
    # =========================================================================
    
    def get_access_token(
        self,
        user: UserDB,
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
                logger.warning(f"Missing Power BI credentials for user {user.user_id}")
                return None
            
            # Check cache first
            cache_key = f"{user.user_id}_{tenant}"
            if cache_key in self.token_cache:
                token, expiry = self.token_cache[cache_key]
                if datetime.utcnow() < expiry:
                    logger.debug(f"Using cached token for user {user.user_id}")
                    return token
            
            token, expires_in = self._request_token(tenant=tenant, client_id=client, client_secret=secret)
            if not token:
                return None
            
            # Cache token
            expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
            self.token_cache[cache_key] = (token, expiry)
            
            logger.info(f"✅ New access token obtained for user {user.user_id}")
            return token
            
        except requests.RequestException as e:
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
        payload = {"queries": [{"query": dax_query}], "serializerSettings": {"includeNulls": True}}

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
            return {"ok": True, "stage": "ok", "result": response.json()}
        except Exception:
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000] + "..."
            return {"ok": True, "stage": "ok", "result": body}

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
            # The /tables endpoint only works for Push API datasets. For import/semantic models,
            # fall back to executeQueries with INFO.TABLES() if available.
            if response.status_code == 404 and "not Push API dataset" in body:
                attempts: list[Dict[str, Any]] = []

                info = self.execute_dax_query_global_verbose("EVALUATE INFO.TABLES()")
                info["stage"] = "info.tables"
                attempts.append(info)
                if info.get("ok"):
                    return info

                # Some dataset types don't support INFO.*; try DMV-style access (may or may not be enabled).
                dmv = self.execute_dax_query_global_verbose("EVALUATE $SYSTEM.TMSCHEMA_TABLES")
                dmv["stage"] = "dmv.tmschema_tables"
                attempts.append(dmv)
                if dmv.get("ok"):
                    dmv["attempts"] = attempts
                    return dmv

                return {"ok": False, "stage": "schema", "error": "Schema discovery failed", "attempts": attempts}
            return {"ok": False, "stage": "tables", "status_code": response.status_code, "body": body}

        try:
            return {"ok": True, "stage": "ok", "result": response.json()}
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
    
    def get_workspaces(self, user: UserDB) -> Optional[List[Dict[str, Any]]]:
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
            
            logger.info(f"✅ Retrieved {len(workspaces)} workspaces for user {user.user_id}")
            return workspaces
            
        except Exception as e:
            logger.error(f"❌ Error fetching workspaces: {str(e)}")
            return None
    
    def get_workspace_details(self, user: UserDB) -> Optional[Dict[str, Any]]:
        """
        Get details of user's primary workspace
        
        Args:
            user: User database object
        
        Returns:
            Workspace details or None
        """
        if not user.power_bi_workspace_id:
            logger.warning(f"No workspace ID configured for user {user.user_id}")
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
    
    def get_datasets(self, user: UserDB) -> Optional[List[Dict[str, Any]]]:
        """
        Get all datasets in user's workspace
        
        Args:
            user: User database object
        
        Returns:
            List of datasets or None
        """
        if not user.power_bi_workspace_id:
            logger.warning(f"No workspace ID configured for user {user.user_id}")
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
    
    def get_dataset_details(self, user: UserDB, dataset_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
            logger.warning(f"No dataset ID provided for user {user.user_id}")
            return None
        
        if not user.power_bi_workspace_id:
            logger.warning(f"No workspace ID configured for user {user.user_id}")
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
        user: UserDB,
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
            logger.warning(f"Missing dataset or workspace ID for user {user.user_id}")
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
    
    def get_risk_data(self, user: UserDB) -> Optional[Dict[str, Any]]:
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
    
    def get_portfolio_metrics(self, user: UserDB) -> Optional[Dict[str, Any]]:
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
        user: UserDB,
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
    
    def refresh_dataset(self, user: UserDB, dataset_id: Optional[str] = None) -> bool:
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
            logger.warning(f"Missing dataset or workspace ID for user {user.user_id}")
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
    
    def update_user_powerbi_config(
        self,
        db: Session,
        user: UserDB,
        workspace_id: str,
        dataset_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Update user's Power BI configuration
        
        Args:
            db: Database session
            user: User database object
            workspace_id: Power BI Workspace ID
            dataset_id: Power BI Dataset ID
            tenant_id: Optional Azure Tenant ID
        
        Returns:
            True if update successful
        """
        try:
            user.power_bi_enabled = True
            user.power_bi_workspace_id = workspace_id
            user.power_bi_dataset_id = dataset_id
            if tenant_id:
                user.power_bi_tenant_id = tenant_id
            user.updated_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"✅ Updated Power BI config for user {user.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating Power BI config: {str(e)}")
            db.rollback()
            return False
    
    def test_connection(self, user: UserDB) -> bool:
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


# Global service instance
powerbi_service = PowerBIService()
