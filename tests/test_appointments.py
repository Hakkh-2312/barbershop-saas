def _booking_payload(customer_id, service_id, start_time):
    return {"customer_id": customer_id, "service_id": service_id, "start_time": start_time}


def test_create_appointment_persists(client, shop, db_session):
    from app.models.appointment import Appointment

    headers, customer_id, service_id = shop

    resp = client.post(
        "/api/appointments",
        headers=headers,
        json=_booking_payload(customer_id, service_id, "2026-09-10T11:00:00"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "booked"
    assert body["end_time"] == "2026-09-10T11:20:00"
    assert body["customer_name"] == "Regular Customer"
    assert body["customer_phone"] == "0501234567"
    assert body["service_name"] == "Haircut"

    row = db_session.query(Appointment).filter(Appointment.id == body["id"]).first()
    assert row is not None
    assert row.customer_id == customer_id


def test_overlapping_booking_rejected(client, shop):
    headers, customer_id, service_id = shop
    payload = _booking_payload(customer_id, service_id, "2026-09-10T14:00:00")

    first = client.post("/api/appointments", headers=headers, json=payload)
    assert first.status_code == 201

    second = client.post(
        "/api/appointments",
        headers=headers,
        json={**payload, "start_time": "2026-09-10T14:10:00"},
    )
    assert second.status_code == 409


def test_non_overlapping_bookings_both_succeed(client, shop):
    headers, customer_id, service_id = shop

    first = client.post(
        "/api/appointments",
        headers=headers,
        json=_booking_payload(customer_id, service_id, "2026-09-10T09:00:00"),
    )
    second = client.post(
        "/api/appointments",
        headers=headers,
        json=_booking_payload(customer_id, service_id, "2026-09-10T09:20:00"),
    )
    assert first.status_code == 201
    assert second.status_code == 201


def test_unknown_customer_returns_404(client, shop):
    headers, _customer_id, service_id = shop
    resp = client.post(
        "/api/appointments",
        headers=headers,
        json=_booking_payload(999999, service_id, "2026-09-10T11:00:00"),
    )
    assert resp.status_code == 404


def test_unknown_service_returns_404(client, shop):
    headers, customer_id, _service_id = shop
    resp = client.post(
        "/api/appointments",
        headers=headers,
        json=_booking_payload(customer_id, 999999, "2026-09-10T11:00:00"),
    )
    assert resp.status_code == 404


def test_booking_outside_working_hours_rejected(client, shop):
    headers, customer_id, service_id = shop
    resp = client.post(
        "/api/appointments",
        headers=headers,
        json=_booking_payload(customer_id, service_id, "2026-09-10T06:00:00"),
    )
    assert resp.status_code == 422


def test_booking_on_closed_day_rejected(client, auth_headers, shop):
    headers, customer_id, service_id = shop

    # Close Monday for this tenant.
    close_resp = client.put(
        "/api/working-hours/1",
        headers=headers,
        json={"start_time": "00:00:00", "end_time": "00:00:00", "is_closed": True},
    )
    assert close_resp.status_code == 200

    # 2026-09-14 is a Monday.
    resp = client.post(
        "/api/appointments",
        headers=headers,
        json=_booking_payload(customer_id, service_id, "2026-09-14T10:00:00"),
    )
    assert resp.status_code == 422
