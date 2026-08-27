"""Health endpoint behavior."""


def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_health_is_public(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_health_has_request_id_header(client):
    r = client.get("/api/v1/health")
    assert r.headers.get("x-request-id")
