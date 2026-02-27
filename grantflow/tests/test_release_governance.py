from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from grantflow.api.app import app
from grantflow.core.version import __version__, is_valid_core_semver


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_runtime_version_is_core_semver_and_matches_api_version():
    assert is_valid_core_semver(__version__) is True
    assert app.version == __version__


def test_release_guard_passes_for_current_repo_state():
    repo_root = _repo_root()
    script = repo_root / "scripts" / "release_guard.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Release guard passed." in completed.stdout


def test_release_guard_fails_on_tag_version_mismatch():
    repo_root = _repo_root()
    script = repo_root / "scripts" / "release_guard.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--tag", "v9.9.9"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "does not match runtime version" in completed.stdout
