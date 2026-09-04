def test_service_crud_cycle(client, auth_headers):
    headers = auth_headers()

    created = client.post(
        "/api/services",
        headers=headers,
        json={"name": "Beard Trim", "duration_minutes": 15, "price": 30},
    )
    assert created.status_code == 201
    service_id = created.json()["id"]

    listed = client.get("/api/services", headers=headers)
    assert any(s["id"] == service_id for s in listed.json())

    patched = client.patch(
        f"/api/services/{service_id}", headers=headers, json={"price": 35}
    )
    assert patched.status_code == 200
    assert patched.json()["price"] == 35

    deleted = client.delete(f"/api/services/{service_id}", headers=headers)
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/services/{service_id}", headers=headers)
    assert after_delete.status_code == 404


def test_service_duration_must_be_positive(client, auth_headers):
    headers = auth_headers()
    resp = client.post(
        "/api/services",
        headers=headers,
        json={"name": "Bad", "duration_minutes": 0, "price": 10},
    )
    assert resp.status_code == 422


def test_service_price_must_be_positive(client, auth_headers):
    headers = auth_headers()
    resp = client.post(
        "/api/services",
        headers=headers,
        json={"name": "Bad", "duration_minutes": 10, "price": 0},
    )
    assert resp.status_code == 422


def test_cannot_delete_service_with_appointments(client, shop):
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

    resp = client.delete(f"/api/services/{service_id}", headers=headers)
    assert resp.status_code == 409
