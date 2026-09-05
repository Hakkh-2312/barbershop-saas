from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    """Render (and most PaaS/CDN setups) terminate the connection at a
    reverse proxy, so request.client.host is the proxy's hop, not the
    actual caller - it can even vary between requests, making per-IP
    limits meaningless. Prefer the first hop in X-Forwarded-For, which is
    the original client, and fall back to the raw socket address (e.g. in
    local dev, where there's no proxy in front)."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


# Shared limiter instance - imported by main.py to wire up the app-level
# exception handler/middleware, and by individual routes to decorate
# specific endpoints (login, signup, the WhatsApp webhook).
limiter = Limiter(key_func=get_client_ip)
