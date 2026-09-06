from datetime import datetime

from app.models.appointment import Appointment


def _book(client, headers, customer_id, service_id, start_time):
    return client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": start_time},
    )


def test_list_appointments_returns_tenants_own_bookings(client, shop):
    headers, customer_id, service_id = shop
    _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00")
    _book(client, headers, customer_id, service_id, "2026-09-10T14:00:00")

    resp = client.get("/api/appointments", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    # Ordered by start_time.
    assert body[0]["start_time"] < body[1]["start_time"]


def test_list_appointments_filters_by_date_and_status(client, shop):
    headers, customer_id, service_id = shop
    _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00")
    other_day = _book(client, headers, customer_id, service_id, "2026-09-11T11:00:00").json()

    by_date = client.get("/api/appointments", headers=headers, params={"date": "2026-09-11"})
    assert [a["id"] for a in by_date.json()] == [other_day["id"]]

    client.post(f"/api/appointments/{other_day['id']}/cancel", headers=headers)
    cancelled = client.get("/api/appointments", headers=headers, params={"status": "cancelled"})
    assert [a["id"] for a in cancelled.json()] == [other_day["id"]]


def test_get_single_appointment(client, shop):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    resp = client.get(f"/api/appointments/{created['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_unknown_appointment_returns_404(client, auth_headers):
    headers = auth_headers()
    resp = client.get("/api/appointments/999999", headers=headers)
    assert resp.status_code == 404


def test_cancel_appointment_frees_the_slot(client, shop):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    cancelled = client.post(f"/api/appointments/{created['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    # The same slot should now be bookable again.
    rebooked = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00")
    assert rebooked.status_code == 201


def test_cancel_already_cancelled_appointment_rejected(client, shop):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    client.post(f"/api/appointments/{created['id']}/cancel", headers=headers)
    second_cancel = client.post(f"/api/appointments/{created['id']}/cancel", headers=headers)
    assert second_cancel.status_code == 409


def test_reschedule_to_free_slot_succeeds(client, shop):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    resp = client.post(
        f"/api/appointments/{created['id']}/reschedule",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["start_time"] == "2026-09-10T15:00:00"
    assert body["end_time"] == "2026-09-10T15:20:00"


def test_reschedule_onto_another_booking_rejected(client, shop):
    headers, customer_id, service_id = shop
    first = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()
    _book(client, headers, customer_id, service_id, "2026-09-10T15:00:00")

    resp = client.post(
        f"/api/appointments/{first['id']}/reschedule",
        headers=headers,
        json={"start_time": "2026-09-10T15:10:00"},
    )
    assert resp.status_code == 409


def test_reschedule_does_not_conflict_with_its_own_old_slot(client, shop):
    """Rescheduling to overlap the appointment's own current slot must not
    be rejected as a self-conflict."""
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    resp = client.post(
        f"/api/appointments/{created['id']}/reschedule",
        headers=headers,
        json={"start_time": "2026-09-10T11:05:00"},
    )
    assert resp.status_code == 200


def test_reschedule_outside_working_hours_rejected(client, shop):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    resp = client.post(
        f"/api/appointments/{created['id']}/reschedule",
        headers=headers,
        json={"start_time": "2026-09-10T06:00:00"},
    )
    assert resp.status_code == 422


def test_reschedule_cancelled_appointment_rejected(client, shop):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()
    client.post(f"/api/appointments/{created['id']}/cancel", headers=headers)

    resp = client.post(
        f"/api/appointments/{created['id']}/reschedule",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00"},
    )
    assert resp.status_code == 409


def test_cannot_act_on_another_tenants_appointment(client, shop, auth_headers):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    other_headers = auth_headers(email="other@shop.com", tenant_name="Other Shop")

    get_resp = client.get(f"/api/appointments/{created['id']}", headers=other_headers)
    assert get_resp.status_code == 404
    assert (
        client.post(f"/api/appointments/{created['id']}/cancel", headers=other_headers).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/appointments/{created['id']}/reschedule",
            headers=other_headers,
            json={"start_time": "2026-09-10T15:00:00"},
        ).status_code
        == 404
    )


def test_mark_no_show_succeeds_for_a_past_appointment(client, shop, db_session):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    appointment = db_session.query(Appointment).filter(Appointment.id == created["id"]).first()
    appointment.start_time = datetime(2020, 1, 1, 11, 0)
    appointment.end_time = datetime(2020, 1, 1, 11, 20)
    db_session.commit()

    resp = client.post(f"/api/appointments/{created['id']}/no-show", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_show"


def test_mark_no_show_rejected_for_a_future_appointment(client, shop):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()

    resp = client.post(f"/api/appointments/{created['id']}/no-show", headers=headers)
    assert resp.status_code == 422


def test_mark_no_show_rejected_for_a_cancelled_appointment(client, shop):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()
    client.post(f"/api/appointments/{created['id']}/cancel", headers=headers)

    resp = client.post(f"/api/appointments/{created['id']}/no-show", headers=headers)
    assert resp.status_code == 409
