"""
Risk analysis & scoring endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_active_user
from app.schemas.schemas import (
    RiskAnalyzeBody,
    RiskBatchBody,
    RiskBatchResult,
    RiskExplainResponse,
    RiskModelVersion,
    RiskRequest,
    RiskResponse,
    RiskScoreDetail,
    RiskSimulationBody,
    RiskSimulationResult,
    User,
)
from app.services import risk_service

router = APIRouter()


@router.post("/risk/score", response_model=RiskResponse, tags=["risk"])
async def score_risk(payload: RiskRequest) -> RiskResponse:
    """Calculate risk score - public endpoint for demo compatibility"""
    result = risk_service.simple_credit_risk_score(payload)
    return RiskResponse(**result)


@router.get("/risk/score/{customer_id}", response_model=RiskScoreDetail, tags=["risk"])
async def score_risk_for_customer(
    customer_id: int,
    as_of_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> RiskScoreDetail:
    customer = risk_service.get_customer_for_risk(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # Demo: dùng lại heuristic theo income/debt giả định
    req = RiskRequest(
        income=customer.income,
        debt=customer.income * 0.3,
        age=customer.age,
        credit_history_months=24,
    )
    base = risk_service.simple_credit_risk_score(req)
    return risk_service.score_to_pd_lgd_ead(base["risk_score"])


@router.post("/risk/analyze", response_model=RiskScoreDetail, tags=["risk"])
async def risk_analyze_endpoint(
    body: RiskAnalyzeBody,
    current_user: User = Depends(get_current_active_user),
) -> RiskScoreDetail:
    # Map từ dict vào RiskRequest đơn giản
    data = body.customer_data
    req = RiskRequest(
        income=data.get("income", 0.0),
        debt=data.get("debt", 0.0),
        age=data.get("age", 30),
        credit_history_months=data.get("credit_history_months", 12),
    )
    base = risk_service.simple_credit_risk_score(req)
    return risk_service.score_to_pd_lgd_ead(base["risk_score"])


@router.post("/risk/batch", response_model=RiskBatchResult, tags=["risk"])
async def risk_batch_endpoint(
    body: RiskBatchBody,
    current_user: User = Depends(get_current_active_user),
) -> RiskBatchResult:
    results = []
    for rec in body.records[:500]:
        req = RiskRequest(
            income=rec.get("income", 0.0),
            debt=rec.get("debt", 0.0),
            age=rec.get("age", 30),
            credit_history_months=rec.get("credit_history_months", 12),
        )
        base = risk_service.simple_credit_risk_score(req)
        results.append(risk_service.score_to_pd_lgd_ead(base["risk_score"]))

    summary = {"count": len(results), "avg_pd": sum(r.pd for r in results) / max(len(results), 1)}
    return RiskBatchResult(results=results, summary=summary)


@router.post("/risk/simulation", response_model=RiskSimulationResult, tags=["risk"])
async def risk_simulation_endpoint(
    body: RiskSimulationBody,
    current_user: User = Depends(get_current_active_user),
) -> RiskSimulationResult:
    # Demo: trả về base_data + từng scenario
    scenario_results = []
    for s in body.scenarios:
        scenario_results.append({"scenario": s, "delta_el": 10_000})
    return RiskSimulationResult(scenario_results=scenario_results)


@router.get("/risk/model/version", response_model=List[RiskModelVersion], tags=["risk"])
async def risk_model_versions_endpoint(
    current_user: User = Depends(get_current_active_user),
) -> List[RiskModelVersion]:
    # Demo: 1 version
    from datetime import datetime

    return [
        RiskModelVersion(version="v1", accuracy=0.85, deployed_at=datetime.utcnow()),
    ]


@router.get("/risk/explain/{customer_id}", response_model=RiskExplainResponse, tags=["risk"])
async def risk_explain_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> RiskExplainResponse:
    customer = risk_service.get_customer_for_risk(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return risk_service.explain_risk(customer_id)
