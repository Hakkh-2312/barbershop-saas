def test_signup_creates_tenant_and_returns_token(client):
    resp = client.post(
        "/api/auth/signup",
        json={"tenant_name": "New Shop", "email": "a@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_signup_duplicate_email_rejected(client):
    payload = {"tenant_name": "Shop 1", "email": "dup@example.com", "password": "supersecret123"}
    first = client.post("/api/auth/signup", json=payload)
    assert first.status_code == 201

    second = client.post(
        "/api/auth/signup",
        json={**payload, "tenant_name": "Shop 2"},
    )
    assert second.status_code == 409


def test_login_with_correct_credentials(client):
    client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Login Shop",
            "email": "login@example.com",
            "password": "supersecret123",
        },
    )

    resp = client.post(
        "/api/auth/login",
        data={"username": "login@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_with_wrong_password_rejected(client):
    client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Login Shop 2",
            "email": "login2@example.com",
            "password": "supersecret123",
        },
    )

    resp = client.post(
        "/api/auth/login",
        data={"username": "login2@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_email_rejected(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "nobody@example.com", "password": "whatever123"},
    )
    assert resp.status_code == 401
