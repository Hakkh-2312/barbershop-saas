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
    debug: bool = True

    # WhatsApp (filled in during Milestone 2)
    whatsapp_verify_token: str | None = None
    whatsapp_access_token: str | None = None


# Import this singleton everywhere instead of re-reading env vars.
settings = Settings()
