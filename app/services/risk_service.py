"""
Risk service: business logic for risk scoring & analysis
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from app.schemas.schemas import RiskExplainResponse, RiskRequest, RiskScoreDetail
from app.services import customer_service


def _build_explanation_detail(
    *,
    payload: RiskRequest,
    loan_type_original: str,
    employment_original: str,
    dti: float,
    dti_factor: float,
    age_factor: float,
    history_factor: float,
    credit_score: int,
    credit_score_factor: float,
    loan_type: str,
    loan_type_factor: float,
    interest_rate: float,
    interest_factor: float,
    loan_term: float,
    term_factor: float,
    collateral_ratio: float,
    collateral_factor: float,
    employment_factor: float,
    raw_risk: float,
    risk_score: float,
    label: str,
    cic_score: int,
    cic_group: str,
    cic_rating: str,
) -> Dict[str, Any]:
    """JSON-serializable breakdown for structured risk explanation UI."""
    keys = [
        "dti",
        "age",
        "history",
        "credit_score",
        "loan_type",
        "interest",
        "term",
        "collateral",
        "employment",
    ]
    weights = [0.28, 0.10, 0.12, 0.18, 0.08, 0.08, 0.06, 0.06, 0.04]
    factors = [
        dti_factor,
        age_factor,
        history_factor,
        credit_score_factor,
        loan_type_factor,
        interest_factor,
        term_factor,
        collateral_factor,
        employment_factor,
    ]
    contributions: List[Dict[str, Any]] = [
        {"key": k, "weight": w, "factor": round(f, 6), "contrib": round(w * f, 6)}
        for k, w, f in zip(keys, weights, factors)
    ]
    cv = payload.collateral_value
    collateral_value_num = float(cv) if cv is not None else None

    return {
        "income": float(payload.income),
        "debt": float(payload.debt),
        "age": int(payload.age),
        "credit_history_months": int(payload.credit_history_months),
        "credit_score": int(credit_score),
        "loan_type_code": loan_type,
        "loan_type_display": loan_type_original or None,
        "interest_rate": float(interest_rate),
        "loan_term": float(loan_term),
        "collateral_value": collateral_value_num,
        "employment_display": employment_original or None,
        "dti": float(dti),
        "dti_factor": float(dti_factor),
        "age_factor": float(age_factor),
        "history_factor": float(history_factor),
        "credit_score_factor": float(credit_score_factor),
        "loan_type_factor": float(loan_type_factor),
        "interest_factor": float(interest_factor),
        "term_factor": float(term_factor),
        "collateral_ratio": float(collateral_ratio),
        "collateral_factor": float(collateral_factor),
        "employment_factor": float(employment_factor),
        "contributions": contributions,
        "raw_risk": float(round(raw_risk, 6)),
        "risk_score": float(round(risk_score, 4)),
        "label": label,
        "cic_score": int(cic_score),
        "cic_group": str(cic_group),
        "cic_rating": str(cic_rating),
        "clamped": bool(abs(raw_risk - risk_score) > 1e-9),
    }


def _detailed_explanations(
    *,
    payload: RiskRequest,
    dti: float,
    dti_factor: float,
    age_factor: float,
    history_factor: float,
    credit_score: int,
    credit_score_factor: float,
    loan_display_vi: str,
    loan_display_en: str,
    loan_type_factor: float,
    interest_rate: float,
    interest_factor: float,
    loan_term: float,
    term_factor: float,
    collateral_ratio: float,
    collateral_factor: float,
    emp_display_vi: str,
    emp_display_en: str,
    employment_factor: float,
    raw_risk: float,
    risk_score: float,
    label: str,
    cic_score: int,
    cic_group: str,
    cic_rating: str,
) -> Tuple[str, str]:
    """Bilingual long-form explanation of the heuristic scoring model."""

    w_dti, w_age, w_hist, w_cs = 0.28, 0.10, 0.12, 0.18
    w_lt, w_ir, w_term, w_col, w_emp = 0.08, 0.08, 0.06, 0.06, 0.04

    c_dti = w_dti * dti_factor
    c_age = w_age * age_factor
    c_hist = w_hist * history_factor
    c_cs = w_cs * credit_score_factor
    c_lt = w_lt * loan_type_factor
    c_ir = w_ir * interest_factor
    c_term = w_term * term_factor
    c_col = w_col * collateral_factor
    c_emp = w_emp * employment_factor

    coll_note_vi = (
        f"Tỷ lệ nợ/TSBD = {collateral_ratio:.4f}."
        if collateral_ratio > 0
        else "Không nhập giá trị TSBD → hệ số kênh TSBD = 0,8 (mặc định trung tính / thiếu thông tin)."
    )
    coll_note_en = (
        f"Debt-to-collateral ratio = {collateral_ratio:.4f}."
        if collateral_ratio > 0
        else "No collateral value provided → collateral channel uses default factor 0.8 (neutral / missing data)."
    )

    label_vi = {"low": "thấp", "medium": "trung bình", "high": "cao"}.get(label, label)
    cic_group_vi = {
        "very_good": "rất tốt",
        "good": "tốt",
        "average": "trung bình",
        "high_risk": "rủi ro cao",
    }.get(cic_group, cic_group)

    clamp_note_vi = ""
    clamp_note_en = ""
    if raw_risk != risk_score:
        clamp_note_vi = f"\n\nGiá trị tổng hợp trước khi cắt ngưỡng là {raw_risk:.4f}; sau khi giới hạn vào [0, 1] còn {risk_score:.4f}."
        clamp_note_en = (
            f"\n\nCombined value before clipping was {raw_risk:.4f}; after bounding to [0, 1] it is {risk_score:.4f}."
        )

    explanation_vi = f"""Mô hình heuristic (demo) gộp nhiều tín hiệu thành một chỉ số rủi ro R ∈ [0, 1]: R càng lớn thì rủi ro tín dụng càng cao.

