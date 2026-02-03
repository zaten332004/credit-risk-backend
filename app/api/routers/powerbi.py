"""
Power BI Integration API Endpoints
Manage user Power BI workspaces and fetch data
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.models import UserDB
from app.db.session import get_db
from app.services.powerbi_service import powerbi_service

router = APIRouter(prefix="/powerbi", tags=["Power BI Integration"])


# =========================================================================
# Pydantic Models
# =========================================================================

class PowerBIConfigRequest(BaseModel):
    """Request to configure Power BI workspace"""
    workspace_id: str
    dataset_id: str
    tenant_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "workspace_id": "f36e0f6d-410f-4ae3-8450-5fcebf90cc31",
                "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "72f988bf-86f1-41af-91ab-2d7cd011db47"
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
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    dataset_id: Optional[str] = None
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


# =========================================================================
# API Endpoints
# =========================================================================

@router.post("/configure", response_model=dict)
async def configure_powerbi(
    config: PowerBIConfigRequest,
    current_user: UserDB = Depends(get_current_active_user),
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
            tenant_id=config.tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to configure Power BI"
            )
        
        return {
            "success": True,
            "message": "Power BI workspace configured successfully",
            "workspace_id": config.workspace_id,
            "dataset_id": config.dataset_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error configuring Power BI: {str(e)}"
        )


@router.get("/test-connection", response_model=PowerBIConnectionResponse)
async def test_powerbi_connection(
    current_user: UserDB = Depends(get_current_active_user)
):
    """
    Test Power BI connection for current user
    """
    if not current_user.power_bi_enabled:
        return PowerBIConnectionResponse(
            connected=False,
            message="Power BI not configured for this user"
        )
    
    connected = powerbi_service.test_connection(current_user)
    
    workspace_details = None
    workspace_name = None
    if connected:
        workspace_details = powerbi_service.get_workspace_details(current_user)
        workspace_name = workspace_details.get("name") if workspace_details else None
    
    return PowerBIConnectionResponse(
        connected=connected,
        workspace_id=current_user.power_bi_workspace_id,
        workspace_name=workspace_name,
        dataset_id=current_user.power_bi_dataset_id,
        last_sync=current_user.power_bi_last_sync.isoformat() if current_user.power_bi_last_sync else None,
        message="✅ Connected" if connected else "❌ Connection failed"
    )


@router.get("/workspaces", response_model=list)
async def get_powerbi_workspaces(
    current_user: UserDB = Depends(get_current_active_user)
):
    """
    Get all Power BI workspaces accessible to current user
    """
    workspaces = powerbi_service.get_workspaces(current_user)
    
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
    current_user: UserDB = Depends(get_current_active_user)
):
    """
    Get all datasets in user's configured workspace
    """
    if not current_user.power_bi_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI workspace not configured"
        )
    
    datasets = powerbi_service.get_datasets(current_user)
    
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
    current_user: UserDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get risk analysis data from Power BI
    - High/Medium/Low risk customer counts
    - Average risk score
    - Default rate
    - Portfolio exposure
    """
    if not current_user.power_bi_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI not configured for this user"
        )
    
    risk_data = powerbi_service.get_risk_data(current_user)
    
    if risk_data is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch risk data from Power BI"
        )
    
    # Update last sync timestamp
    current_user.power_bi_last_sync = __import__("datetime").datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "data": risk_data,
        "timestamp": current_user.power_bi_last_sync.isoformat()
    }


@router.get("/portfolio-metrics", response_model=dict)
async def get_powerbi_portfolio_metrics(
    current_user: UserDB = Depends(get_current_active_user),
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
    if not current_user.power_bi_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI not configured for this user"
        )
    
    metrics = powerbi_service.get_portfolio_metrics(current_user)
    
    if metrics is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch portfolio metrics from Power BI"
        )
    
    # Update last sync timestamp
    current_user.power_bi_last_sync = __import__("datetime").datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "metrics": metrics,
        "timestamp": current_user.power_bi_last_sync.isoformat()
    }


@router.get("/customer/{customer_id}/risk-profile", response_model=dict)
async def get_customer_risk_profile(
    customer_id: int,
    current_user: UserDB = Depends(get_current_active_user)
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
    if not current_user.power_bi_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI not configured for this user"
        )
    
    profile = powerbi_service.get_customer_risk_profile(current_user, customer_id)
    
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
    current_user: UserDB = Depends(get_current_active_user)
):
    """
    Trigger Power BI dataset refresh
    """
    if not current_user.power_bi_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Power BI not configured for this user"
        )
    
    success = powerbi_service.refresh_dataset(current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger dataset refresh"
        )
    
    return {
        "success": True,
        "message": "Dataset refresh triggered successfully"
    }


@router.delete("/disconnect", response_model=dict)
async def disconnect_powerbi(
    current_user: UserDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Power BI from user account
    """
    try:
        current_user.power_bi_enabled = False
        current_user.power_bi_workspace_id = None
        current_user.power_bi_dataset_id = None
        current_user.power_bi_tenant_id = None
        current_user.power_bi_api_key = None
        
        db.commit()
        
        return {
            "success": True,
            "message": "Power BI disconnected successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error disconnecting Power BI: {str(e)}"
        )
