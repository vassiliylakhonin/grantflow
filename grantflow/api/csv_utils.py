from __future__ import annotations

from typing import Any


def flatten_value_rows(value: Any, *, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, dict):
        rows: list[tuple[str, str]] = []
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(flatten_value_rows(child, prefix=next_prefix))
        return rows
    if isinstance(value, list):
        list_rows: list[tuple[str, str]] = []
        for idx, child in enumerate(value):
            next_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            list_rows.extend(flatten_value_rows(child, prefix=next_prefix))
        return list_rows
    return [(prefix or "value", "" if value is None else str(value))]


def csv_escape(value: str) -> str:
    if any(ch in value for ch in [",", "\"", "\n", "\r"]):
        return '"' + value.replace('"', '""') + '"'
    return value


def csv_text_from_mapping(payload: dict[str, Any]) -> str:
    rows = flatten_value_rows(payload)
    lines = ["field,value"]
    for field, value in rows:
        lines.append(f"{csv_escape(field)},{csv_escape(value)}")
    return "\n".join(lines) + "\n"
