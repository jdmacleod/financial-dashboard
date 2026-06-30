"""Best-effort in-process IP throttle for failed PAT authentication.

Per the eng review (outside-voice #8): a PAT secret is 32 url-safe bytes of
entropy, so online guessing is already infeasible — this is abuse / log-spam
control, not anti-brute-force. The store is intentionally in-memory: it resets
on restart and is per-process (not shared across uvicorn workers). That is an
accepted limitation for v1; a Redis-backed counter is the follow-up if a real
abuse case appears. Keyed on source IP because a failed PAT has no identity to
lock until it resolves.
"""

import time

from app.core.config import settings

# ip -> (failure_count, window_start_epoch)
_failures: dict[str, tuple[int, float]] = {}


def _window_seconds() -> int:
    return settings.lockout_minutes * 60


def is_throttled(ip: str | None) -> bool:
    if ip is None:
        return False
    entry = _failures.get(ip)
    if entry is None:
        return False
    count, started = entry
    if time.monotonic() - started >= _window_seconds():
        _failures.pop(ip, None)
        return False
    return count >= settings.max_login_attempts


def record_failure(ip: str | None) -> None:
    if ip is None:
        return
    now = time.monotonic()
    entry = _failures.get(ip)
    if entry is None or now - entry[1] >= _window_seconds():
        _failures[ip] = (1, now)
    else:
        _failures[ip] = (entry[0] + 1, entry[1])


def clear(ip: str | None) -> None:
    if ip is not None:
        _failures.pop(ip, None)


def reset_all() -> None:
    """Test hook — wipe the throttle store."""
    _failures.clear()
