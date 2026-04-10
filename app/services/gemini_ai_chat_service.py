"""
Gemini AI chat service.

Priority of analysis context:
1. Uploaded file context attached by the user
2. Power BI context when backend Power BI config is available
3. Database analytics context
"""

from __future__ import annotations

import logging
import math
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ChatHistoryDB, ChatSessionDB
from app.services.analytics_data_service import get_analysis_context, get_analysis_context_powerbi
from app.services.bank_faq_service import BankFAQService
from app.services.chat_session_metadata import (
    build_message_with_attachments,
    build_session_metadata,
    extract_message_attachments,
    extract_initial_context,
    fetch_chat_session_names,
    fetch_pinned_session_ids,
    format_history_user_message_for_llm,
    strip_session_metadata,
    summary_title_from_message,
    update_chat_session_name,
)

logger = logging.getLogger(__name__)


@dataclass
class GeminiChatResponse:
    session_id: str
    message: str
    role: str
    timestamp: datetime
    sources: Optional[List[str]] = None


class GeminiResourceExhaustedError(RuntimeError):
    def __init__(self, message: str, retry_after_seconds: Optional[int] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class GeminiServiceUnavailableError(RuntimeError):
    """Google Gemini returned 503 UNAVAILABLE (overload / high demand)."""

    pass


def _looks_like_upstream_unavailable(exc: BaseException, msg: str) -> bool:
    m = (msg or "").lower()
    if "503" in (msg or "") and ("unavailable" in m or "high demand" in m or "try again later" in m):
        return True
    try:
        from google.genai.errors import ServerError

        return isinstance(exc, ServerError) and getattr(exc, "status_code", None) == 503
    except ImportError:
        return False


def _parse_retry_after_seconds(msg: str) -> Optional[int]:
    s = msg or ""

    match = re.search(r"retryDelay'\s*:\s*'(?P<sec>[0-9]+)s'", s)
    if match:
        return int(match.group("sec"))

    match = re.search(r"retry in\s+(?P<sec>[0-9]+(?:\.[0-9]+)?)s", s, flags=re.IGNORECASE)
    if match:
        return int(math.ceil(float(match.group("sec"))))

    return None


def _looks_like_resource_exhausted(msg: str) -> bool:
    s = (msg or "").lower()
    return ("resource_exhausted" in s or "quota exceeded" in s) and (
        "429" in s or "code': 429" in s or 'code": 429' in s
    )


def _powerbi_context_available() -> bool:
    return all(
        [
            (os.getenv("POWER_BI_TENANT_ID") or settings.power_bi_tenant_id).strip(),
            (os.getenv("POWER_BI_CLIENT_ID") or settings.power_bi_client_id).strip(),
            (os.getenv("POWER_BI_CLIENT_SECRET") or settings.power_bi_client_secret).strip(),
            (os.getenv("POWER_BI_WORKSPACE_ID") or settings.power_bi_workspace_id).strip(),
            (os.getenv("POWER_BI_DATASET_ID") or settings.power_bi_dataset_id).strip(),
        ]
    )


def _runtime_powerbi_context_available(customer_context: Optional[Dict]) -> bool:
    if not isinstance(customer_context, dict):
        return False
    cfg = customer_context.get("powerbi_runtime_config")
    if not isinstance(cfg, dict):
        return False
    # Tenant có thể lấy từ .env máy chủ khi user không lưu trong file — chỉ cần workspace + dataset.
    return bool(str(cfg.get("workspace_id") or "").strip() and str(cfg.get("dataset_id") or "").strip())


def _runtime_powerbi_user(customer_context: Optional[Dict]):
    if not _runtime_powerbi_context_available(customer_context):
        return None
    from types import SimpleNamespace

    cfg = customer_context.get("powerbi_runtime_config") or {}
    return SimpleNamespace(
        user_id="runtime-powerbi",
        power_bi_tenant_id=str(cfg.get("tenant_id") or "").strip(),
        power_bi_workspace_id=str(cfg.get("workspace_id") or "").strip(),
        power_bi_dataset_id=str(cfg.get("dataset_id") or "").strip(),
        power_bi_enabled=bool(cfg.get("enabled", True)),
        power_bi_table_names=[
            str(item).strip()
            for item in (cfg.get("table_names") or [])
            if str(item).strip()
        ],
    )


def _powerbi_binding_header(customer_context: Optional[Dict]) -> str:
    """Luôn đưa tên/ID kết nối thật vào prompt để model không bịa dataset mẫu (AdventureWorks, ...)."""
    if not isinstance(customer_context, dict):
        return ""
    cfg = customer_context.get("powerbi_runtime_config")
    if not isinstance(cfg, dict):
        return ""
    ws = str(cfg.get("workspace_id") or "").strip()
    ds = str(cfg.get("dataset_id") or "").strip()
    if not ws or not ds:
        return ""
    wn = str(cfg.get("workspace_name") or "").strip()
    dsn = str(cfg.get("dataset_name") or "").strip()
    tn = str(cfg.get("tenant_id") or "").strip()
    lines = [
        "--- THONG TIN KET NOI POWER BI (TAI KHOAN — BAT BUOC DUNG KHI HOI VE TEN/KET NOI) ---",
    ]
    if wn:
        lines.append(f"Ten workspace trong Power BI Service: {wn}")
    lines.append(f"Workspace ID (GUID): {ws}")
    if dsn:
        lines.append(f"Ten dataset trong Power BI Service: {dsn}")
    lines.append(f"Dataset ID (GUID): {ds}")
    if tn:
        lines.append(f"Tenant ID (Azure AD): {tn}")
    lines.append(
        "Khi tra loi ve workspace/dataset da ket noi, chi duoc dung Ten/ID o tren. "
        "Tuyet doi khong tu neu ten bo mau (AdventureWorks, Contoso, Fabrikam, ...)."
    )
    return "\n".join(lines).strip() + "\n\n"


def _resolve_context_source(customer_context: Optional[Dict] = None) -> str:
    if _runtime_powerbi_context_available(customer_context):
        return "powerbi"
    configured = (os.getenv("AI_CHAT_CONTEXT_SOURCE") or settings.ai_chat_context_source or "").strip().lower()
    if configured == "powerbi":
        return "powerbi" if _powerbi_context_available() else "db"
    if configured == "db":
        return "db"
    return "powerbi" if _powerbi_context_available() else "db"


def _sanitize_system_context(raw_context: str, source: str) -> str:
    text = (raw_context or "").strip()
    if not text:
        return ""

    lowered = text.lower()
    if source == "powerbi":
        bad_markers = (
            "power bi direct context error",
            "power bi chưa được cấu hình",
            "failed to obtain access token",
            "power bi global config missing",
            "check tenant/app credentials",
        )
        if any(marker in lowered for marker in bad_markers):
            return ""
    return text


_CTX_ACK_MODEL_VI = (
    "Đã tiếp nhận. Tôi chỉ tham chiếu nội dung này—không nhắc lại nguyên văn các đoạn dài, "
    "danh sách hay bảng số trừ khi bạn yêu cầu trích dẫn hoặc có thay đổi mới."
)


def _dedupe_response_text(text: str) -> str:
    """Collapse consecutive duplicate lines / paragraphs (common LLM glitch)."""
    s = (text or "").strip()
    if not s:
        return ""

    lines = s.split("\n")
    out_lines: List[str] = []
    prev_line_norm: Optional[str] = None
    for line in lines:
        cur = line.rstrip()
        if cur.strip() and prev_line_norm is not None and cur == prev_line_norm:
            continue
        out_lines.append(line)
        prev_line_norm = cur if cur.strip() else prev_line_norm

    s2 = "\n".join(out_lines).strip()
    paras_raw = s2.split("\n\n")
    out_paras: List[str] = []
    prev_para_key: Optional[str] = None
    for raw in paras_raw:
        p = raw.strip()
        if not p:
            continue
        key = " ".join(p.split())
        if len(key) >= 80 and key == prev_para_key:
            continue
        out_paras.append(p)
        prev_para_key = key if len(key) >= 80 else prev_para_key
    return "\n\n".join(out_paras)


def _extract_uploaded_file_context(customer_context: Optional[Dict]) -> str:
    if not isinstance(customer_context, dict):
        return ""

    raw_files = customer_context.get("uploaded_files") or customer_context.get("uploadedFiles") or []
    if not isinstance(raw_files, list):
        return ""

    chunks: List[str] = []
    for idx, item in enumerate(raw_files, start=1):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip().lower()
        if status == "error":
            continue
        name = str(item.get("name") or item.get("file_name") or item.get("fileName") or f"File {idx}").strip()
        context_text = str(item.get("context_text") or item.get("contextText") or "").strip()
        if not context_text:
            continue
        chunks.append(f"[FILE {idx}: {name}]\n{context_text}")

    return "\n\n".join(chunks).strip()


def _extract_additional_customer_context(customer_context: Optional[Dict]) -> str:
    if not isinstance(customer_context, dict):
        return ""
    remaining = {
        key: value
        for key, value in customer_context.items()
        if key not in {"uploaded_files", "uploadedFiles", "context_mode", "contextMode", "powerbi_runtime_config"}
    }
    return str(remaining).strip() if remaining else ""


def _extract_uploaded_files_metadata(customer_context: Optional[Dict]) -> List[Dict]:
    if not isinstance(customer_context, dict):
        return []
    raw_files = customer_context.get("uploaded_files") or customer_context.get("uploadedFiles") or []
    if not isinstance(raw_files, list):
        return []
    out: List[Dict] = []
    for idx, item in enumerate(raw_files, start=1):
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "id": item.get("id") or f"file-{idx}",
                "name": item.get("name") or item.get("file_name") or item.get("fileName") or f"File {idx}",
                "size": item.get("size") or 0,
                "extension": item.get("extension") or "",
                "status": item.get("status") or "ready",
                "job_id": item.get("job_id") or item.get("jobId"),
                "row_count": item.get("row_count") or item.get("rowCount"),
                "column_count": item.get("column_count") or item.get("columnCount"),
                "columns": item.get("columns"),
                "preview_rows": item.get("preview_rows") or item.get("previewRows"),
                "context_text": item.get("context_text") or item.get("contextText"),
                "error": item.get("error"),
            }
        )
    return out


