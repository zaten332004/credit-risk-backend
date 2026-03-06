"""
Risk service: business logic for risk scoring & analysis
"""
from typing import Optional

from app.schemas.schemas import RiskExplainResponse, RiskRequest, RiskScoreDetail
from app.services import customer_service


def simple_credit_risk_score(payload: RiskRequest) -> dict:
    """
    Baseline heuristic scoring to keep the backend functional.
    Replace with a trained model (sklearn, SageMaker endpoint, etc.) later.
    """
    dti = (payload.debt / payload.income) if payload.income > 0 else 1.0  # debt-to-income
    # Normalize rough factors into [0,1]
    dti_factor = min(max(dti, 0.0), 2.0) / 2.0
    age_factor = 1.0 - min(max((payload.age - 18) / (70 - 18), 0.0), 1.0)
    history_factor = 1.0 - min(max(payload.credit_history_months / 120.0, 0.0), 1.0)

    risk_score = 0.6 * dti_factor + 0.2 * age_factor + 0.2 * history_factor
    if risk_score < 0.33:
        label = "low"
    elif risk_score < 0.66:
        label = "medium"
    else:
        label = "high"

    explanation = (
        f"DTI={dti:.2f}, age={payload.age}, history_months={payload.credit_history_months}. "
        f"Higher DTI / younger age / shorter history increases risk."
    )
    return {"risk_score": float(round(risk_score, 4)), "risk_label": label, "explanation": explanation}


def score_to_pd_lgd_ead(risk_score: float) -> RiskScoreDetail:
    pd = min(max(risk_score, 0.01), 0.99)
    lgd = 0.4 + 0.3 * risk_score
    ead = 100_000  # demo
    el = pd * lgd * ead
    return RiskScoreDetail(pd=pd, lgd=lgd, ead=ead, el=el, risk_score=risk_score, confidence=0.8, model_version="v1")


def explain_risk(customer_id: int) -> RiskExplainResponse:
    # Demo SHAP-like output
    return RiskExplainResponse(feature_importance={"income": -0.3, "debt": 0.4, "age": -0.1, "credit_history": -0.2})


def get_customer_for_risk(customer_id: int):
    """Helper to get customer for risk calculation"""
    return customer_service.get_customer(customer_id)
