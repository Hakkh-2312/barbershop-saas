import logging

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import (
    analytics,
    appointments,
    auth,
    availability,
    billing,
    customers,
    health,
    internal,
    notifications,
    services,
    tenants,
    time_blocks,
    whatsapp,
    working_hours,
)
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)

app = FastAPI(
    title="Barbershop SaaS API",
    version="0.1.0",
    debug=settings.debug,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    if settings.sentry_dsn:
        sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(availability.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(working_hours.router, prefix="/api")
app.include_router(whatsapp.router, prefix="/api")
app.include_router(tenants.router, prefix="/api")
app.include_router(time_blocks.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(internal.router, prefix="/api")
app.include_router(billing.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {
        "message": "Barbershop SaaS API is running",
        "environment": settings.environment,
    }