class GeminiAIChatService:
    MODE_PROMPTS = {
        "fast": (
            "Che do Nhanh:\n"
            "- Muc tieu la phan hoi nhanh nhat co the nhung van dung trong tam cau hoi.\n"
            "- Uu tien cau tra loi ngan, ro, de quet nhanh.\n"
            "- Dua ket luan chinh len dau, sau do moi neu 2-3 y bo tro quan trong.\n"
            "- Han che dao qua sau vao cac huong phan tich phu neu nguoi dung khong yeu cau.\n"
            "- Neu co the tra loi truc tiep bang ket luan, thi tra loi truc tiep truoc.\n"
            "- Neu du lieu chua du, chi ra ngay phan thieu va de xuat buoc tiep theo ngan gon."
        ),
        "thinking": (
            "Che do Tu duy:\n"
            "- Muc tieu la can bang giua chat luong phan tich va do dai cau tra loi.\n"
            "- Truoc khi tra loi, hay xac dinh nguoi dung dang hoi ve tong quan, liet ke, giai thich, so sanh, hay khuyen nghi.\n"
            "- Neu bai toan phuc tap, hay chia nho van de thanh tung phan hop ly va lap luan theo trinh tu.\n"
            "- Neu co nhieu cach dien giai, hay chon cach hop ly nhat dua tren du lieu hien co va noi ro gia dinh neu can.\n"
            "- Uu tien chi ra ly do, dau hieu, mau hinh va moi lien he giua cac chi so.\n"
            "- Ket thuc bang tong ket ngan hoac 1-3 khuyen nghi neu phu hop."
        ),
        "pro": (
            "Che do Pro:\n"
            "- Muc tieu la dua ra cau tra loi co chat luong phan tich cao nhat trong pham vi du lieu duoc cung cap.\n"
            "- Hay suy nghi nhu mot chuyen gia phan tich rui ro/du lieu cap cao: xac dinh van de, nguyen nhan, tac dong, muc do uu tien va hanh dong de xuat.\n"
            "- Khi danh gia rui ro, uu tien cac goc nhin: xac suat xay ra, muc do anh huong, dau hieu canh bao, nhom khach hang/phan khuc bi anh huong va tinh cap bach.\n"
            "- Neu phu hop, co the trinh bay theo cau truc: Nhan dinh chinh, Bang chung tu du lieu, Phan tich nguyen nhan, Tac dong, Kien nghi hanh dong.\n"
            "- Chu y tranh khang dinh qua muc khi du lieu chua du; thay vao do, neu ro muc do tin cay va thong tin can bo sung.\n"
            "- Uu tien tinh thuc chien: khuyen nghi phai cu the, co the hanh dong duoc, va gan voi du lieu dang co."
        ),
    }
    SYSTEM_PROMPT = (
        "Ban la tro ly AI chuyen phan tich rui ro tin dung, du lieu tai chinh va du lieu nghiep vu. "
        "Nhiem vu cua ban la doc dung ngu canh duoc cung cap, hieu dung y nguoi dung, va dua ra cau tra loi phu hop nhat voi muc tieu thuc te cua ho.\n\n"
        "Nguyen tac uu tien du lieu:\n"
        "1. Neu nguoi dung gui file, ban phai uu tien tuyet doi noi dung trong file do.\n"
        "2. Neu khong co file, ban chi duoc dua tren du lieu he thong duoc chen trong prompt.\n"
        "3. Khong duoc gia vo da xem them du lieu ben ngoai prompt.\n"
        "4. Khong duoc bo sung so lieu, ten cot, ten bang, chi so hay ket luan ma prompt khong ho tro.\n"
        "5. Neu co khoi 'THONG TIN KET NOI POWER BI', khi hoi ve ten workspace/dataset phai tra loi dung theo khoi do — khong duoc dung ten dataset mau cong nghe.\n\n"
        "Nguyen tac hieu yeu cau:\n"
        "- Truoc khi tra loi, ngam xac dinh nguoi dung dang muon: tong quan, liet ke, giai thich, so sanh, xep hang, tim bat thuong, danh gia rui ro, hay de xuat hanh dong.\n"
        "- Chon hinh thuc tra loi phu hop voi cau hoi thay vi dung mot khuon mau co dinh.\n"
        "- Neu nguoi dung hoi rat cu the, hay tra loi truc dien vao cau hoi.\n"
        "- Neu nguoi dung hoi mo, co the chu dong cau truc cau tra loi de giup ho ra quyet dinh nhanh hon.\n\n"
        "Nguyen tac phan tich:\n"
        "- Tim cac dau hieu quan trong, xu huong, nhom noi bat, gia tri cao/thap bat thuong, va moi lien he giua cac truong thong tin neu du lieu cho phep.\n"
        "- Khi nhan xet rui ro, can neu ro vi sao mot doi tuong/nhom duoc xem la rui ro hon doi tuong/nhom khac.\n"
        "- Khi liet ke, uu tien sap xep theo muc do lien quan hoac muc do rui ro neu co co so.\n"
        "- Khi tong hop, dua ket luan chinh len truoc, sau do bo tro bang cac diem chung minh gon gang.\n"
        "- Khi co nhieu cach dien giai hop ly, hay chon cach hop ly nhat va neu gia dinh neu can.\n\n"
        "Khung tham chieu phan loai no theo quy dinh SBV khi bai toan lien quan den no qua han/no xau:\n"
        "- Co the su dung lam khung phan tich nghiep vu mac dinh khi nguoi dung hoi ve nhom no, no xau, muc do qua han, chat luong tin dung hoac canh bao rui ro lien quan.\n"
        "- Nhom 1 (No du tieu chuan): trong han hoac qua han duoi 10 ngay.\n"
        "- Nhom 2 (No can chu y): qua han tu 10 ngay den duoi 90 ngay, hoac mot so truong hop co cau lai no theo quy dinh.\n"
        "- Nhom 3 (No duoi tieu chuan, bat dau la no xau): qua han tu 91 den 180 ngay.\n"
        "- Nhom 4 (No nghi ngo): qua han tu 181 den 360 ngay.\n"
        "- Nhom 5 (No co kha nang mat von): qua han tren 360 ngay hoac co dau hieu mat kha nang thu hoi.\n"
        "- Khi du lieu co truong so ngay qua han, hay uu tien anh xa vao 5 nhom no nay truoc khi dua ra nhan dinh rui ro.\n"
        "- Khi du lieu khong du de phan nhom chinh xac, hay noi ro rang du lieu con thieu va tranh gan nhom no mot cach vo can cu.\n"
        "- Neu co su khac biet giua quy tac nghiep vu do nguoi dung cung cap va du lieu thuc te, hay neu ro gia dinh dang duoc ap dung trong phan tich.\n\n"
        "Nguyen tac trinh bay:\n"
        "- Tra loi bang tieng Viet tu nhien, ro rang, de doc.\n"
        "- Duoc phep dung tieu de ngan, danh sach, bang tom tat ngat doan hop ly khi giup de hieu hon.\n"
        "- Co the dung giong van chuyen nghiep nhung khong quan lieu, khong lan man.\n"
        "- Khong lap lai cac cau mo dau may moc nhu 'Chao ban' o moi lan tra loi, tru khi thuc su can thiet cho ngu canh.\n"
        "- Tranh lap lai nguyen van cung mot doan danh sach, cung mot bang so lieu, hoac cung mot khoi 'du lieu thieu' "
        "o nhieu lan tra loi lien tiep neu noi dung khong doi; chi nhac lai khi co thong tin moi hoac nguoi dung yeu cau tom tat/trich dan.\n"
        "- Tranh viet qua dai neu cau hoi don gian; mo rong phan tich khi cau hoi phuc tap hoac nguoi dung muon dao sau.\n\n"
        "Mau tra loi cho bai toan chuan hoa/import danh sach khach hang hoac ho so vay:\n"
        "- Khi nguoi dung yeu cau trich xuat, chuan hoa, lap bang, tao CSV, hoac chuan bi du lieu de import vao danh sach khach hang, hay tra loi theo dung 3 phan theo thu tu sau.\n"
        "- Phan 1: mot bang markdown chuan hoa du lieu de nguoi dung doc va ra soat nhanh.\n"
        "- Phan 2: mot phan 'Phan tich ngan' chi 3-6 dong, tap trung vao ho so rui ro cao, ho so thieu du lieu, va ho so can manager/admin xem ky.\n"
        "- Phan 3: mot khoi ma ```csv ... ``` chua du lieu CSV chuan hoa de nguoi dung co the copy va luu thanh file .csv.\n"
        "- Trong CSV, ten cot phai on dinh, ro nghia, khong chen giai thich vao cung mot o du lieu.\n"
        "- Neu mot truong khong co du lieu chac chan, de trong hoac dua vao cot canh bao/missing_fields, khong tu bo sung gia dinh nhu mot su that.\n"
        "- Neu so luong ban ghi lon, uu tien dua bang tom tat cho nhung cot quan trong nhat nhung khoi CSV van phai du thong tin can import neu du lieu cho phep.\n\n"
        "Xu ly truong hop thieu du lieu:\n"
        "- Neu du lieu chua du de ket luan chac chan, hay noi ro phan nao chua du.\n"
        "- Neu co the, dua ra ket luan tam thoi kem muc do than trong.\n"
        "- De xuat 1-3 thong tin bo sung hoac buoc tiep theo cu the, thay vi tra loi chung chung.\n\n"
        "Muc tieu cuoi cung:\n"
        "- Giup nguoi dung hieu du lieu nhanh hon.\n"
        "- Lam ro doi tuong, van de, rui ro, nguyen nhan va hanh dong uu tien.\n"
        "- Dua ra cau tra loi vua dung, vua huu ich, vua co tinh hanh dong."
    )

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or settings.gemini_api_key or None
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set GEMINI_API_KEY (or gemini_api_key) in .env")

        raw_model = (model or os.getenv("GEMINI_MODEL") or settings.gemini_model or "gemini-2.0-flash").strip()
        if raw_model.startswith("models/"):
            raw_model = raw_model[len("models/") :]
        self.model = raw_model
        self.mode_tier = self._infer_mode_tier(raw_model)

        try:
            from google import genai  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"google-genai is not installed or import failed: {exc}")

        self._genai = genai
        self.client = genai.Client(api_key=self.api_key)
        self.faq_service = BankFAQService()

    def _infer_mode_tier(self, model_name: str) -> str:
        normalized = (model_name or "").strip().lower()
        if "lite" in normalized:
            return "fast"
        if "pro" in normalized:
            return "pro"
        return "thinking"

    def _build_system_prompt(self) -> str:
        mode_prompt = self.MODE_PROMPTS.get(self.mode_tier or "", "")
        if not mode_prompt:
            return self.SYSTEM_PROMPT
        return f"{self.SYSTEM_PROMPT} {mode_prompt}"

    def start_chat_session(
        self,
        session: Session,
        user_id: int,
        session_name: str,
        initial_context: Optional[str] = None,
    ) -> Tuple[str, str]:
        try:
            now = datetime.utcnow()
            session_id = str(uuid.uuid4())
            chat_session = ChatSessionDB(
                session_id=session_id,
                user_id=user_id,
                created_at=now,
                last_interaction=now,
            )
            session.add(chat_session)

            session.add(
                ChatHistoryDB(
                    session_id=session_id,
                    user_id=user_id,
                    message=build_session_metadata(session_name=session_name, initial_context=initial_context),
                    bot_response=None,
                    created_at=now,
                )
            )
            session.flush()
            update_chat_session_name(session, session_id, session_name)
            session.commit()
            return session_id, ""
        except Exception as exc:
            session.rollback()
            raise Exception(f"Error starting chat session (gemini): {exc}")

    def send_message(
        self,
        session: Session,
        session_id: str,
        user_id: int,
        message: str,
        customer_context: Optional[Dict] = None,
    ) -> GeminiChatResponse:
        try:
            sid = _normalize_session_id(session_id)
            chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            history_rows = (
                session.query(ChatHistoryDB)
                .filter(ChatHistoryDB.session_id == sid)
                .order_by(ChatHistoryDB.created_at)
                .limit(20)
                .all()
            )

            session_initial_context = ""
            for row in history_rows:
                if not session_initial_context:
                    session_initial_context = extract_initial_context(row.message) or ""
                if session_initial_context:
                    break

            contents: List[dict] = [{"role": "user", "parts": [{"text": f"[SYSTEM]\n{self._build_system_prompt()}"}]}]

            # Long session/bootstrap context: inject once as its own turn (not re-appended on every user message).
            if session_initial_context.strip():
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    "[HO SO/NGU CANH KHOI TAO PHIEN — CHI THAM CHIEU, KHONG NHAC LAI NGUYEN VAN]\n"
                                    + session_initial_context.strip()
                                )
                            }
                        ],
                    }
                )
                contents.append({"role": "model", "parts": [{"text": _CTX_ACK_MODEL_VI}]})

            uploaded_now = _extract_uploaded_file_context(customer_context)
            # When uploads or session bootstrap text exist, skip loading portfolio/Power BI blob (same as before).
            skip_data_context = bool(uploaded_now.strip() or session_initial_context.strip())

            data_context = ""
            context_source = ""
            now = datetime.utcnow()
            cache_ttl_hours = 1
            runtime_powerbi_enabled = _runtime_powerbi_context_available(customer_context)

            if not skip_data_context:
                if runtime_powerbi_enabled:
                    try:
                        context_source = "powerbi"
                        data_context = _sanitize_system_context(
                            get_analysis_context_powerbi(runtime_user=_runtime_powerbi_user(customer_context)),
                            context_source,
                        )
                    except Exception as exc:
                        logger.warning("Could not load runtime Power BI context for AI: %s", exc)
                    if data_context.strip():
                        chat_session.data_context_cached = data_context
                        chat_session.data_context_cached_at = now
                elif (
                    chat_session.data_context_cached
                    and chat_session.data_context_cached_at
                    and (now - chat_session.data_context_cached_at).total_seconds() < cache_ttl_hours * 3600
                ):
                    data_context = chat_session.data_context_cached
                else:
                    try:
                        context_source = _resolve_context_source(customer_context)
                        if context_source == "powerbi":
                            data_context = _sanitize_system_context(
                                get_analysis_context_powerbi(runtime_user=_runtime_powerbi_user(customer_context)),
                                context_source,
                            )
                        else:
                            data_context = _sanitize_system_context(get_analysis_context(session), "db")
                    except Exception as exc:
                        logger.warning("Could not load analytics context for AI: %s", exc)

                    if data_context.strip():
                        chat_session.data_context_cached = data_context
                        chat_session.data_context_cached_at = now

            pb_bind = _powerbi_binding_header(customer_context)
            if pb_bind.strip() and not skip_data_context:
                data_context_for_llm = (
                    pb_bind + ("\n" + data_context.strip() if data_context.strip() else "")
                ).strip()
            else:
                data_context_for_llm = data_context.strip()

            # Analytics / Power BI snapshot: separate turn so we do not paste the same block into every question.
            if data_context_for_llm:
                src = context_source.upper() if context_source else "HE THONG"
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    f"[DU LIEU TONG HOP ({src}) — CHI THAM CHIEU, KHONG NHAC LAI TOAN BO BANG]\n"
                                    + data_context_for_llm
                                )
                            }
                        ],
                    }
                )
                contents.append({"role": "model", "parts": [{"text": _CTX_ACK_MODEL_VI}]})

            for row in history_rows:
                history_user_text = format_history_user_message_for_llm(row.message)
                if history_user_text:
                    contents.append({"role": "user", "parts": [{"text": history_user_text}]})
                if row.bot_response:
                    contents.append({"role": "model", "parts": [{"text": row.bot_response}]})

            user_text = message
            if uploaded_now.strip():
                user_text = (
                    "[FILE DINH KEM TRONG YEU CAU NAY]\n"
                    + uploaded_now.strip()
                    + "\n\n[CAU HOI]\n"
                    + message
                )

            if not skip_data_context:
                faq_context = ""
                try:
                    faq_context = self.faq_service.build_context(query=message)
                except Exception as exc:
                    logger.warning("Could not load FAQ context for AI: %s", exc)
                if faq_context.strip():
                    user_text = "[NGU CANH FAQ NGAN HANG]\n" + faq_context.strip() + "\n\n" + user_text

            additional_customer_context = _extract_additional_customer_context(customer_context)
            if additional_customer_context:
                user_text = "[THONG TIN KHACH HANG BO SUNG]\n" + additional_customer_context + "\n\n" + user_text

            contents.append({"role": "user", "parts": [{"text": user_text}]})

            try:
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                )
            except Exception as exc:
                msg = str(exc)
                if _looks_like_resource_exhausted(msg):
                    retry_after = _parse_retry_after_seconds(msg)
                    detail = (msg or "").strip()
                    if len(detail) > 800:
                        detail = detail[:800] + "..."
                    raise GeminiResourceExhaustedError(
                        message=(
                            "Gemini quota/rate limit exceeded (429 RESOURCE_EXHAUSTED)."
                            + (f" Retry after {retry_after}s." if retry_after else "")
                            + (f" Detail: {detail}" if detail else "")
                        ),
                        retry_after_seconds=retry_after,
                    ) from exc
                if _looks_like_upstream_unavailable(exc, msg):
                    logger.warning("Gemini generate_content unavailable (503): %s", msg[:500])
                    raise GeminiServiceUnavailableError(
                        "Gemini model temporarily unavailable (503 UNAVAILABLE). Please retry later."
                    ) from exc
                raise

            ai_text = _dedupe_response_text(_extract_text(resp))
            if not ai_text:
                ai_text = "Minh chua nhan duoc noi dung tra loi tu mo hinh. Ban thu lai giup minh nhe."

            prior_rows = (
                session.query(ChatHistoryDB)
                .filter(ChatHistoryDB.session_id == sid)
                .order_by(ChatHistoryDB.created_at.asc())
                .all()
            )
            prior_user_messages = sum(1 for row in prior_rows if format_history_user_message_for_llm(row.message))

            now_final = datetime.utcnow()
            session.add(
                ChatHistoryDB(
                    session_id=sid,
                    user_id=user_id,
                    message=build_message_with_attachments(message, _extract_uploaded_files_metadata(customer_context)),
                    bot_response=ai_text,
                    created_at=now_final,
                )
            )
            chat_session.last_interaction = now_final
            if prior_user_messages == 0:
                auto_title = summary_title_from_message(message)
                if auto_title:
                    update_chat_session_name(session, sid, auto_title)
            session.commit()

            return GeminiChatResponse(
                session_id=sid,
                message=ai_text,
                role="assistant",
                timestamp=now_final,
                sources=None,
            )
        except ValueError:
            session.rollback()
            raise
        except GeminiResourceExhaustedError:
            session.rollback()
            raise
        except GeminiServiceUnavailableError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            raise Exception(f"Error sending message (gemini): {exc}")

    def get_chat_history(self, session: Session, session_id: str, limit: int = 50) -> List[Dict]:
        sid = _normalize_session_id(session_id)
        rows = (
            session.query(ChatHistoryDB)
            .filter(ChatHistoryDB.session_id == sid)
            .order_by(ChatHistoryDB.created_at)
            .limit(limit)
            .all()
        )
        out: List[Dict] = []
        for row in rows:
            ts = row.created_at.isoformat()
            clean_message = (strip_session_metadata(row.message) or "").strip()
            attachments = extract_message_attachments(row.message)
            if clean_message or attachments:
                out.append(
                    {
                        "role": "user",
                        "content": clean_message,
                        "timestamp": ts,
                        "attachments": attachments,
                    }
                )
            if row.bot_response:
                out.append({"role": "assistant", "content": row.bot_response, "timestamp": ts})
        return out

    def close_chat_session(self, session: Session, session_id: str) -> Dict:
        sid = _normalize_session_id(session_id)
        chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid).first()
        if not chat_session:
            raise ValueError(f"Chat session {session_id} not found")
        rows = session.query(ChatHistoryDB).filter(ChatHistoryDB.session_id == sid).all()
        user_messages = sum(1 for row in rows if row.message)
        assistant_messages = sum(1 for row in rows if row.bot_response)
        now = datetime.utcnow()
        chat_session.last_interaction = now
        session.commit()
        session_name = fetch_chat_session_names(session, [sid]).get(sid)
        return {
            "session_id": sid,
            "session_name": session_name or f"Session {sid[:8]}",
            "duration": None,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "total_messages": len(rows),
            "closed_at": now.isoformat(),
        }

    def get_user_sessions(self, session: Session, user_id: int) -> List[Dict]:
        sessions = (
            session.query(ChatSessionDB)
            .filter(ChatSessionDB.user_id == user_id)
            .order_by(ChatSessionDB.created_at.desc())
            .all()
        )
        pinned_ids = fetch_pinned_session_ids(session, user_id, [str(item.session_id) for item in sessions])
        sessions = sorted(sessions, key=lambda item: (0 if str(item.session_id) in pinned_ids else 1,))
        session_names = fetch_chat_session_names(session, [str(item.session_id) for item in sessions])
        return [
            {
                "session_id": str(item.session_id),
                "session_name": session_names.get(str(item.session_id)) or f"Session {str(item.session_id)[:8]}",
                "is_active": True,
                "is_pinned": str(item.session_id) in pinned_ids,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "closed_at": item.last_interaction.isoformat() if item.last_interaction else None,
            }
            for item in sessions
        ]

    def generate_analysis_report(self, session: Session, session_id: str) -> str:
        return "[GEMINI MODE] Report is not implemented separately yet."


def _extract_text(resp) -> str:
    text = getattr(resp, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(resp, "candidates", None)
    if candidates:
        try:
            candidate = candidates[0]
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None)
            if parts:
                texts = []
                for part in parts:
                    part_text = getattr(part, "text", None)
                    if isinstance(part_text, str) and part_text.strip():
                        t = part_text.strip()
                        if texts and texts[-1] == t:
                            continue
                        texts.append(t)
                if texts:
                    return "\n".join(texts)
        except Exception:
            pass
    return ""


def _normalize_session_id(session_id: str) -> str:
    value = (session_id or "").strip()
    if not value:
        raise ValueError("session_id is required")
    return value
