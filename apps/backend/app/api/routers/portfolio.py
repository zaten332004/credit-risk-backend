"""
Portfolio & aggregated metrics endpoints
"""
from typing import Optional

from fastapi import APIRouter, Depends

from app.core.security import get_current_analyst_user, get_current_manager_user
from app.schemas.schemas import (
    ConcentrationResponse,
    PortfolioCompareBody,
    PortfolioCompareResponse,
    PortfolioKPIResponse,
    PortfolioTrendResponse,
    RiskDistributionResponse,
    User,
)
from app.services import portfolio_service

router = APIRouter()


@router.get("/portfolio/kpi", response_model=PortfolioKPIResponse, tags=["portfolio"])
async def portfolio_kpi_endpoint(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    segment: Optional[str] = None,
    current_user: User = Depends(get_current_analyst_user),  # Analyst+ có thể xem KPI dashboard
) -> PortfolioKPIResponse:
    return portfolio_service.compute_portfolio_kpi(date_from, date_to, segment)


@router.get("/portfolio/risk-distribution", response_model=RiskDistributionResponse, tags=["portfolio"])
async def portfolio_risk_distribution_endpoint(
    group_by: Optional[str] = None,
    current_user: User = Depends(get_current_manager_user),  # Chỉ Manager+
) -> RiskDistributionResponse:
    return portfolio_service.risk_distribution(group_by)


@router.get("/portfolio/concentration", response_model=ConcentrationResponse, tags=["portfolio"])
async def portfolio_concentration_endpoint(
    top_n: int = 10,
    current_user: User = Depends(get_current_manager_user),  # Chỉ Manager+
) -> ConcentrationResponse:
    return portfolio_service.concentration(top_n)


@router.get("/portfolio/trend", response_model=PortfolioTrendResponse, tags=["portfolio"])
async def portfolio_trend_endpoint(
    metric: str,
    interval: str = "month",
    current_user: User = Depends(get_current_manager_user),  # Chỉ Manager+
) -> PortfolioTrendResponse:
    return portfolio_service.portfolio_trend(metric, interval)


@router.post("/portfolio/compare", response_model=PortfolioCompareResponse, tags=["portfolio"])
async def portfolio_compare_endpoint(
    body: PortfolioCompareBody,
    current_user: User = Depends(get_current_manager_user),  # Chỉ Manager+
) -> PortfolioCompareResponse:
    return portfolio_service.portfolio_compare(body)
