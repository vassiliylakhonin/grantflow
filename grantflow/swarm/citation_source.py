from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def citation_source_from_metadata(meta: Dict[str, Any]) -> Optional[str]:
    uploaded_filename = str(meta.get("uploaded_filename") or "").strip()
    if uploaded_filename:
        return uploaded_filename

    source = str(meta.get("source") or "").strip()
    if not source:
        return None

    if "/" in source or "\\" in source:
        basename = Path(source).name.strip()
        if basename:
            return basename
    return source


def citation_label_from_metadata(meta: Dict[str, Any], *, namespace: str, rank: int) -> str:
    citation = str(meta.get("citation") or "").strip()
    if citation:
        return citation

    source = citation_source_from_metadata(meta)
    if source:
        return source

    return f"{namespace}#{rank}"
