"""Conservative duplicate candidate detection; never silently deletes records."""
from __future__ import annotations

from typing import Any

from .normalize import normalize_record


def _coordinates(record: dict[str, Any]) -> tuple[float, float] | None:
    try:
        lat, lon = float(record["latitude"]), float(record["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _near(a: tuple[float, float], b: tuple[float, float], tolerance: float = 0.0005) -> bool:
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance


def duplicate_reason(a: dict[str, Any], b: dict[str, Any]) -> str | None:
    """Return a reason only for strong matches; ambiguous pairs remain separate."""
    na, nb = normalize_record(a), normalize_record(b)

    if a.get("source_id") and a.get("source") == b.get("source") and a["source_id"] == b.get("source_id"):
        return "same_source_id"

    if na["phone_key"] and na["phone_key"] == nb["phone_key"]:
        if na["name_key"] == nb["name_key"] or not na["name_key"] or not nb["name_key"]:
            return "same_phone_and_compatible_name"

    ca, cb = _coordinates(a), _coordinates(b)
    if ca and cb and _near(ca, cb):
        if na["name_key"] and na["name_key"] == nb["name_key"]:
            return "same_name_and_near_coordinates"

    return None


def find_duplicate_candidates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return candidate pairs for human review; input records are never modified."""
    candidates: list[dict[str, Any]] = []
    for i, left in enumerate(records):
        for j in range(i + 1, len(records)):
            right = records[j]
            reason = duplicate_reason(left, right)
            if reason:
                candidates.append({"left_index": i, "right_index": j, "reason": reason})
    return candidates
