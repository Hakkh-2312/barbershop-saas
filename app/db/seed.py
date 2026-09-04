from datetime import time

from app.db.session import SessionLocal
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.working_hours import WorkingHours


def seed_database():
    db = SessionLocal()

    try:
        # Don't create the shop twice
        existing_tenant = db.query(Tenant).first()

        if existing_tenant:
            print("Tenant already exists.")
            return

        # Create the barbershop
        tenant = Tenant(
            name="My Barbershop",
        )

        db.add(tenant)
        db.flush()

        # Sunday = 0, Monday = 1, ..., Saturday = 6
        schedule = [
            (0, time(9, 0), time(18, 0), False),  # Sunday
            (1, time(0, 0), time(0, 0), True),     # Monday - closed
            (2, time(9, 0), time(18, 0), False),  # Tuesday
            (3, time(9, 0), time(18, 0), False),  # Wednesday
            (4, time(9, 0), time(18, 0), False),  # Thursday
            (5, time(9, 0), time(18, 0), False),  # Friday
            (6, time(9, 0), time(18, 0), False),  # Saturday
        ]

        for day, start, end, closed in schedule:
            working_hours = WorkingHours(
                tenant_id=tenant.id,
                day_of_week=day,
                start_time=start,
                end_time=end,
                is_closed=closed,
            )

            db.add(working_hours)
            service = Service(
            tenant_id=tenant.id,
            name="Haircut",
            duration_minutes=20,
            price=50,
        )

        db.add(service)

        db.commit()

        print("Database seeded successfully.")


    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()