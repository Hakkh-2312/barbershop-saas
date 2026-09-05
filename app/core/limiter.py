from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance - imported by main.py to wire up the app-level
# exception handler/middleware, and by individual routes to decorate
# specific endpoints (login, signup, the WhatsApp webhook).
limiter = Limiter(key_func=get_remote_address)
