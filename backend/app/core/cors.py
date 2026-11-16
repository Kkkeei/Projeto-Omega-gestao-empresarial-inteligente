"""Helpers for parsing trusted frontend origins."""
from __future__ import annotations


def parse_cors_origins(raw: str | None) -> list[str]:
    """Parse comma-separated origins, tolerating whitespace and accidental quotes."""
    values: list[str] = []
    seen: set[str] = set()
    for part in (raw or "").split(","):
        origin = part.strip().strip("\"'").strip().rstrip("/")
        if not origin:
            continue
        if not origin.startswith(("http://", "https://")):
            continue
        if origin not in seen:
            values.append(origin)
            seen.add(origin)
    return values


def development_origin_regex(environment: str | None) -> str | None:
    """Allow local Vite origins on loopback/private IPv4 only outside production."""
    if (environment or "development").strip().lower() in {"production", "prod"}:
        return None
    return (
        r"^https?://(?:localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|"
        r"192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}):5173$"
    )
