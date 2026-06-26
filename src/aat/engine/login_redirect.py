"""Login-redirect URL detection extracted from :mod:`aat.engine.executor`.

Owns the single source of truth for the substrings that identify a
login/auth page. :class:`StepExecutor` retains a
:data:`StepExecutor._LOGIN_URL_PATTERNS` class attribute (built from

════════════════════════════════════════════════════════════════════════════════
                    🔐  Login Redirect Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Detects login/auth redirect patterns in URLs to identify when a test needs
to re-authenticate. Provides single source of truth for login URL patterns.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.login_redirect import is_login_url, is_login_redirect

# Check if current URL is a login page
current_url = "https://example.com/login"
if is_login_url(current_url):
    print("Need to login first")

# Check if redirecting to login
is_redirect = is_login_redirect(
    from_url="/dashboard",
    to_url="/login?redirect=/dashboard"
)
# Returns: True
```

⚙️  LOGIN URL PATTERNS
───────────────────────────────────────────────────────────────────────────────
Common login URL patterns:
• /login
• /signin
• /auth
• /auth/login
• /user/login
• /account/login
• /session/new
• ?redirect= (login after redirect)

💡 USE CASES
───────────────────────────────────────────────────────────────────────────────
• Detect session expiration during test
• Identify when re-authentication is needed
• Prevent false failures from login redirects
• Smart session management

════════════════════════════════════════════════════════════════════════════════

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
