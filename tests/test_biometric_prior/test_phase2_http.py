"""Phase 2 — HTTP shim tests against the REAL server (stdlib http.client).

Exercises the five required cases through an actual socket on an ephemeral
port: 401 (bad token), 422 (bad payload + bad JSON), 201 (create), 200
(same-day update), and BIOMETRICS_ENABLED=0 (disabled → 404).
"""

from __future__ import annotations

import http.client
import json
import threading

import pytest

from harlo.biometric_prior.server import BioServer, InMemoryStore

VALID = {"captured_at": "2026-06-10T07:00:00", "sleep_minutes": 330, "source": "manual"}


@pytest.fixture
def server():
    started: list[BioServer] = []

    def factory(*, enabled=True, token="secret"):
        srv = BioServer(("127.0.0.1", 0), enabled=enabled, token=token,
                        store=InMemoryStore())
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        started.append(srv)
        return srv.server_address[1]

    yield factory
    for srv in started:
        srv.shutdown()
        srv.server_close()


def _post(port, body, token="secret", path="/v1/biometrics"):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    data = body if isinstance(body, str) else json.dumps(body)
    conn.request("POST", path, body=data, headers=headers)
    resp = conn.getresponse()
    status, payload = resp.status, resp.read().decode()
    conn.close()
    return status, payload


def test_201_create(server):
    port = server(enabled=True, token="secret")
    status, body = _post(port, VALID)
    assert status == 201, body
    assert json.loads(body)["created"] is True


def test_200_same_day_update(server):
    port = server(enabled=True, token="secret")
    assert _post(port, VALID)[0] == 201
    same_date = {**VALID, "captured_at": "2026-06-10T21:00:00", "sleep_minutes": 400}
    status, body = _post(port, same_date)
    assert status == 200, body
    assert json.loads(body)["created"] is False


def test_401_bad_token(server):
    port = server(enabled=True, token="secret")
    assert _post(port, VALID, token="WRONG")[0] == 401


def test_401_no_token(server):
    port = server(enabled=True, token="secret")
    assert _post(port, VALID, token=None)[0] == 401


def test_422_missing_required_field(server):
    port = server(enabled=True, token="secret")
    bad = {"captured_at": "2026-06-10T07:00:00", "source": "manual"}  # no sleep_minutes
    assert _post(port, bad)[0] == 422


def test_422_bad_json(server):
    port = server(enabled=True, token="secret")
    assert _post(port, "{not valid json")[0] == 422


def test_disabled_returns_404(server):
    port = server(enabled=False, token="secret")
    assert _post(port, VALID)[0] == 404


def test_wrong_path_404(server):
    port = server(enabled=True, token="secret")
    assert _post(port, VALID, path="/v1/nope")[0] == 404
