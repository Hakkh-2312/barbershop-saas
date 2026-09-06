from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central app configuration. Values are read from the .env file (or real
    environment variables in production, e.g. on Render).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    # Auth
    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # App
    environment: str = "development"
    # Defaults to False so a deployment that forgets to set this explicitly
    # doesn't leak stack traces. Set DEBUG=true in .env for local dev.
    debug: bool = False

    # CORS - comma-separated list of allowed origins, e.g. the Next.js
    # dashboard's dev server and its deployed Vercel URL.
    cors_allowed_origins: str = "http://localhost:3000"

    # Logging / error monitoring
    log_level: str = "INFO"
    sentry_dsn: str | None = None

    # WhatsApp (filled in during Milestone 2)
    whatsapp_verify_token: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    # Meta App Secret (App Dashboard -> Settings -> Basic), used to verify
    # the X-Hub-Signature-256 header on incoming webhook POSTs so only Meta
    # can trigger bookings/cancellations through this endpoint. Signature
    # verification is skipped (with a warning) if this isn't set.
    whatsapp_app_secret: str | None = None
    # Which tenant this WhatsApp Business number belongs to. There's no
    # phone-number-to-tenant routing yet, so one WhatsApp number = one shop
    # until multiple shops are actually onboarded onto WhatsApp.
    whatsapp_tenant_id: int | None = None

    # A shared secret an external scheduler (e.g. a free cron-ping service)
    # must present to trigger internal jobs like sending appointment
    # reminders - there's no logged-in user for this kind of request, so
    # it can't go through the normal JWT auth. Unset means the endpoint
    # refuses every request.
    internal_task_secret: str | None = None

    # Billing (Stripe)
    stripe_secret_key: str | None = None
    # Dashboard -> Developers -> Webhooks -> (your endpoint) -> Signing secret.
    stripe_webhook_secret: str | None = None
    # The Price id (not Product id) of the one subscription plan, from
    # Dashboard -> Product catalog. Billing is unconfigured (checkout/portal
    # routes return an error) until both this and the secret key are set.
    stripe_price_id: str | None = None
    # Where Stripe should send the customer back after Checkout/the
    # Customer Portal - the deployed dashboard's own URL.
    dashboard_url: str = "http://localhost:3000"
    trial_period_days: int = 14

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


# Import this singleton everywhere instead of re-reading env vars.
settings = Settings()
