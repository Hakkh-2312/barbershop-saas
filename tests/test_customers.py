def test_customer_crud_cycle(client, auth_headers):
    headers = auth_headers()

    created = client.post(
        "/api/customers", headers=headers, json={"name": "Alice", "phone": "0501112222"}
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]

    listed = client.get("/api/customers", headers=headers)
    assert listed.status_code == 200
    assert any(c["id"] == customer_id for c in listed.json())

    got = client.get(f"/api/customers/{customer_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["name"] == "Alice"

    patched = client.patch(
        f"/api/customers/{customer_id}", headers=headers, json={"phone": "0509998888"}
    )
    assert patched.status_code == 200
    assert patched.json()["phone"] == "0509998888"

    deleted = client.delete(f"/api/customers/{customer_id}", headers=headers)
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/customers/{customer_id}", headers=headers)
    assert after_delete.status_code == 404


def test_customer_profile_includes_history_stats_and_notes(client, shop):
    from datetime import date, timedelta

    headers, customer_id, service_id = shop

    # A second service so "favorite" has something to actually pick between.
    beard = client.post(
        "/api/services",
        headers=headers,
        json={"name": "Beard trim", "duration_minutes": 15, "price": 20},
    ).json()

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Two past haircuts (the favorite), one past beard trim, one cancelled
    # haircut that shouldn't count toward anything, one still-upcoming visit.
    client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": f"{yesterday}T09:00:00"},
    )
    client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": f"{yesterday}T10:00:00"},
    )
    client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": beard["id"], "start_time": f"{yesterday}T11:00:00"},
    )
    cancelled = client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": f"{yesterday}T13:00:00"},
    ).json()
    client.post(f"/api/appointments/{cancelled['id']}/cancel", headers=headers)
    client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": f"{tomorrow}T09:00:00"},
    )

    client.patch(f"/api/customers/{customer_id}", headers=headers, json={"notes": "Low fade"})

    resp = client.get(f"/api/customers/{customer_id}", headers=headers)
    assert resp.status_code == 200
    profile = resp.json()

    assert profile["notes"] == "Low fade"
    # 4 non-cancelled appointments: 2 haircuts + 1 beard trim in the past,
    # plus the 1 still-upcoming haircut. The cancelled one doesn't count.
    assert profile["total_appointments"] == 4
    assert profile["total_spent"] == 50 * 3 + 20  # 3 haircuts + 1 beard trim
    assert profile["last_visit"].startswith(yesterday)
    assert profile["favorite_service"] == "Haircut"


def test_get_unknown_customer_returns_404(client, auth_headers):
    headers = auth_headers()
    resp = client.get("/api/customers/999999", headers=headers)
    assert resp.status_code == 404


def test_duplicate_phone_within_tenant_rejected(client, auth_headers):
    headers = auth_headers()
    client.post("/api/customers", headers=headers, json={"name": "First", "phone": "0505550000"})

    dup = client.post(
        "/api/customers", headers=headers, json={"name": "Second", "phone": "0505550000"}
    )
    assert dup.status_code == 409


def test_cannot_delete_customer_with_a_booked_appointment(client, shop):
    headers, customer_id, service_id = shop

    client.post(
        "/api/appointments",
        headers=headers,
        json={
            "customer_id": customer_id,
            "service_id": service_id,
            "start_time": "2026-09-10T11:00:00",
        },
    )

    resp = client.delete(f"/api/customers/{customer_id}", headers=headers)
    assert resp.status_code == 409


def test_deleting_customer_with_only_past_appointments_archives_instead(
    client, shop, db_session
):
    """A customer with only cancelled/completed appointment history can't
    be hard-deleted (appointments.customer_id is ON DELETE RESTRICT, kept
    for analytics/history) - deleting archives them instead: they
    disappear from the dashboard, but their appointment record and its
    customer_id reference both stay intact. A currently *booked*
    appointment still blocks deletion (see the test above) - cancelling
    it is what actually unblocks this, unlike before this fix."""
    from app.models.appointment import Appointment

    headers, customer_id, service_id = shop

    created = client.post(
        "/api/appointments",
        headers=headers,
        json={
            "customer_id": customer_id,
            "service_id": service_id,
            "start_time": "2026-09-10T11:00:00",
        },
    )
    appointment_id = created.json()["id"]
    client.post(f"/api/appointments/{appointment_id}/cancel", headers=headers)

    resp = client.delete(f"/api/customers/{customer_id}", headers=headers)
    assert resp.status_code == 204

    assert client.get(f"/api/customers/{customer_id}", headers=headers).status_code == 404
    listed = client.get("/api/customers", headers=headers)
    assert all(c["id"] != customer_id for c in listed.json())

    appointment = db_session.get(Appointment, appointment_id)
    assert appointment is not None
    assert appointment.customer_id == customer_id
    assert appointment.status == "cancelled"


def test_readding_a_deleted_customers_phone_restores_them(client, auth_headers):
    headers = auth_headers()
    created = client.post(
        "/api/customers", headers=headers, json={"name": "Bob", "phone": "0507771111"}
    )
    customer_id = created.json()["id"]
    client.delete(f"/api/customers/{customer_id}", headers=headers)

    restored = client.post(
        "/api/customers", headers=headers, json={"name": "Bob Again", "phone": "0507771111"}
    )
    assert restored.status_code == 201
    assert restored.json()["id"] == customer_id
    assert restored.json()["name"] == "Bob Again"

    listed = client.get("/api/customers", headers=headers)
    assert sum(1 for c in listed.json() if c["id"] == customer_id) == 1
