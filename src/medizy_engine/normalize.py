"""Conservative normalization helpers; original source values are retained separately."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_text(value: Any) -> str:
    """Normalize Unicode, spacing and case without deleting meaningful characters."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text


def normalize_phone(value: Any) -> str:
    """Keep digits and a leading international plus; do not infer missing digits."""
    if value is None:
        return ""
    raw = str(value).strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    return ("+" if raw.startswith("+") else "") + digits


def normalize_wilaya(value: Any) -> str:
    """Normalize a wilaya label/code to a comparable text key."""
    return normalize_text(value)


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return normalized comparison keys while leaving the input untouched."""
    return {
        "name_key": normalize_text(record.get("name")),
        "address_key": normalize_text(record.get("address")),
        "wilaya_key": normalize_wilaya(record.get("wilaya")),
        "phone_key": normalize_phone(record.get("phone")),
    }
