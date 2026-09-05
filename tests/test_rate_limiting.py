import pytest

from app.core.limiter import limiter


@pytest.fixture()
def rate_limiting_enabled():
    """conftest.py disables the limiter globally so the rest of the suite
    isn't throttled by the auth_headers fixture signing up once per test.
    Re-enable it just for these tests, and reset its in-memory counters
    afterwards so no leftover hits bleed into other tests."""
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()
    limiter.enabled = False


def test_login_is_rate_limited(client, rate_limiting_enabled):
    for _ in range(10):
        resp = client.post(
            "/api/auth/login",
            data={"username": "nobody@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    resp = client.post(
        "/api/auth/login",
        data={"username": "nobody@example.com", "password": "wrong"},
    )
    assert resp.status_code == 429


def test_signup_is_rate_limited(client, rate_limiting_enabled):
    for i in range(5):
        resp = client.post(
            "/api/auth/signup",
            json={
                "tenant_name": "Spam Shop",
                "email": f"spam{i}@example.com",
                "password": "supersecret123",
            },
        )
        assert resp.status_code == 201

    resp = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Spam Shop",
            "email": "spam-overflow@example.com",
            "password": "supersecret123",
        },
    )
    assert resp.status_code == 429
