from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# Import every model here so Alembic's autogenerate can discover them.
# (We'll add these as we design the schema, e.g.:)
# from app.models.barbershop import Barbershop  # noqa
# from app.models.user import User  # noqa
