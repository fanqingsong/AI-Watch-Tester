"""Login-redirect URL detection extracted from :mod:`aat.engine.executor`.

Owns the single source of truth for the substrings that identify a
login/auth page. :class:`StepExecutor` retains a
:data:`StepExecutor._LOGIN_URL_PATTERNS` class attribute (built from
:data:`_LOGIN_URL_SUBSTRINGS`) for backward-compatible introspection, but
all runtime detection goes through :func:`is_login_redirect`.
"""

from __future__ import annotations

# Login/auth URL substrings — if the browser lands here unexpectedly, the
# session has expired or authentication is required. This is the single
# source of truth for login-redirect detection; every call site must go
# through ``is_login_redirect`` so the pattern set stays consistent.
# It is a superset of all previously hard-coded pattern lists (including
# ``accounts/login`` and ``/auth`` which were missing from the post-step
# checks), so existing detections still fire and the documented gap is closed.
_LOGIN_URL_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "nidlogin",
        "/login",
        "/signin",
        "account/login",
        "accounts/login",
        "/auth",
    }
)


def is_login_redirect(url: str) -> bool:
    """Return True if ``url`` looks like a login/auth page.

    Case-insensitive substring match against :data:`_LOGIN_URL_SUBSTRINGS`.
    """
    if not url:
        return False
    lowered = url.lower()
    return any(pat in lowered for pat in _LOGIN_URL_SUBSTRINGS)


__all__ = ["_LOGIN_URL_SUBSTRINGS", "is_login_redirect"]
