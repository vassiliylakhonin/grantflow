#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from grantflow.core.version import __version__, is_valid_core_semver  # noqa: E402

TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.]+)?$")


def _normalize_tag(raw_tag: str) -> str:
    tag = str(raw_tag or "").strip()
    if tag.startswith("refs/tags/"):
        tag = tag[len("refs/tags/") :]
    return tag


def _check(condition: bool, ok_message: str, fail_message: str, errors: list[str]) -> None:
    if condition:
        print(f"[ok] {ok_message}")
    else:
        errors.append(fail_message)
        print(f"[fail] {fail_message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release governance guardrails.")
    parser.add_argument("--tag", default="", help="Optional release tag (vX.Y.Z) for strict release checks.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root path (default: auto-detected).",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    changelog_path = repo_root / "CHANGELOG.md"
    api_stability_path = repo_root / "docs" / "api-stability-policy.md"
    release_process_path = repo_root / "docs" / "release-process.md"
    pr_template_path = repo_root / ".github" / "pull_request_template.md"

    errors: list[str] = []
    _check(changelog_path.exists(), "CHANGELOG.md present", "CHANGELOG.md missing", errors)
    _check(api_stability_path.exists(), "API stability policy present", "docs/api-stability-policy.md missing", errors)
    _check(release_process_path.exists(), "Release process doc present", "docs/release-process.md missing", errors)
    _check(pr_template_path.exists(), "PR template present", ".github/pull_request_template.md missing", errors)

    _check(
        is_valid_core_semver(__version__),
        f"runtime version is valid core SemVer ({__version__})",
        f"runtime version is not valid core SemVer: {__version__}",
        errors,
    )

    changelog_text = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else ""
    _check(
        "## [Unreleased]" in changelog_text,
        "CHANGELOG has [Unreleased] section",
        "CHANGELOG missing [Unreleased] section",
        errors,
    )
    _check(
        f"## [{__version__}]" in changelog_text,
        f"CHANGELOG contains current version section ({__version__})",
        f"CHANGELOG missing current version section: ## [{__version__}]",
        errors,
    )

    tag = _normalize_tag(args.tag)
    if tag:
        _check(
            bool(TAG_PATTERN.match(tag)),
            f"tag format looks valid ({tag})",
            f"invalid tag format: {tag} (expected vX.Y.Z)",
            errors,
        )
        if TAG_PATTERN.match(tag):
            tag_version = tag[1:]
            _check(
                tag_version == __version__,
                f"tag version matches runtime version ({tag_version})",
                f"tag version {tag_version} does not match runtime version {__version__}",
                errors,
            )
            _check(
                f"## [{tag_version}]" in changelog_text,
                f"CHANGELOG contains release section for {tag_version}",
                f"CHANGELOG missing release section for {tag_version}",
                errors,
            )

    if errors:
        print("\nRelease guard failed with the following issue(s):")
        for idx, error in enumerate(errors, start=1):
            print(f"{idx}. {error}")
        return 1

    print("\nRelease guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
