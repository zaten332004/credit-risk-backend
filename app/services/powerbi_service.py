"""
Power BI Integration Service
Handles multi-workspace Power BI connections and data retrieval
"""
import os
import json
import logging
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
    POWER_BI_AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
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
            # Use provided credentials or environment variables
            tenant = tenant_id or user.power_bi_tenant_id or os.getenv("POWER_BI_TENANT_ID")
            client = client_id or os.getenv("POWER_BI_CLIENT_ID")
            secret = client_secret or os.getenv("POWER_BI_CLIENT_SECRET")
            
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
            
            # Request new token
            auth_url = self.POWER_BI_AUTH_URL.format(tenant_id=tenant)
            
            payload = {
                "grant_type": "client_credentials",
                "client_id": client,
                "client_secret": secret,
                "resource": "https://analysis.windows.net/powerbi/api"
            }
            
            response = requests.post(auth_url, data=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            
            # Cache token
            expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
            self.token_cache[cache_key] = (token, expiry)
            
            logger.info(f"✅ New access token obtained for user {user.user_id}")
            return token
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to get Power BI access token: {str(e)}")
            return None
    
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
            ("Default Rate %", DIVIDE(COUNTIF('Loan'[Status], "Defaulted"), COUNTROWS('Loan'))*100),
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