1) Định nghĩa DTI (gánh nợ so với thu nhập): DTI = dư nợ / thu nhập tháng = {payload.debt:.2f} / {payload.income:.2f} = {dti:.4f}. Hệ số chuẩn hóa f_DTI = min(DTI, 2) / 2 ∈ [0, 1] = {dti_factor:.4f}. DTI cao → f_DTI lớn → kênh này đẩy R lên.

2) Tuổi: f_tuổi = 1 − giới hạn((tuổi−18)/(70−18)) vào [0,1] = {age_factor:.4f}. Tuổi càng nhỏ (trong khoảng 18–70) thì f_tuổi càng lớn → rủi ro tăng (theo giả định mô hình).

3) Lịch sử tín dụng (tháng): f_LS = 1 − min(tháng/120, 1) = {history_factor:.4f}. Thời gian lịch sử ngắn hơn → f_LS lớn hơn.

4) Điểm tín dụng nội bộ (thang ~300–900, mặc định 650 nếu không nhập): f_điểm = 1 − giới hạn((điểm−300)/600) = {credit_score_factor:.4f} với điểm = {credit_score}. Điểm thấp hơn → f_điểm lớn hơn.

5) Loại vay ({loan_display_vi}): hệ số kênh loại vay = {loan_type_factor:.2f} (ví dụ có đảm bảo thấp hơn tín chấp).

6) Lãi suất (%/năm, mặc định 12%): f_LS% = min(lãi suất/24, 1) = {interest_factor:.4f} (lãi suất hiện dùng {interest_rate:.2f}%).

7) Kỳ hạn (tháng, mặc định theo lịch sử nếu không nhập): f_kỳ = min(kỳ/240, 1) = {term_factor:.4f} (kỳ = {loan_term:.0f} tháng).

8) Tài sản bảo đảm: {coll_note_vi} Hệ số kênh TSBD = {collateral_factor:.4f}.

