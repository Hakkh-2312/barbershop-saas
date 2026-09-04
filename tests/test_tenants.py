def test_get_my_tenant(client, auth_headers):
    headers = auth_headers(tenant_name="Get Test Shop")
    resp = client.get("/api/tenants/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Get Test Shop"
    assert body["phone"] is None
    assert body["address"] is None


def test_update_my_tenant(client, auth_headers):
    headers = auth_headers(tenant_name="Update Test Shop")
    resp = client.patch(
        "/api/tenants/me",
        headers=headers,
        json={"phone": "+972501234567", "address": "123 Main St"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == "+972501234567"
    assert body["address"] == "123 Main St"
    assert body["name"] == "Update Test Shop"

    refetched = client.get("/api/tenants/me", headers=headers).json()
    assert refetched["phone"] == "+972501234567"


def test_get_my_tenant_requires_auth(client):
    resp = client.get("/api/tenants/me")
    assert resp.status_code == 401


def test_update_does_not_affect_other_tenants(client, auth_headers):
    headers_a = auth_headers(email="a@iso.com", tenant_name="Shop A")
    headers_b = auth_headers(email="b@iso.com", tenant_name="Shop B")

    client.patch("/api/tenants/me", headers=headers_a, json={"phone": "111"})

    shop_b = client.get("/api/tenants/me", headers=headers_b).json()
    assert shop_b["phone"] is None
