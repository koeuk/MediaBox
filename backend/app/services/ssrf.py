"""SSRF guard: refuse downloads whose host resolves to a private/internal IP."""

import ipaddress
import socket

import httpx

from app.config import settings


def ensure_public_host(request: httpx.Request) -> None:
    """httpx request hook — runs on every redirect hop, not just the first URL."""
    if settings.allow_private_urls:
        return
    host = request.url.host
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        raise ValueError(f"Could not resolve host {host!r}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError(
                "This URL points to a private or internal address and cannot be downloaded"
            )
