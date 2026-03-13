from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import ipaddress
import socket


def _allowed_attachment_roots() -> list[Path]:
    roots: list[Path] = []
    configured = os.getenv("GRANTFLOW_ATTACHMENT_ALLOWED_ROOTS", "").strip()
    if configured:
        for part in configured.split(","):
            token = part.strip()
            if not token:
                continue
            roots.append(Path(token).expanduser().resolve())
    if not roots:
        roots.append(Path.cwd().resolve())
        roots.append(Path(tempfile.gettempdir()).resolve())
    return roots


def resolve_allowed_attachment_path(path_text: str) -> Optional[Path]:
    candidate = str(path_text or "").strip()
    if not candidate:
        return None
    try:
        resolved = Path(candidate).expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None
    if not resolved.is_file():
        return None

    for root in _allowed_attachment_roots():
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    return None


def is_safe_webhook_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").strip()
    if not host:
        return False
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False

    # direct IP literal
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
        return True
    except ValueError:
        pass

    # resolve hostname and reject private/internal ranges
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip_text = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True
