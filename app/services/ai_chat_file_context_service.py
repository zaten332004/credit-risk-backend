from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


class AIChatFileContextService:
    MAX_PREVIEW_ROWS = 40
    MAX_CELL_CHARS = 160
    # ─Éß╗º cho nhiß╗üu cß╗Öt + v├ái chß╗Ñc d├▓ng mß║½u; vß║½n giß║úm sß╗æ d├▓ng nß║┐u v╞░ß╗út ng╞░ß╗íng.
    MAX_CONTEXT_CHARS = 48000

    @classmethod
    def extract_context(cls, *, filename: str, content: bytes) -> Dict[str, Any]:
        clean_name = Path(filename or "uploaded_file").name
        if not clean_name:
            raise ValueError("Thiß║┐u t├¬n file.")

        ext = Path(clean_name).suffix.lower()
        if ext not in {".csv", ".xlsx", ".xls"}:
            raise ValueError("Chß╗ë hß╗ù trß╗ú file .csv, .xlsx, .xls cho AI Chat.")

        df = cls._read_dataframe(ext=ext, content=content)
        if df.empty and len(df.columns) == 0:
            raise ValueError("File kh├┤ng c├│ dß╗» liß╗çu ─æß╗â ph├ón t├¡ch.")

        df = df.copy()
        df.columns = [str(col).strip() or f"column_{idx + 1}" for idx, col in enumerate(df.columns)]

        all_columns = [str(col) for col in df.columns]
        preview_df = df.head(cls.MAX_PREVIEW_ROWS).fillna("")
        full_df = df.fillna("")

        column_list = ", ".join(all_columns) if all_columns else "(kh├┤ng c├│ cß╗Öt)"
        if len(column_list) > 8000:
            column_list = column_list[:7997] + "..."

        header_lines: List[str] = [
            f"Tß╗çp: {clean_name}",
            f"─Éß╗ïnh dß║íng: {ext.lstrip('.').upper()}",
            f"Sß╗æ d├▓ng dß╗» liß╗çu: {len(df)}",
            f"Sß╗æ cß╗Öt dß╗» liß╗çu: {len(df.columns)}",
            f"Danh s├ích cß╗Öt: {column_list}",
            "Dß╗» liß╗çu mß║½u:",
        ]

        def sample_lines_for_rows(num_rows: int) -> List[str]:
            if num_rows <= 0 or preview_df.empty:
                return ["(Kh├┤ng c├│ d├▓ng dß╗» liß╗çu n├áo trong file)"]
            sub = preview_df.head(num_rows)
            lines: List[str] = []
            for idx, (_, row) in enumerate(sub.iterrows(), start=1):
                parts: List[str] = []
                for col in all_columns:
                    parts.append(f"{col}={cls._normalize_cell(row.get(col))}")
                lines.append(f"{idx}. " + "; ".join(parts))
            return lines

        context_text = ""
        for num_rows in range(cls.MAX_PREVIEW_ROWS, 0, -1):
            body = sample_lines_for_rows(num_rows)
            candidate = "\n".join(header_lines + body).strip()
            if len(candidate) <= cls.MAX_CONTEXT_CHARS:
                context_text = candidate
                break
        else:
            context_text = "\n".join(header_lines + sample_lines_for_rows(1)).strip()
            if len(context_text) > cls.MAX_CONTEXT_CHARS:
                context_text = context_text[: cls.MAX_CONTEXT_CHARS].rstrip() + "\n...(─æ├ú r├║t gß╗ìn)"

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
            raise ValueError(f"Kh├┤ng thß╗â ─æß╗ìc file CSV: {last_error}")

        buffer.seek(0)
        try:
            return pd.read_excel(buffer)
        except Exception as exc:
            raise ValueError(f"Kh├┤ng thß╗â ─æß╗ìc file Excel: {exc}") from exc

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
