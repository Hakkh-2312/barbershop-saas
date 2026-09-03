from fastapi import FastAPI

from app.api.routes import health
from app.core.config import settings

app = FastAPI(
    title="Barbershop SaaS API",
    version="0.1.0",
    debug=settings.debug,
)

app.include_router(health.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"message": "Barbershop SaaS API is running", "environment": settings.environment}
