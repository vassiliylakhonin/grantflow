from __future__ import annotations

import re

__version__ = "2.0.0"

SEMVER_CORE_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def is_valid_core_semver(value: str) -> bool:
    return bool(SEMVER_CORE_PATTERN.match(str(value or "").strip()))
