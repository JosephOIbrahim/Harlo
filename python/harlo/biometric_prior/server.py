"""Phase 2 — HTTP shim for biometric_prior (stdlib http.server only).

POST /v1/biometrics, port 8787. Bearer token from HARLO_BIO_TOKEN; kill switch
BIOMETRICS_ENABLED (default off, enabled iff == "1"). Status codes:
  404 — wrong path, OR kill switch off (the feature is absent when disabled)
  405 — wrong method
  401 — missing/bad Bearer token
  422 — unparseable JSON or schema-invalid payload
  201 — accepted, new calendar date
  200 — accepted, same calendar date (idempotent update)

The store is pluggable: handle_request is the pure, socket-free core (unit
tested directly); Phase 3 swaps the in-memory store for the buffer + USD
persistence behind the same `upsert` interface.
"""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Protocol

from pydantic import ValidationError

from .schema import BiometricPrior

ROUTE = "/v1/biometrics"
DEFAULT_PORT = 8787


class BiometricStore(Protocol):
    def upsert(self, prior: BiometricPrior) -> bool:
        """Persist a prior keyed by calendar date. Return True if this created a
        new date, False if it updated an existing one."""
        ...


class InMemoryStore:
    """Phase 2 default store — date-keyed dict. Replaced in Phase 3."""

    def __init__(self) -> None:
        self._by_date: dict[str, BiometricPrior] = {}

    def upsert(self, prior: BiometricPrior) -> bool:
        created = prior.calendar_date not in self._by_date
        self._by_date[prior.calendar_date] = prior
        return created


def enabled_from_env() -> bool:
    """Kill switch: BIOMETRICS_ENABLED default off, enabled iff literal "1"
    (matches the repo's engine_config env convention)."""
    return os.environ.get("BIOMETRICS_ENABLED", "0") == "1"


def _authorized(auth_header: Optional[str], token: Optional[str]) -> bool:
    if not token:  # no token configured → deny all
        return False
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    presented = auth_header[len("Bearer "):]
    return hmac.compare_digest(presented, token)


def handle_request(
    *,
    enabled: bool,
    token: Optional[str],
    method: str,
    path: str,
    auth_header: Optional[str],
    body: bytes,
    store: BiometricStore,
) -> tuple[int, dict]:
    """Pure request core — no sockets. Returns (status, response_dict)."""
    route = path.split("?", 1)[0]
    if route != ROUTE:
        return 404, {"error": "not_found"}
    if not enabled:
        # Kill switch off: the feature is absent (404, no existence leak).
        return 404, {"error": "not_found"}
    if method != "POST":
        return 405, {"error": "method_not_allowed"}
    if not _authorized(auth_header, token):
        return 401, {"error": "unauthorized"}
    try:
        raw = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 422, {"error": "invalid_json"}
    try:
        prior = BiometricPrior.model_validate(payload)
    except ValidationError as exc:
        return 422, {
            "error": "validation_error",
            "detail": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()],
        }
    created = store.upsert(prior)
    return (201 if created else 200), {"date": prior.calendar_date, "created": created}


class BioHandler(BaseHTTPRequestHandler):
    server_version = "HarloBio/1"

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        status, resp = handle_request(
            enabled=self.server.enabled,  # type: ignore[attr-defined]
            token=self.server.token,  # type: ignore[attr-defined]
            method="POST",
            path=self.path,
            auth_header=self.headers.get("Authorization"),
            body=body,
            store=self.server.store,  # type: ignore[attr-defined]
        )
        self._send(status, resp)

    def _send(self, status: int, resp: dict) -> None:
        data = json.dumps(resp).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:  # quiet — no stderr access logging
        pass


class BioServer(HTTPServer):
    # Single-threaded on purpose: a ~1/day endpoint whose store holds a
    # thread-bound SQLite connection. No per-request threads → no cross-thread
    # connection use.
    allow_reuse_address = True

    def __init__(self, server_address, *, enabled: bool, token: Optional[str],
                 store: BiometricStore) -> None:
        super().__init__(server_address, BioHandler)
        self.enabled = enabled
        self.token = token
        self.store = store


def make_server(port: int = DEFAULT_PORT, *, enabled: Optional[bool] = None,
                token: Optional[str] = None,
                store: Optional[BiometricStore] = None) -> BioServer:
    return BioServer(
        ("127.0.0.1", port),
        enabled=enabled_from_env() if enabled is None else enabled,
        token=os.environ.get("HARLO_BIO_TOKEN") if token is None else token,
        store=InMemoryStore() if store is None else store,
    )


def run() -> None:
    from .persistence import default_store

    port = int(os.environ.get("HARLO_BIO_PORT", str(DEFAULT_PORT)))
    srv = make_server(port, store=default_store())
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    run()
