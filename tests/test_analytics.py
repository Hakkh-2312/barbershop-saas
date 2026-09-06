from datetime import date, timedelta


def _book(client, headers, customer_id, service_id, start_time):
    return client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": start_time},
    )


def _today_at(hour: int) -> str:
    return f"{date.today().isoformat()}T{hour:02d}:00:00"


def test_revenue_today_counts_only_todays_booked_appointments(client, shop):
    headers, customer_id, service_id = shop

    _book(client, headers, customer_id, service_id, _today_at(11))

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    _book(client, headers, customer_id, service_id, f"{tomorrow}T11:00:00")

    resp = client.get("/api/analytics/overview", headers=headers, params={"range": "today"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["revenue"] == 50.0


def test_cancelled_appointments_do_not_count_as_revenue(client, shop):
    headers, customer_id, service_id = shop

    created = _book(client, headers, customer_id, service_id, _today_at(11)).json()
    client.post(f"/api/appointments/{created['id']}/cancel", headers=headers)

    resp = client.get("/api/analytics/overview", headers=headers, params={"range": "today"})
    assert resp.json()["revenue"] == 0.0


def test_revenue_this_week_includes_todays_booking(client, shop):
    headers, customer_id, service_id = shop
    _book(client, headers, customer_id, service_id, _today_at(11))

    resp = client.get("/api/analytics/overview", headers=headers, params={"range": "week"})
    assert resp.status_code == 200
    assert resp.json()["revenue"] == 50.0


def test_revenue_this_month_includes_todays_booking(client, shop):
    headers, customer_id, service_id = shop
    _book(client, headers, customer_id, service_id, _today_at(11))

    resp = client.get("/api/analytics/overview", headers=headers, params={"range": "month"})
    assert resp.status_code == 200
    assert resp.json()["revenue"] == 50.0


def test_custom_range_requires_start_and_end(client, shop):
    headers, _customer_id, _service_id = shop
    resp = client.get("/api/analytics/overview", headers=headers, params={"range": "custom"})
    assert resp.status_code == 422


def test_custom_range_filters_correctly(client, shop):
    headers, customer_id, service_id = shop
    _book(client, headers, customer_id, service_id, _today_at(11))

    far_past = "2020-01-01"
    far_future = "2020-01-02"
    resp = client.get(
        "/api/analytics/overview",
        headers=headers,
        params={"range": "custom", "start": far_past, "end": far_future},
    )
    assert resp.status_code == 200
    assert resp.json()["revenue"] == 0.0


def test_new_customer_counted_in_range_they_were_created(client, shop):
    headers, _customer_id, _service_id = shop

    # "Regular Customer" was created by the `shop` fixture just now, so
    # they count as a new customer today.
    resp = client.get("/api/analytics/overview", headers=headers, params={"range": "today"})
    assert resp.json()["new_customers"] == 1
    assert resp.json()["total_customers"] == 1


def test_returning_customer_counted_only_after_a_prior_appointment(client, shop):
    headers, customer_id, service_id = shop

    # A booking today, with nothing before it: not "returning" for today.
    _book(client, headers, customer_id, service_id, _today_at(11))
    resp = client.get("/api/analytics/overview", headers=headers, params={"range": "today"})
    assert resp.json()["returning_customers"] == 0

    # A booking yesterday plus one today: today's report now sees them as
    # returning, since they had an appointment before today's range started.
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _book(client, headers, customer_id, service_id, f"{yesterday}T11:00:00")
    resp = client.get("/api/analytics/overview", headers=headers, params={"range": "today"})
    assert resp.json()["returning_customers"] == 1


def test_analytics_are_tenant_isolated(client, auth_headers):
    headers_a = auth_headers(email="a@analytics.com", tenant_name="Analytics Shop A")
    headers_b = auth_headers(email="b@analytics.com", tenant_name="Analytics Shop B")

    for day in range(7):
        client.put(
            f"/api/working-hours/{day}",
            headers=headers_a,
            json={"start_time": "09:00:00", "end_time": "18:00:00", "is_closed": False},
        )

    customer = client.post(
        "/api/customers", headers=headers_a, json={"name": "A's Customer", "phone": "0501112222"}
    ).json()
    service = client.post(
        "/api/services",
        headers=headers_a,
        json={"name": "Cut", "duration_minutes": 20, "price": 80},
    ).json()
    _book(client, headers_a, customer["id"], service["id"], _today_at(11))

    resp_b = client.get("/api/analytics/overview", headers=headers_b, params={"range": "today"})
    assert resp_b.status_code == 200
    body_b = resp_b.json()
    assert body_b["revenue"] == 0.0
    assert body_b["total_customers"] == 0
