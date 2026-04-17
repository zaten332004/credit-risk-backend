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
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ChatHistoryDB, ChatSessionDB
from app.services.analytics_data_service import (
    get_analysis_context,
    get_analysis_context_powerbi,
    get_customer_focus_context,
    get_customers_focus_context,
)
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


class GeminiServiceOverloadedError(RuntimeError):
    """Gemini returned 503 / UNAVAILABLE (capacity spikes). Prefer HTTP 503 + Retry-After upstream."""

    def __init__(self, message: str, retry_after_seconds: Optional[int] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


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


def _looks_like_service_unavailable(msg: str) -> bool:
    """503 UNAVAILABLE from Google GenAI (high demand / temporary outage)."""
    s = (msg or "").lower()
    if "503" in msg and ("unavailable" in s or "servererror" in s):
        return True
    if "high demand" in s and ("model" in s or "gemini" in s or "try again later" in s):
        return True
    if "'status': 'unavailable'" in s or '"status": "unavailable"' in s:
        return True
    return False


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


def _parse_ai_data_source(customer_context: Optional[Dict]) -> Optional[str]:
    """
    Nguồn dữ liệu do client chọn (POST /ai-chat/send customer_context).
    None = không gửi key → giữ hành vi cũ (runtime Power BI / env / DB).
    """
    if not isinstance(customer_context, dict):
        return None
    if "ai_data_source" not in customer_context and "aiDataSource" not in customer_context:
        return None
    raw = customer_context.get("ai_data_source") or customer_context.get("aiDataSource") or ""
    s = str(raw).strip().lower()
    if s in ("portfolio", "portfolio_db", "db", "danh_muc", "system"):
        return "portfolio"
    if s in ("customer", "customer_db", "customers", "khach_hang"):
        return "customer"
    if s in ("upload", "file", "files"):
        return "upload"
    if s in ("powerbi", "power_bi", "pbi"):
        return "powerbi"
    if s in ("alerts", "alert", "canh_bao", "danh_muc_alerts", "alert_list"):
        return "alerts"
    if s in ("none", "off", "general", "no", "no_context", "chat_only", "khong", "khong_nguon"):
        return "none"
    return "portfolio"


def _customer_id_from_context(customer_context: Optional[Dict]) -> Optional[int]:
    if not isinstance(customer_context, dict):
        return None
    for key in ("customer_id", "customerId", "focus_customer_id", "focusCustomerId"):
        v = customer_context.get(key)
        if v is None:
            continue
        try:
            n = int(v)
            if n > 0:
                return n
        except (TypeError, ValueError):
            continue
    return None


def _customer_ids_from_context(customer_context: Optional[Dict]) -> List[int]:
    """Ưu tiên mảng customer_ids; không có thì dùng một customer_id."""
    if not isinstance(customer_context, dict):
        return []
    raw = customer_context.get("customer_ids") or customer_context.get("customerIds")
    out: List[int] = []
    if isinstance(raw, list):
        for item in raw:
            try:
                n = int(item)
                if n > 0:
                    out.append(n)
            except (TypeError, ValueError):
                continue
    seen: set[int] = set()
    uniq: List[int] = []
    for n in out:
        if n in seen:
            continue
        seen.add(n)
        uniq.append(n)
    if uniq:
        return uniq
    single = _customer_id_from_context(customer_context)
    return [single] if single else []


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
    "Received — I will only reference this context; I will not dump long verbatim tables/lists "
    "unless you ask for quotes or something materially changed. "
    "Đã tiếp nhận — tôi chỉ tham chiếu nội dung này, không nhắc lại nguyên văn các đoạn dài, "
    "danh sách hay bảng số trừ khi bạn yêu cầu trích dẫn hoặc có thay đổi mới."
)


