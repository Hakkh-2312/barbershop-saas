def test_create_time_block(client, shop):
    headers, _customer_id, _service_id = shop
    resp = client.post(
        "/api/time-blocks",
        headers=headers,
        json={
            "start_time": "2026-09-10T15:00:00",
            "end_time": "2026-09-10T16:00:00",
            "reason": "Doctor's appointment",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["reason"] == "Doctor's appointment"


def test_start_must_be_before_end(client, shop):
    headers, _customer_id, _service_id = shop
    resp = client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-10T16:00:00", "end_time": "2026-09-10T15:00:00"},
    )
    assert resp.status_code == 422


def test_conflicting_block_rejected_with_appointment_details(client, shop):
    headers, customer_id, service_id = shop

    booked = client.post(
        "/api/appointments",
        headers=headers,
        json={
            "customer_id": customer_id,
            "service_id": service_id,
            "start_time": "2026-09-10T14:00:00",
        },
    )
    assert booked.status_code == 201

    resp = client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-10T13:30:00", "end_time": "2026-09-10T14:30:00"},
    )
    assert resp.status_code == 409
    assert "Regular Customer" in resp.json()["detail"]
    assert "14:00" in resp.json()["detail"]


def test_list_time_blocks_with_date_filter(client, shop):
    headers, _customer_id, _service_id = shop
    client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00", "end_time": "2026-09-10T16:00:00"},
    )
    client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-11T15:00:00", "end_time": "2026-09-11T16:00:00"},
    )

    all_blocks = client.get("/api/time-blocks", headers=headers)
    assert len(all_blocks.json()) == 2

    filtered = client.get("/api/time-blocks", headers=headers, params={"date": "2026-09-11"})
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["start_time"] == "2026-09-11T15:00:00"


def test_delete_time_block(client, shop):
    headers, _customer_id, _service_id = shop
    created = client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00", "end_time": "2026-09-10T16:00:00"},
    ).json()

    resp = client.delete(f"/api/time-blocks/{created['id']}", headers=headers)
    assert resp.status_code == 204

    remaining = client.get("/api/time-blocks", headers=headers)
    assert remaining.json() == []


def test_cannot_book_into_a_blocked_time(client, shop):
    headers, customer_id, service_id = shop
    client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00", "end_time": "2026-09-10T16:00:00"},
    )

    resp = client.post(
        "/api/appointments",
        headers=headers,
        json={
            "customer_id": customer_id,
            "service_id": service_id,
            "start_time": "2026-09-10T15:20:00",
        },
    )
    assert resp.status_code == 422
    assert "not available" in resp.json()["detail"]


def test_blocked_time_excluded_from_available_slots(client, shop, db_session):
    headers, _customer_id, service_id = shop
    client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00", "end_time": "2026-09-10T16:00:00"},
    )

    from datetime import date

    from app.models.service import Service
    from app.services.booking import get_available_slots

    service = db_session.query(Service).filter(Service.id == service_id).first()
    slots = get_available_slots(
        db_session, service.tenant_id, service, start_date=date(2026, 9, 10), num_days=1, limit=50
    )
    slot_times = {s.strftime("%H:%M") for s in slots}

    # 15:00-15:59 all fall inside the 15:00-16:00 block and must be gone.
    assert not any(t.startswith("15:") for t in slot_times)
    # 16:00 starts exactly when the block ends - adjacent, not overlapping,
    # so it should still be offered.
    assert "16:00" in slot_times


def test_deleting_block_frees_the_slot_again(client, shop):
    headers, customer_id, service_id = shop
    block = client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00", "end_time": "2026-09-10T16:00:00"},
    ).json()

    client.delete(f"/api/time-blocks/{block['id']}", headers=headers)

    resp = client.post(
        "/api/appointments",
        headers=headers,
        json={
            "customer_id": customer_id,
            "service_id": service_id,
            "start_time": "2026-09-10T15:20:00",
        },
    )
    assert resp.status_code == 201


def test_time_blocks_are_tenant_isolated(client, shop, auth_headers):
    headers, _customer_id, _service_id = shop
    other_headers = auth_headers(email="other@shop.com", tenant_name="Other Shop")

    client.post(
        "/api/time-blocks",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00", "end_time": "2026-09-10T16:00:00"},
    )

    other_blocks = client.get("/api/time-blocks", headers=other_headers)
    assert other_blocks.json() == []
