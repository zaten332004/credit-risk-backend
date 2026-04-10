"""
Map exceptions to short, user-facing messages (no SQL / stack traces in API detail).
Call sites should log the full exception with logger.exception / logger.error.
"""

from __future__ import annotations

try:
    from sqlalchemy.exc import OperationalError as SAOperationalError
except Exception:  # pragma: no cover
    SAOperationalError = None  # type: ignore


def _is_sqlalchemy_dump(text: str) -> bool:
    t = text.lower()
    return any(
        x in t
        for x in (
            "pymysql",
            "sqlalchemy",
            "[sql:",
            "operationalerror",
            "from `",
            "from [",
        )
    )


def public_message_for_exception(exc: BaseException) -> str:
    """
    Vietnamese, operational messages suitable for HTTP `detail` and UI.
    """
    msg = str(exc).strip()
    low = msg.lower()

    # Gemini / Google GenAI (often very long error bodies)
    if "gemini_api_key" in low or ("api key" in low and "invalid" in low) or "api_key_invalid" in low:
        return "Khóa API Gemini không hợp lệ hoặc chưa được cấu hình. Kiểm tra biến GEMINI_API_KEY (hoặc gemini_api_key) trên máy chủ."
    if "resource has been exhausted" in low or "resource_exhausted" in low or "quota" in low and "exceed" in low:
        return "Đã vượt hạn mức hoặc quota Gemini. Vui lòng thử lại sau hoặc kiểm tra billing trên Google AI."
    if ("404" in msg or "not found" in low) and "model" in low:
        return "Model AI không tồn tại hoặc không khả dụng với khóa hiện tại. Hãy chọn model khác trong danh sách hoặc cập nhật GEMINI_MODEL."
    if "permission_denied" in low or ("permission" in low and "denied" in low):
        return "Không có quyền gọi API Gemini với khóa hiện tại. Kiểm tra quyền dự án và billing."

    if (
        (SAOperationalError is not None and isinstance(exc, SAOperationalError))
        or "operationalerror" in low
        or "pymysql.err" in low
    ):
        if "unknown column" in low and "data_context_cached" in low:
            return (
                "Cơ sở dữ liệu thiếu cột cache cho phiên chat AI (data_context_cached). "
                "Quản trị viên cần chạy migration MySQL cho bảng Chat_Session "
                "(scripts/migrate_chat_session_cache_mysql.sql)."
            )
        if "unknown column" in low or "1054" in msg:
            return (
                "Phiên bản cơ sở dữ liệu không khớp với ứng dụng (thiếu hoặc sai cột). "
                "Vui lòng chạy các script migration mới nhất hoặc liên hệ quản trị viên."
            )
        return "Lỗi cơ sở dữ liệu. Vui lòng thử lại sau hoặc liên hệ quản trị viên."

    if _is_sqlalchemy_dump(msg):
        return "Đã xảy ra lỗi khi truy cập dữ liệu. Vui lòng thử lại sau hoặc liên hệ quản trị viên."

    if len(msg) <= 200 and not _is_sqlalchemy_dump(msg):
        return msg

    return "Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau."


def chat_service_unavailable_message() -> str:
    return "Dịch vụ chat AI tạm thời không khả dụng. Vui lòng thử lại sau hoặc kiểm tra cấu hình máy chủ."