def _detect_user_question_language(text: str) -> Optional[str]:
    """
    Infer language of the user's question for reply-language hints.
    Returns 'vi' if Vietnamese script (tone marks / đ) is present, or common Vietnamese
    phrases without diacritics; else 'en' if there is Latin text; else None.
    """
    s = (text or "").strip()
    if not s:
        return None
    if re.search(
        r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơớờởỡợùúủũụưừứửữựỳýỷỹỵđ"
        r"ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]",
        s,
    ):
        return "vi"
    low = s.lower()
    # Typing without diacritics — still treat as Vietnamese when clearly so.
    _vi_ascii_markers = (
        "ngan hang",
        "tin dung",
        "khoan vay",
        "khach hang",
        "danh muc",
        "du lieu",
        "bao cao",
        "rui ro",
        "canh bao",
        "no xau",
        "qua han",
        "hop dong",
        "phan tich",
        "tong hop",
        "hay cho",
        "hay giup",
        "gia tri",
        "the nao",
        "vi sao",
        "cua toi",
        "cho toi",
        "giup toi",
        "lam on",
        "xin ",
    )
    if any(m in low for m in _vi_ascii_markers):
        return "vi"
    if re.search(r"[A-Za-z]", s):
        return "en"
    return None


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
        if key
        not in {
            "uploaded_files",
            "uploadedFiles",
            "context_mode",
            "contextMode",
            "powerbi_runtime_config",
            "ai_data_source",
            "aiDataSource",
            "customer_id",
            "customerId",
            "customer_ids",
            "customerIds",
            "focus_customer_id",
            "focusCustomerId",
        }
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
            "Che do Nhanh (mo hinh nhe):\n"
            "- Uu tien tra loi DUNG va DU Y theo cau hoi; mac dinh tra loi NGAN-GON de ra quyet dinh nhanh.\n"
            "- Dat ket luan / so lieu chinh o dau (hoac ngay sau 1 cau nen) khi cau hoi dinh luong hoac can quyet dinh nhanh.\n"
            "- Chi trich xuat phan ngu canh lien quan truc tiep; khong tom tat lai toan bo file/bang neu nguoi dung khong yeu cau.\n"
            "- Gom y thanh 2-5 diem co can cu; tranh lap lai cung mot y o nhieu cau.\n"
            "- Cau hoi mo ho: neu van tra loi duoc thi tra loi day du voi gia dinh ro; chi hoi them DUNG MOT cau khi that su thieu thong tin bat buoc.\n"
            "- So/xep hang/rui ro: gan voi cot hoac doan trong ngu canh; tranh lap lai cung mot cau mo dau.\n"
            "- Do dai mac dinh: cau hoi don gian 4-8 dong; cau hoi phuc tap 8-14 dong, chi dai hon khi user yeu cau."
        ),
        "thinking": (
            "Che do Tu duy (mo hinh can bang):\n"
            "- Tra loi du y can thiet (ly luan + ket luan + gioi han neu co) nhung uu tien de ngan toc do cao.\n"
            "- Tu kiem nhanh: neu hai phan ngu canh mau thuan, neu ro truoc khi ket luan; tranh hop nhat vo ly.\n"
            "- Tu duy noi bo: hieu nguoi dung muon gi va chi rut ra phan ngu canh can thiet; khong liet ke tung buoc neu khong tang gia tri.\n"
            "- Neu nhieu cach hieu: chon cach sat ngu canh nhat; neu van mo thi hoi mot cau truoc khi mo rong.\n"
            "- Phan tich linh hoat: sap xep, so sanh, hoac danh gia rui ro tuy cau hoi; moi y co can cu trong ngu canh.\n"
            "- Ket luan chinh co the dat dau hoac sau phan giai thich tuy do dai va do phuc tap — uu tien de doc, khong ep khuon.\n"
            "- Khong suy dien vuot qua du lieu; neu thieu X thi noi ro thay vi doan.\n"
            "- Neu hop le: ket thuc bang 1-3 goi y hanh dong nghiep vu; khong can them muc neu user chi can cau tra loi truc tiep."
        ),
        "pro": (
            "Che do Pro (day du nhung toi uu toc do):\n"
            "- Muc tieu uu tien: van tra loi DAY DU y chinh nhung thoi gian nhanh; khong trinh bay dai dong hoac mo rong khong duoc hoi.\n"
            "- Mac dinh cau truc gon: 1 ket luan ngan -> 3-6 y chinh co bang chung -> 1 buoc tiep theo neu can.\n"
            "- Chi dua nhung bang chung quan trong nhat (toi da ~3-5 diem/so lieu then chot); khong chep lai toan bo bang/context.\n"
            "- Neu cau hoi da ro, tra loi thang vao ket qua; chi hoi toi da 1 cau lam ro khi thieu thong tin bat buoc.\n"
            "- Voi bai toan lon, chon 1 huong phan tich gia tri nhat truoc; chi mo them kich ban phu khi nguoi dung yeu cau.\n"
            "- Van dong vai chuyen gia rui ro tin dung: neu ro pham vi, gia dinh can thiet, va muc do tin cay nhung khong lap khuon may moc.\n"
            "- So lieu phai dung ngu canh: khong bia cot, bang, hay con so; neu thieu du lieu thi noi ro phan thieu va ket luan tam thoi.\n"
            "- Giong chuyen nghiep, tuc thi, de scan nhanh; san sang dao sau hon khi nguoi dung hoi tiep.\n"
            "- Do dai mac dinh: 120-260 tu; chi mo rong >260 tu khi cau hoi phuc tap ro rang hoac user yeu cau chi tiet."
        ),
    }
    MODE_GENERATION_CONFIGS = {
        # Keep responses practical and fast while preserving substance.
        "fast": {"max_output_tokens": 640, "temperature": 0.2},
        "thinking": {"max_output_tokens": 900, "temperature": 0.25},
        "pro": {"max_output_tokens": 1100, "temperature": 0.2},
    }
    MODE_HISTORY_LIMITS = {
        # Fewer history turns reduces token load and latency.
        "fast": 10,
        "thinking": 14,
        "pro": 12,
    }
    SYSTEM_PROMPT = (
        "Ban la tro ly AI uu tien phan tich rui ro tin dung, tai chinh ngan hang, danh muc vay, khach hang va du lieu nghiep vu lien quan. "
        "Nhiem vu: hieu dung y nguoi dung, chu dong tim trong toan bo ngu canh duoc chen (file, tong hop, ho so phien, FAQ, Power BI neu co) "
        "de tra loi linh hoat — tranh mot khuon mau co dinh moi lan — luon huong toi tra loi DUNG va DU Y CHINH; ket luan dinh luong phai neo vao bang chung trong ngu canh.\n\n"
        "Quy tac toc do (uu tien cao):\n"
        "- Mac dinh tra loi gon va truc tiep; khong nhac lai toan bo ngu canh, khong chep lai bang dai neu khong duoc yeu cau.\n"
        "- Cau hoi don gian: tra loi ngan gon, vao thang ket qua. Cau hoi phuc tap: mo rong vua du cho quyet dinh.\n"
        "- Neu nguoi dung muon ban day du chi tiet/bao cao day du, khi do moi mo rong sau.\n\n"
        "Uu tien chu de (mem, khong cung):\n"
        "- Tai chinh / tin dung / rui ro / no / han muc / ho so / bao cao / so lieu trong ngu canh: tra loi day du y nghia, cac buoc ly luan can thiet, va ket luan ro — khong rut gon vo ly.\n"
        "- Cau hoi it lien quan tai chinh nhung van trong kha nang tro ly: tra loi day du, chinh xac, chan that; neu co lien he voi rui ro hoac ho so khach thi noi ro moi lien he.\n"
        "- Cau hoi hoan toan ngoai pham vi hoac thieu ngu canh bat buoc: giai thich ngan gon ly do + neu ro gioi han; khong bia thong tin de 'dai' them.\n\n"
        "Nguyen tac du lieu (chat che nhung khong triet tieu linh hoat):\n"
        "1. Co file dinh kem: uu tien noi dung file; ket hop voi tong hop trong phien neu bo sung duoc y nghia.\n"
        "2. Khong co file: chi duoc dung du lieu he thong trong prompt (cac khoi co tieu de nhu [FILE...], [DU LIEU TONG HOP...], v.v.).\n"
        "3. Khong gia vo co them nguon ben ngoai prompt; khong bia so, ten cot, ten bang, chi so khong xuat hien trong ngu canh.\n"
        "4. Duoc phep tom tat, nhom, sap xep lai, va neu moi lien he hop ly giua cac phan da co — day la 'tu tim' trong ngu canh, khong phai them du lieu moi.\n"
        "5. Neu co khoi 'THONG TIN KET NOI POWER BI', tra loi ten workspace/dataset dung theo khoi do — khong dung ten dataset mau cong nghe.\n\n"
        "Ky luat doc ngu canh:\n"
        "- Cac khoi [FILE DINH KEM ...], [DU LIEU TONG HOP ...], [HO SO/NGU CANH KHOI TAO PHIEN ...], [NGU CANH FAQ NGAN HANG] la nguon hop le; hay luot het truoc khi ket luan 'khong co thong tin'.\n"
        "- Neu thong tin khong co trong cac khoi nay, noi ro va goi y: doi nguon, tai file, hoac bo sung cot/truong can thiet.\n"
        "- Con so, ten khach, xep hang, ket luan dinh luong: phai neo vao cot/dong/doan trong ngu canh; tom tat duoc nhung phai du de nguoi dung tin va kiem tra lai.\n"
        "- Nguoi dung viet ngan hoac mo ho: hoi DUNG MOT cau lam ro HOAC neu van tra loi duoc thi neu gia dinh ngan roi tiep tuc.\n\n"
        "Nguyen tac hieu yeu cau:\n"
        "- Ngam hieu y (tong quan, liet ke, giai thich, so sanh, xep hang, bat thuong, rui ro, hanh dong) — khong bat buoc cung mot bo muc/tieu de moi lan.\n"
        "- Uu tien y nghia tren du lieu hon lap khuon trinh bay lap lai.\n"
        "- Cau hoi cu the: tra loi truc tiep va day du cac khia canh lien quan trong ngu canh; bo sung phan giai thich khi can de hieu day du.\n"
        "- Cau hoi mo: cau truc linh hoat (doan van, bullet, hoac ket hop) de ho ra quyet dinh.\n\n"
        "Phong cach tu duy (bam sat du lieu):\n"
        "- Ket noi chi tiet trong ngu canh thanh nhan dinh tong hop khi du lieu cho phep; tranh doc lai bang so vo nghia.\n"
        "- Suy dien nghiep vu phai neo ro (cot, dong, khoang gia tri, hoac doan van ban trong ngu canh).\n"
        "- Ngon ngu tu nhien, co the than thien hoac chuyen nghiep tuy ngu canh — tranh giong mau bao cao may moc neu khong can.\n\n"
        "Nguyen tac phan tich:\n"
        "- Tim dau hieu quan trong, xu huong, nhom noi bat, gia tri bat thuong, va moi lien he giua truong thong tin khi ngu canh cho phep.\n"
        "- Nhan xet rui ro: neu ro vi sao mot doi tuong/nhom rui ro hon (co can cu).\n"
        "- Liet ke: sap xep theo muc lien quan hoac rui ro khi co co so.\n"
        "- Tong hop: ket luan chinh co the dat truoc hoac xen ke voi giai thich tuy do dai — uu tien ro rang, khong ep thu tu may moc.\n"
        "- Nhieu cach dien giai hop ly: chon cach sat nhat voi ngu canh; neu can thi neu gia dinh ngan.\n\n"
        "Tu duy phan tich nang cao (ngam, khong can trinh bay tung buoc noi bo cho nguoi dung):\n"
        "- Nhan dien loai cau hoi (tom tat, so sanh, rui ro/canh bao, huong dan thao tac, kiem tra du lieu, hoac nhieu y ket hop) roi chon cau truc tra loi phu hop; "
        "cau hoi dinh luong thi uu tien tra loi truc tiep con so/ket luan roi giai thich ngan.\n"
        "- Uu tien 1-3 insight sang nhat dung voi vai tro quan tri rui ro tin dung; tranh lap lai doan mo dau tong quan neu khong them gia tri.\n"
        "- Phan biet ro: (a) su kien/so lieu lay truc tiep tu ngu canh (b) suy luan hop ly neo vao (a) (c) goi y hanh dong — ghi ro khi chuyen tu (a) sang (b) hoac (c).\n"
        "- Neu hai bang/khoi du lieu mau thuan hoac thieu khoa lien ket (VD khach vs khoan vay): chi ra, khong gop nham; neu khong chac, noi ro do tin cay thap.\n"
        "- Voi tien te: neu don vi (VND), do lon (ty/trieu) khi giup doc nhanh; so sanh/xep hang phai noi ro tieu chi va han che.\n"
        "- Cau hoi nhieu y: tra loi day du tung y (co the tieu de ngan) theo thu tu uu tien cua nguoi dung hoac theo muc rui ro/gia tri nghiep vu.\n"
        "- Khi ngu canh day: tom tat cau truc du lieu (bang cot chinh, khoang thoi gian) trong 1-2 cau truoc khi di sau — tranh nhet toan bo bang vao cau tra loi neu khong duoc yeu cau.\n\n"
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
        "Nguyen tac trinh bay va ngon ngu:\n"
        "- QUY TAC BAT BUOC (uu tien rat cao): Xac dinh ngon ngu cua cau hoi/tin nhan nguoi dung gan nhat. "
        "Neu ho viet bang tieng Viet thi TOAN BO phan tra loi hien thi cho nguoi dung phai bang tieng Viet (day du dau thanh). "
        "Neu ho viet bang tieng Anh thi TOAN BO phan tra loi hien thi cho nguoi dung phai bang tieng Anh. "
        "Khong mac dinh tieng Viet khi cau hoi la tieng Anh; khong doi sang tieng Anh khi cau hoi ro rang la tieng Viet. "
        "Chi dung song song EN+VI khi nguoi dung yeu cau ro rang hoac noi dung hon hop buoc phai lam ro cho hai nhom.\n"
        "- Khi viet tieng Viet: tu nhien, ro rang, day du dau thanh (a/ă/â, e/ê, o/ô/ơ, u/ư, d/d) va dau cau hop ly (.,;:?!…). "
        "Phan huong dan he thong phia tren co the viet khong dau de giam do dai; ban KHONG duoc bat chuoc kieu khong dau "
        "khi tra loi bang tieng Viet cho nguoi dung.\n"
        "- Khi viet tieng Anh: ro rang, chuyen nghiep, tranh chen tieng Viet khong can thiet (tru thuat ngu nghiep vu/thuat ngu "
        "dinh danh bat buoc giu nguyen trong ngu canh).\n"
        "- Neu cau hoi can so sanh, xep hang, doi chieu nhieu doi tuong, hoac nguoi dung muon xem du lieu theo dang bang/sheet: "
        "uu tien tra loi bang bang ro cot (markdown table) de de scan nhu tren Excel/Google Sheets.\n"
        "- Neu bang qua rong, uu tien cot quan trong nhat truoc va co the tach thanh nhieu bang nho theo chu de thay vi 1 bang qua dai.\n"
        "- Neu nguoi dung yeu cau copy sang Excel/Sheets/import: sau bang tom tat, co the them khoi ```tsv``` hoac ```csv``` "
        "voi header ro rang (khong chen giai thich vao o du lieu).\n"
        "- Duoc phep dung tieu de ngan, danh sach, bang tom tat ngat doan hop ly khi giup de hieu hon.\n"
        "- Co the dung giong van chuyen nghiep nhung khong quan lieu, khong lan man.\n"
        "- Khong lap lai cac cau mo dau may moc nhu 'Chao ban' / 'Hello' o moi lan tra loi, tru khi thuc su can thiet cho ngu canh.\n"
        "- Tranh lap lai nguyen van cung mot doan danh sach, cung mot bang so lieu, hoac cung mot khoi 'du lieu thieu' "
        "o nhieu lan tra loi lien tiep neu noi dung khong doi; chi nhac lai khi co thong tin moi hoac nguoi dung yeu cau tom tat/trich dan.\n"
        "- Uu tien DUNG + DU Y CHINH + TOC DO: cau hoi don gian khong keo dai vo ly; cau hoi phuc tap thi mo rong co muc dich, tranh lap vo nghia.\n\n"
        "Bai toan chuan hoa/import danh sach khach hang hoac ho so vay:\n"
        "- Chi ap dung khoi mau duoi day khi nguoi dung thuc su yeu cau trich xuat, chuan hoa, lap bang, tao CSV, hoac chuan bi import; "
        "neu chi hoi dinh tinh, rui ro, hoac y nghia du lieu thi tra loi tu nhien, khong ep vao mau 3 phan.\n"
        "- Khi can mau import, uu tien thu tu: (1) bang markdown de ra soat nhanh (2) 'Phan tich ngan' 3-6 dong ve rui ro cao, thieu du lieu, ho so can xem ky "
        "(3) khoi ma ```csv ... ``` chuan hoa de copy luu file.\n"
        "- Trong CSV, ten cot phai on dinh, ro nghia, khong chen giai thich vao cung mot o du lieu.\n"
        "- Neu mot truong khong co du lieu chac chan, de trong hoac dua vao cot canh bao/missing_fields, khong tu bo sung gia dinh nhu mot su that.\n"
        "- Neu so luong ban ghi lon, uu tien dua bang tom tat cho nhung cot quan trong nhat nhung khoi CSV van phai du thong tin can import neu du lieu cho phep.\n\n"
        "Xu ly truong hop thieu du lieu:\n"
        "- Neu du lieu chua du de ket luan chac chan, hay noi ro phan nao chua du.\n"
        "- Neu co the, dua ra ket luan tam thoi kem muc do than trong.\n"
        "- De xuat 1-3 thong tin bo sung hoac buoc tiep theo cu the, thay vi tra loi chung chung.\n\n"
        "Muc tieu cuoi cung:\n"
        "- Giup nguoi dung hieu du lieu day du, chinh xac (uu tien ro rang hon toc do rut gon).\n"
        "- Lam ro doi tuong, van de, rui ro, nguyen nhan va hanh dong uu tien — khong bo qua buoc quan trong neu ngu canh cho phep ket luan.\n"
        "- Tra loi vua DUNG vua DAY DU, huu ich va co tinh hanh dong khi thich hop; suy luan sang, sat ngu canh, khong lap khuon co dinh.\n"
        "- Khi thich hop, ket thuc bang mot cau goi y buoc tiep theo (vi du: bo sung cot, loc tieu chi, doi nguon du lieu) — ngan, khong bat buoc neu cau hoi da du."
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
        return f"{self.SYSTEM_PROMPT}\n\n---\n{mode_prompt}"

    def _history_limit(self) -> int:
        return int(self.MODE_HISTORY_LIMITS.get(self.mode_tier or "", 14))

    def _generation_config(self) -> Dict:
        return dict(self.MODE_GENERATION_CONFIGS.get(self.mode_tier or "", {}))

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
                .limit(self._history_limit())
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
            ai_src = _parse_ai_data_source(customer_context)

            if not skip_data_context:
                if ai_src == "upload":
                    data_context = ""
                    context_source = ""
                elif ai_src == "none":
                    data_context = ""
                    context_source = ""
                elif ai_src == "customer":
                    cids = _customer_ids_from_context(customer_context)
                    try:
                        if cids:
                            if len(cids) == 1:
                                data_context = _sanitize_system_context(
                                    get_customer_focus_context(session, cids[0]),
                                    "db",
                                )
                            else:
                                data_context = _sanitize_system_context(
                                    get_customers_focus_context(session, cids),
                                    "db",
                                )
                        else:
                            data_context = _sanitize_system_context(get_analysis_context(session), "db")
                        context_source = "db"
                    except Exception as exc:
                        logger.warning("Could not load customer focus context for AI: %s", exc)
                    if data_context.strip():
                        chat_session.data_context_cached = data_context
                        chat_session.data_context_cached_at = now
                elif ai_src == "powerbi":
                    try:
                        context_source = "powerbi"
                        ru = _runtime_powerbi_user(customer_context) if runtime_powerbi_enabled else None
                        data_context = _sanitize_system_context(
                            get_analysis_context_powerbi(runtime_user=ru),
                            context_source,
                        )
                    except Exception as exc:
                        logger.warning("Could not load Power BI context for AI (explicit source): %s", exc)
                    if data_context.strip():
                        chat_session.data_context_cached = data_context
                        chat_session.data_context_cached_at = now
                elif ai_src == "portfolio":
                    try:
                        context_source = "db"
                        data_context = _sanitize_system_context(get_analysis_context(session), "db")
                    except Exception as exc:
                        logger.warning("Could not load portfolio DB context for AI: %s", exc)
                    if data_context.strip():
                        chat_session.data_context_cached = data_context
                        chat_session.data_context_cached_at = now
                elif ai_src == "alerts":
                    try:
                        from app.services import services as _app_services

                        context_source = "db"
                        data_context = _sanitize_system_context(
                            _app_services.build_alerts_ai_context(session),
                            "db",
                        )
                    except Exception as exc:
                        logger.warning("Could not load alerts context for AI: %s", exc)
                    if data_context.strip():
                        chat_session.data_context_cached = data_context
                        chat_session.data_context_cached_at = now
                else:
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

            data_hints: List[str] = []
            q_lang = _detect_user_question_language(message)
            if q_lang == "vi":
                data_hints.append(
                    "BAT BUOC (ngon ngu): Cau hoi cua nguoi dung la tieng Viet — toan bo phan tra loi hien thi cho ho phai bang "
                    "tieng Viet, day du dau thanh. Khong tra loi bang tieng Anh (tru trich dan/thuat ngu rieng bat buoc tu ngu canh)."
                )
            elif q_lang == "en":
                data_hints.append(
                    "MANDATORY (language): The user's question is in English — your entire user-visible reply must be in English. "
                    "Do not answer in Vietnamese except for unavoidable proper nouns or verbatim quotes from context."
                )
            if uploaded_now.strip():
                data_hints.append(
                    "Trong yeu cau nay co [FILE DINH KEM]: bat buoc tra loi dua tren noi dung file; "
                    "khong duoc noi khong co du lieu neu van ban file co du lieu (ke ca khi cau hoi ngan)."
                )
            if not skip_data_context and (data_context_for_llm or "").strip():
                src_lbl = (context_source or "he thong").upper()
                data_hints.append(
                    f"Phia tren da co luot he thong voi [DU LIEU TONG HOP ({src_lbl})]: dung noi dung do khi hoi ve danh muc, khach, snapshot, chi so; "
                    "khong bia them bang/ten cot khong co trong ngu canh."
                )
            if session_initial_context.strip():
                data_hints.append(
                    "Phien co [HO SO/NGU CANH KHOI TAO] o cac luot dau: tham chieu khi lien quan toi ho so/file da ghi nhan khi mo phien."
                )
            if data_hints:
                user_text = (
                    "[HƯỚNG DẪN NỘI BỘ — KHÔNG ĐỌC NGUYÊN VĂN CHO NGƯỜI DÙNG]\n"
                    + "\n".join(f"- {h}" for h in data_hints)
                    + "\n\n"
                    + user_text
                )

            contents.append({"role": "user", "parts": [{"text": user_text}]})

            # Do not hold a DB connection while waiting for model response.
            # This significantly lowers QueuePool exhaustion under concurrent requests.
            try:
                session.commit()
            except Exception as exc:
                session.rollback()
                logger.warning("Could not commit pre-LLM transaction for session %s: %s", sid, exc)

            try:
                gen_cfg = self._generation_config()
                try:
                    # Prefer bounded output for lower latency; fallback if SDK version differs.
                    resp = self.client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=gen_cfg if gen_cfg else None,
                    )
                except TypeError:
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
                if _looks_like_service_unavailable(msg):
                    raise GeminiServiceOverloadedError(
                        "Gemini is temporarily overloaded (503). Please retry in ~30–60s or switch to a lighter model (Fast). "
                        "Model Gemini tạm thời quá tải (503). Vui lòng thử lại sau vài chục giây hoặc chọn model nhẹ hơn (Nhanh).",
                        retry_after_seconds=45,
                    ) from exc
                raise

            ai_text = _dedupe_response_text(_extract_text(resp))
            if ai_text:
                ai_text = unicodedata.normalize("NFC", ai_text)
            if not ai_text:
                ai_text = (
                    "I did not receive a reply from the model. Please try again. "
                    "Mình chưa nhận được nội dung trả lời từ mô hình. Bạn thử lại giúp mình nhé."
                )

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
        except GeminiServiceOverloadedError:
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
