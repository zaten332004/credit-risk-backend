from fastapi import APIRouter

from app.schemas.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    RiskRequest,
    RiskResponse,
)
from app.services.services import simple_chat_reply, simple_credit_risk_score

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/risk/score", response_model=RiskResponse)
async def score_risk(payload: RiskRequest) -> RiskResponse:
    result = simple_credit_risk_score(payload)
    return RiskResponse(**result)


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    answer = simple_chat_reply(payload.message)
    return ChatResponse(answer=answer)
