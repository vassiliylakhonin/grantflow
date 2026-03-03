#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

CONVENTIONAL_PR_TITLE = re.compile(
    r"^(feat|fix|refactor|docs|test|chore)(\([a-z0-9._/-]+\))?: .+"
)


def _extract_pr_title_from_event(path: str) -> str:
    event_path = Path(path)
    if not event_path.exists():
        return ""
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return ""
    return str(pull_request.get("title") or "").strip()


def _resolve_title(explicit: str) -> str:
    title = str(explicit or "").strip()
    if title:
        return title
    event_path = str(os.getenv("GITHUB_EVENT_PATH") or "").strip()
    if event_path:
        return _extract_pr_title_from_event(event_path)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PR title with Conventional Commit format.")
    parser.add_argument("--title", default="", help="PR title to validate. If omitted, use GITHUB_EVENT_PATH.")
    args = parser.parse_args()

    title = _resolve_title(args.title)
    if not title:
        print("[skip] PR title guard skipped: title is not available")
        return 0

    if CONVENTIONAL_PR_TITLE.match(title):
        print(f"[ok] PR title follows Conventional Commit format: {title}")
        return 0

    print("[fail] PR title does not follow Conventional Commit format.")
    print(f"Title: {title}")
    print("Expected format: type(scope): summary")
    print("Allowed types: feat, fix, refactor, docs, test, chore")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
