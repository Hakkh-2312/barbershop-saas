def test_new_tenant_has_no_working_hours(client, auth_headers):
    headers = auth_headers()
    resp = client.get("/api/working-hours", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_set_working_hours_creates_then_updates(client, auth_headers):
    headers = auth_headers()

    created = client.put(
        "/api/working-hours/2",
        headers=headers,
        json={"start_time": "09:00:00", "end_time": "18:00:00", "is_closed": False},
    )
    assert created.status_code == 200
    assert created.json()["day_of_week"] == 2

    updated = client.put(
        "/api/working-hours/2",
        headers=headers,
        json={"start_time": "10:00:00", "end_time": "19:00:00", "is_closed": False},
    )
    assert updated.status_code == 200
    assert updated.json()["start_time"] == "10:00:00"

    listed = client.get("/api/working-hours", headers=headers)
    assert len(listed.json()) == 1


def test_invalid_day_of_week_rejected(client, auth_headers):
    headers = auth_headers()
    resp = client.put(
        "/api/working-hours/7",
        headers=headers,
        json={"start_time": "09:00:00", "end_time": "18:00:00"},
    )
    assert resp.status_code == 422
