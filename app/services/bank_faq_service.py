"""
Bank FAQ retrieval service.

Lightweight retrieval from CSV with columns:
- Question
- Answer
- Class (optional)
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config import settings


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


@dataclass
class FAQItem:
    question: str
    answer: str
    category: str = ""

    def combined_text(self) -> str:
        parts = [f"Question: {self.question}", f"Answer: {self.answer}"]
        if self.category:
            parts.append(f"Class: {self.category}")
        return ". ".join(parts).strip() + "."


def _tokenize(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")}


class BankFAQService:
    def __init__(self, csv_path: Optional[str] = None) -> None:
        self.csv_path = (csv_path or os.getenv("BANK_FAQ_CSV_PATH") or settings.bank_faq_csv_path or "").strip()
        self._items: List[FAQItem] = []
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.csv_path:
            return

        p = Path(self.csv_path)
        if not p.exists() or not p.is_file():
            return

        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q = (row.get("Question") or "").strip()
                a = (row.get("Answer") or "").strip()
                c = (row.get("Class") or "").strip()
                if not q or not a:
                    continue
                self._items.append(FAQItem(question=q, answer=a, category=c))

    def find_related(self, query: str, top_k: Optional[int] = None) -> List[Tuple[FAQItem, float]]:
        self._load()
        if not query or not self._items:
            return []

        k = top_k or settings.bank_faq_top_k
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        scored: List[Tuple[FAQItem, float]] = []
        for item in self._items:
            item_terms = _tokenize(item.question + " " + item.answer)
            if not item_terms:
                continue
            overlap = len(query_terms & item_terms)
            if overlap <= 0:
                continue
            score = overlap / max(1, len(query_terms))
            scored.append((item, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: max(1, int(k))]

    def build_context(self, query: str, top_k: Optional[int] = None) -> str:
        rows = self.find_related(query=query, top_k=top_k)
        if not rows:
            return ""
        return "\n".join(item.combined_text() for item, _ in rows)

