from app.core.security import decode_access_token
from app.models.notification import Notification


def _add_notification(db_session, tenant_id, **overrides):
    notification = Notification(
        tenant_id=tenant_id,
        type=overrides.get("type", "new_booking"),
        title=overrides.get("title", "New booking"),
        message=overrides.get("message", "Someone booked something."),
        appointment_id=overrides.get("appointment_id"),
        is_read=overrides.get("is_read", False),
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification


def _tenant_id_from_headers(headers):
    token = headers["Authorization"].split(" ", 1)[1]
    return decode_access_token(token)["tenant_id"]


def test_list_notifications_newest_first(client, auth_headers, db_session):
    headers = auth_headers(tenant_name="Notif Shop")
    tenant_id = _tenant_id_from_headers(headers)

    first = _add_notification(db_session, tenant_id, title="First")
    second = _add_notification(db_session, tenant_id, title="Second")

    resp = client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert [n["id"] for n in body] == [second.id, first.id]


def test_unread_only_filter(client, auth_headers, db_session):
    headers = auth_headers(tenant_name="Unread Shop")
    tenant_id = _tenant_id_from_headers(headers)

    _add_notification(db_session, tenant_id, title="Read one", is_read=True)
    unread = _add_notification(db_session, tenant_id, title="Unread one", is_read=False)

    resp = client.get("/api/notifications", headers=headers, params={"unread_only": True})
    assert resp.status_code == 200
    assert [n["id"] for n in resp.json()] == [unread.id]


def test_unread_count(client, auth_headers, db_session):
    headers = auth_headers(tenant_name="Count Shop")
    tenant_id = _tenant_id_from_headers(headers)

    _add_notification(db_session, tenant_id, is_read=True)
    _add_notification(db_session, tenant_id, is_read=False)
    _add_notification(db_session, tenant_id, is_read=False)

    resp = client.get("/api/notifications/unread-count", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


def test_mark_notification_read(client, auth_headers, db_session):
    headers = auth_headers(tenant_name="Mark Read Shop")
    tenant_id = _tenant_id_from_headers(headers)

    notification = _add_notification(db_session, tenant_id, is_read=False)

    resp = client.post(f"/api/notifications/{notification.id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True


def test_mark_all_notifications_read(client, auth_headers, db_session):
    headers = auth_headers(tenant_name="Mark All Shop")
    tenant_id = _tenant_id_from_headers(headers)

    _add_notification(db_session, tenant_id, is_read=False)
    _add_notification(db_session, tenant_id, is_read=False)

    resp = client.post("/api/notifications/read-all", headers=headers)
    assert resp.status_code == 200

    remaining_unread = client.get("/api/notifications/unread-count", headers=headers).json()
    assert remaining_unread == {"count": 0}


def test_notifications_are_tenant_isolated(client, auth_headers, db_session):
    headers_a = auth_headers(email="a@notif.com", tenant_name="Notif Shop A")
    headers_b = auth_headers(email="b@notif.com", tenant_name="Notif Shop B")
    tenant_a = _tenant_id_from_headers(headers_a)

    _add_notification(db_session, tenant_a, title="Shop A's notification")

    resp_b = client.get("/api/notifications", headers=headers_b)
    assert resp_b.status_code == 200
    assert resp_b.json() == []


def test_mark_read_requires_ownership(client, auth_headers, db_session):
    headers_a = auth_headers(email="owner@notif.com", tenant_name="Owner Shop")
    headers_b = auth_headers(email="intruder@notif.com", tenant_name="Intruder Shop")
    tenant_a = _tenant_id_from_headers(headers_a)

    notification = _add_notification(db_session, tenant_a)

    resp = client.post(f"/api/notifications/{notification.id}/read", headers=headers_b)
    assert resp.status_code == 404
