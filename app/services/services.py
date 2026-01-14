from __future__ import annotations

from app.schemas.schemas import RiskRequest


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


def simple_chat_reply(message: str) -> str:
    """
    Placeholder chatbot behavior.
    Later: integrate Langflow/LangChain + AWS (Bedrock/Lambda) or your chosen LLM stack.
    """
    msg = message.strip().lower()
    if "risk" in msg or "rủi ro" in msg:
        return (
            "Bạn có thể gọi POST /api/v1/risk/score với income, debt, age, credit_history_months "
            "để nhận điểm rủi ro (0..1) và nhãn low/medium/high."
        )
    if "power bi" in msg:
        return "Backend này cung cấp API để Power BI/Flutter gọi lấy điểm rủi ro và dữ liệu tổng hợp."
    return "Mình đã nhận câu hỏi. Hãy mô tả dữ liệu khách hàng/bài toán để mình hướng dẫn endpoint phù hợp."
