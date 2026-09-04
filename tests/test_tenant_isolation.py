def test_availability_requires_auth(client):
    resp = client.get("/api/availability", params={"date": "2026-09-10"})
    assert resp.status_code == 401


def test_create_appointment_requires_auth(client):
    resp = client.post(
        "/api/appointments",
        json={"customer_id": 1, "service_id": 1, "start_time": "2026-09-10T11:00:00"},
    )
    assert resp.status_code == 401


def test_tenant_cannot_read_another_tenants_customer(client, auth_headers):
    shop_a = auth_headers(email="a@shop.com", tenant_name="Shop A")
    shop_b = auth_headers(email="b@shop.com", tenant_name="Shop B")

    created = client.post(
        "/api/customers",
        headers=shop_a,
        json={"name": "A's Customer", "phone": "0501111111"},
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]

    # Shop A can see it.
    own_read = client.get(f"/api/customers/{customer_id}", headers=shop_a)
    assert own_read.status_code == 200

    # Shop B cannot, even though it's a valid id.
    cross_read = client.get(f"/api/customers/{customer_id}", headers=shop_b)
    assert cross_read.status_code == 404


def test_tenant_cannot_delete_another_tenants_service(client, auth_headers):
    shop_a = auth_headers(email="a2@shop.com", tenant_name="Shop A2")
    shop_b = auth_headers(email="b2@shop.com", tenant_name="Shop B2")

    created = client.post(
        "/api/services",
        headers=shop_a,
        json={"name": "Haircut", "duration_minutes": 20, "price": 50},
    )
    service_id = created.json()["id"]

    resp = client.delete(f"/api/services/{service_id}", headers=shop_b)
    assert resp.status_code == 404

    # Still there for shop A.
    still_there = client.get(f"/api/services/{service_id}", headers=shop_a)
    assert still_there.status_code == 200


def test_tenant_cannot_book_using_another_tenants_ids(client, auth_headers):
    shop_a = auth_headers(email="a3@shop.com", tenant_name="Shop A3")
    shop_b = auth_headers(email="b3@shop.com", tenant_name="Shop B3")

    customer = client.post(
        "/api/customers", headers=shop_a, json={"name": "Cust", "phone": "0502222222"}
    ).json()
    service = client.post(
        "/api/services",
        headers=shop_a,
        json={"name": "Cut", "duration_minutes": 20, "price": 50},
    ).json()

    resp = client.post(
        "/api/appointments",
        headers=shop_b,
        json={
            "customer_id": customer["id"],
            "service_id": service["id"],
            "start_time": "2026-09-10T11:00:00",
        },
    )
    assert resp.status_code == 404
