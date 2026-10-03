from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import re
from typing import Any


@dataclass(frozen=True)
class SourceEvidence:
    url: str
    title: str
    content: str
    source_version: str = ""
    published_at: str = ""
    retrieved_at: str = ""
    validity: str = "unverified"
    content_hash: str = ""


def evidence_from_record(record: dict[str, Any]) -> SourceEvidence:
    content = str(record.get("content") or record.get("summary") or "")
    return SourceEvidence(
        url=str(record.get("url") or ""),
        title=str(record.get("title") or ""),
        content=content[:20000],
        source_version=str(record.get("version") or record.get("source_version") or ""),
        published_at=str(record.get("published_at") or record.get("date") or ""),
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        validity=str(record.get("validity") or "unverified"),
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )


def contradiction_check(evidence: list[SourceEvidence]) -> list[dict[str, Any]]:
    claims: dict[str, list[SourceEvidence]] = {}
    for item in evidence:
        for sentence in re.split(r"(?<=[.!?])\s+", item.content):
            normalized = re.sub(r"\W+", " ", sentence.lower()).strip()
            if len(normalized.split()) >= 5:
                claims.setdefault(normalized, []).append(item)
    contradictions = []
    for index, left in enumerate(evidence):
        for right in evidence[index + 1:]:
            left_words = set(re.findall(r"\b[a-z0-9_]{5,}\b", left.content.lower()))
            right_words = set(re.findall(r"\b[a-z0-9_]{5,}\b", right.content.lower()))
            overlap = len(left_words & right_words) / max(1, len(left_words | right_words))
            if overlap >= 0.65 and left.content.strip() != right.content.strip():
                contradictions.append({"left": asdict(left), "right": asdict(right), "overlap": round(overlap, 3)})
    return contradictions


def verify_research(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    items = [evidence_from_record(x) for x in evidence if isinstance(x, dict)]
    contradictions = contradiction_check(items)
    verified = bool(items) and not contradictions
    return {
        "verified": verified,
        "source_count": len(items),
        "contradiction_count": len(contradictions),
        "contradictions": contradictions,
        "provenance": [asdict(x) for x in items],
    }