9) Việc làm ({emp_display_vi}): hệ số kênh việc làm = {employment_factor:.4f}.

Công thức tổng hợp (trọng số cố định):
R_thô = 0,28×f_DTI + 0,10×f_tuổi + 0,12×f_LS + 0,18×f_điểm + 0,08×f_loại_vay + 0,08×f_lãi + 0,06×f_kỳ + 0,06×f_TSBD + 0,04×f_việc_làm
     = {c_dti:.4f} + {c_age:.4f} + {c_hist:.4f} + {c_cs:.4f} + {c_lt:.4f} + {c_ir:.4f} + {c_term:.4f} + {c_col:.4f} + {c_emp:.4f}
     = {raw_risk:.4f}.

Sau đó R = min(max(R_thô, 0), 1) = {risk_score:.4f}.{clamp_note_vi}

Phân loại nhãn: R < 0,33 → rủi ro {label_vi} (low); 0,33 ≤ R < 0,66 → trung bình; R ≥ 0,66 → cao. Trường hợp này R = {risk_score:.4f} → nhãn «{label_vi}».

Tham chiếu CIC (quy đổi minh họa): điểm {cic_score}, nhóm {cic_group} ({cic_group_vi}), xếp hạng {cic_rating}."""

    explanation_en = f"""This demo heuristic combines several signals into a single credit risk score R ∈ [0, 1]. Higher R means higher risk.

1) Debt-to-income (DTI) = debt / monthly income = {payload.debt:.2f} / {payload.income:.2f} = {dti:.4f}. Normalized factor f_DTI = min(DTI, 2) / 2 ∈ [0, 1] = {dti_factor:.4f}. Higher DTI increases R.

2) Age: f_age = 1 − clip((age−18)/(70−18)) to [0,1] = {age_factor:.4f}. Younger ages (within 18–70) yield a larger f_age → higher modeled risk.

3) Credit history (months): f_hist = 1 − min(months/120, 1) = {history_factor:.4f}. Shorter history increases f_hist.

4) Internal credit score (~300–900, default 650): f_cs = 1 − clip((score−300)/600) = {credit_score_factor:.4f} with score = {credit_score}. Lower scores increase f_cs.

5) Loan type ({loan_display_en}): loan-type channel factor = {loan_type_factor:.2f} (e.g. secured lower than unsecured).

6) Interest rate (% p.a., default 12%): f_ir = min(rate/24, 1) = {interest_factor:.4f} (rate used: {interest_rate:.2f}%).

7) Term (months, defaults to history if omitted): f_term = min(term/240, 1) = {term_factor:.4f} (term = {loan_term:.0f} months).

8) Collateral: {coll_note_en} Collateral channel factor = {collateral_factor:.4f}.

9) Employment ({emp_display_en}): employment channel factor = {employment_factor:.4f}.

Weighted sum (fixed weights):
R_raw = 0.28·f_DTI + 0.10·f_age + 0.12·f_hist + 0.18·f_cs + 0.08·f_loan + 0.08·f_ir + 0.06·f_term + 0.06·f_col + 0.04·f_emp
      = {c_dti:.4f} + {c_age:.4f} + {c_hist:.4f} + {c_cs:.4f} + {c_lt:.4f} + {c_ir:.4f} + {c_term:.4f} + {c_col:.4f} + {c_emp:.4f}
      = {raw_risk:.4f}.

Then R = min(max(R_raw, 0), 1) = {risk_score:.4f}.{clamp_note_en}

Labels: R < 0.33 → low risk; 0.33 ≤ R < 0.66 → medium; R ≥ 0.66 → high. Here R = {risk_score:.4f} → «{label}».

