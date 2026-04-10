from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


class AIChatFileContextService:
    MAX_PREVIEW_ROWS = 40
    MAX_PREVIEW_COLUMNS = 16
    MAX_CELL_CHARS = 160
    MAX_CONTEXT_CHARS = 12000

    @classmethod
    def extract_context(cls, *, filename: str, content: bytes) -> Dict[str, Any]:
        clean_name = Path(filename or "uploaded_file").name
        if not clean_name:
            raise ValueError("Thiếu tên file.")

        ext = Path(clean_name).suffix.lower()
        if ext not in {".csv", ".xlsx", ".xls"}:
            raise ValueError("Chỉ hỗ trợ file .csv, .xlsx, .xls cho AI Chat.")

        df = cls._read_dataframe(ext=ext, content=content)
        if df.empty and len(df.columns) == 0:
            raise ValueError("File không có dữ liệu để phân tích.")

        df = df.copy()
        df.columns = [str(col).strip() or f"column_{idx + 1}" for idx, col in enumerate(df.columns)]

        context_columns = [str(col) for col in df.columns[: cls.MAX_PREVIEW_COLUMNS]]
        preview_df = df.head(cls.MAX_PREVIEW_ROWS).fillna("")
        full_df = df.fillna("")

        context_lines: List[str] = [
            f"Tệp: {clean_name}",
            f"Định dạng: {ext.lstrip('.').upper()}",
            f"Số dòng dữ liệu: {len(df)}",
            f"Số cột dữ liệu: {len(df.columns)}",
            f"Danh sách cột: {', '.join(context_columns) if context_columns else '(không có cột)'}",
            "Dữ liệu mẫu:",
        ]

        if preview_df.empty:
            context_lines.append("(Không có dòng dữ liệu nào trong file)")
        else:
            for idx, (_, row) in enumerate(preview_df.iterrows(), start=1):
                parts: List[str] = []
                for col in context_columns:
                    parts.append(f"{col}={cls._normalize_cell(row.get(col))}")
                context_lines.append(f"{idx}. " + "; ".join(parts))

        context_text = "\n".join(context_lines).strip()
        if len(context_text) > cls.MAX_CONTEXT_CHARS:
            context_text = context_text[: cls.MAX_CONTEXT_CHARS].rstrip() + "\n...(đã rút gọn)"

        return {
            "file_name": clean_name,
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "columns": [str(col) for col in df.columns],
            "preview_rows": preview_df.to_dict(orient="records"),
            "full_rows": full_df.to_dict(orient="records"),
            "context_text": context_text,
        }

    @classmethod
    def _read_dataframe(cls, *, ext: str, content: bytes) -> pd.DataFrame:
        buffer = BytesIO(content)
        if ext == ".csv":
            last_error: Exception | None = None
            for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
                buffer.seek(0)
                try:
                    return pd.read_csv(buffer, encoding=encoding)
                except Exception as exc:  # pragma: no cover - best effort decoding
                    last_error = exc
            raise ValueError(f"Không thể đọc file CSV: {last_error}")

        buffer.seek(0)
        try:
            return pd.read_excel(buffer)
        except Exception as exc:
            raise ValueError(f"Không thể đọc file Excel: {exc}") from exc

    @classmethod
    def _normalize_cell(cls, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if len(text) > cls.MAX_CELL_CHARS:
            return text[: cls.MAX_CELL_CHARS - 3] + "..."
        return text