CIC-style reference mapping: score {cic_score}, bucket {cic_group}, rating {cic_rating}."""

    return explanation_vi.strip(), explanation_en.strip()


@dataclass(frozen=True)
class HeuristicState:
    dti: float
    dti_factor: float
    age_factor: float
    history_factor: float
    credit_score: int
    credit_score_factor: float
    loan_type_original: str
    loan_type: str
    loan_type_factor: float
    interest_rate: float
    interest_factor: float
    loan_term: float
    term_factor: float
    collateral_ratio: float
    collateral_factor: float
    employment_original: str
    employment_factor: float
    raw_risk: float
    contributions: Dict[str, float]


def compute_heuristic_state(payload: RiskRequest) -> HeuristicState:
    """
    Single source for the demo heuristic: same factors/weights as simple_credit_risk_score.
    `contributions` maps engine keys to (weight × factor).
    """
    dti = (payload.debt / payload.income) if payload.income > 0 else 1.0
    dti_factor = min(max(dti, 0.0), 2.0) / 2.0
    age_factor = 1.0 - min(max((payload.age - 18) / (70 - 18), 0.0), 1.0)
    history_factor = 1.0 - min(max(payload.credit_history_months / 120.0, 0.0), 1.0)

    credit_score = int(payload.credit_score if payload.credit_score is not None else 650)
    credit_score_factor = 1.0 - min(max((credit_score - 300) / (900 - 300), 0.0), 1.0)

    loan_type_original = (payload.loan_type or "").strip()
    loan_type = loan_type_original.lower()
    if loan_type == "secured":
        loan_type_factor = 0.25
    elif loan_type == "business":
        loan_type_factor = 0.55
    elif loan_type == "unsecured":
        loan_type_factor = 0.7
    else:
        loan_type_factor = 0.5

    interest_rate = float(payload.interest_rate if payload.interest_rate is not None else 12.0)
    interest_factor = min(max(interest_rate / 24.0, 0.0), 1.0)

    loan_term = float(
        payload.loan_term_months if payload.loan_term_months is not None else payload.credit_history_months
    )
    term_factor = min(max(loan_term / 240.0, 0.0), 1.0)

    collateral_ratio = 0.0
    if payload.collateral_value is not None and payload.collateral_value > 0:
        collateral_ratio = payload.debt / payload.collateral_value if payload.collateral_value else 0.0
    collateral_factor = min(max(collateral_ratio, 0.0), 2.0) / 2.0 if collateral_ratio > 0 else 0.8

    employment_original = (payload.employment_status or "").strip()
    employment_status_raw = employment_original.lower()
    if employment_status_raw in {"permanent", "full_time", "employed"}:
        employment_factor = 0.25
    elif employment_status_raw in {"contract", "part_time", "self_employed"}:
        employment_factor = 0.55
    elif employment_status_raw:
        employment_factor = 0.65
    else:
        employment_factor = 0.5

    contributions: Dict[str, float] = {
        "dti": 0.28 * dti_factor,
        "age": 0.10 * age_factor,
        "history": 0.12 * history_factor,
        "credit_score": 0.18 * credit_score_factor,
        "loan_type": 0.08 * loan_type_factor,
        "interest": 0.08 * interest_factor,
        "term": 0.06 * term_factor,
        "collateral": 0.06 * collateral_factor,
        "employment": 0.04 * employment_factor,
    }
    raw_risk = sum(contributions.values())
    return HeuristicState(
        dti=dti,
        dti_factor=dti_factor,
        age_factor=age_factor,
        history_factor=history_factor,
        credit_score=credit_score,
        credit_score_factor=credit_score_factor,
        loan_type_original=loan_type_original,
        loan_type=loan_type,
        loan_type_factor=loan_type_factor,
        interest_rate=interest_rate,
        interest_factor=interest_factor,
        loan_term=loan_term,
        term_factor=term_factor,
        collateral_ratio=collateral_ratio,
        collateral_factor=collateral_factor,
        employment_original=employment_original,
        employment_factor=employment_factor,
        raw_risk=raw_risk,
        contributions=contributions,
    )


def simple_credit_risk_score(payload: RiskRequest) -> dict:
    """
    Baseline heuristic scoring to keep the backend functional.
    Replace with a trained model (sklearn, SageMaker endpoint, etc.) later.
    """
    h = compute_heuristic_state(payload)
    dti = h.dti
    dti_factor = h.dti_factor
    age_factor = h.age_factor
    history_factor = h.history_factor
    credit_score = h.credit_score
    credit_score_factor = h.credit_score_factor
    loan_type_original = h.loan_type_original
    loan_type = h.loan_type
    loan_type_factor = h.loan_type_factor
    interest_rate = h.interest_rate
    interest_factor = h.interest_factor
    loan_term = h.loan_term
    term_factor = h.term_factor
    collateral_ratio = h.collateral_ratio
    collateral_factor = h.collateral_factor
    employment_original = h.employment_original
    employment_factor = h.employment_factor
    raw_risk = h.raw_risk

    risk_score = min(max(raw_risk, 0.0), 1.0)
    if risk_score < 0.33:
        label = "low"
    elif risk_score < 0.66:
        label = "medium"
    else:
        label = "high"

    # Vietnam CIC reference scale (commonly used in practice): higher score is lower risk.
    cic_score = int(round(850 - (risk_score * 700)))  # map 0..1 -> 850..150
    if cic_score >= 700:
        cic_group = "very_good"
        cic_rating = "excellent"
    elif cic_score >= 570:
        cic_group = "good"
        cic_rating = "good"
    elif cic_score >= 431:
        cic_group = "average"
        cic_rating = "watchlist"
    else:
        cic_group = "high_risk"
        cic_rating = "loss"

    loan_display_vi = loan_type_original or "— (trung tính)"
    loan_display_en = loan_type_original or "— (neutral default)"
    emp_display_vi = employment_original or "— (mặc định trung tính)"
    emp_display_en = employment_original or "— (neutral default)"

    explanation_vi, explanation_en = _detailed_explanations(
        payload=payload,
        dti=dti,
        dti_factor=dti_factor,
        age_factor=age_factor,
        history_factor=history_factor,
        credit_score=credit_score,
        credit_score_factor=credit_score_factor,
        loan_display_vi=loan_display_vi,
        loan_display_en=loan_display_en,
        loan_type_factor=loan_type_factor,
        interest_rate=interest_rate,
        interest_factor=interest_factor,
        loan_term=float(loan_term),
        term_factor=term_factor,
        collateral_ratio=collateral_ratio,
        collateral_factor=collateral_factor,
        emp_display_vi=emp_display_vi,
        emp_display_en=emp_display_en,
        employment_factor=employment_factor,
        raw_risk=raw_risk,
        risk_score=risk_score,
        label=label,
        cic_score=cic_score,
        cic_group=cic_group,
        cic_rating=cic_rating,
    )

    explanation_detail = _build_explanation_detail(
        payload=payload,
        loan_type_original=loan_type_original,
        employment_original=employment_original,
        dti=dti,
        dti_factor=dti_factor,
        age_factor=age_factor,
        history_factor=history_factor,
        credit_score=credit_score,
        credit_score_factor=credit_score_factor,
        loan_type=loan_type,
        loan_type_factor=loan_type_factor,
        interest_rate=interest_rate,
        interest_factor=interest_factor,
        loan_term=float(loan_term),
        term_factor=term_factor,
        collateral_ratio=collateral_ratio,
        collateral_factor=collateral_factor,
        employment_factor=employment_factor,
        raw_risk=raw_risk,
        risk_score=risk_score,
        label=label,
        cic_score=cic_score,
        cic_group=cic_group,
        cic_rating=cic_rating,
    )

    return {
        "risk_score": float(round(risk_score, 4)),
        "risk_label": label,
        "cic_score": cic_score,
        "cic_group": cic_group,
        "cic_rating": cic_rating,
        "explanation": explanation_vi,
        "explanation_en": explanation_en,
        "explanation_detail": explanation_detail,
    }


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
