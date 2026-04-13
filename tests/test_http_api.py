import json
from http.client import HTTPConnection
from threading import Thread

from multica_quant_ops.api.http import build_http_server


def build_sample_payload(now: str = "2026-04-13T09:35:00") -> dict[str, object]:
    return {
        "symbol": "AAPL",
        "now": now,
        "snapshot": {
            "symbol": "AAPL",
            "as_of": "2026-04-13T09:34:00",
            "open_price": 200.0,
            "high_price": 202.0,
            "low_price": 199.0,
            "close_price": 201.0,
            "volume": 1000,
        },
        "quality_check": {
            "max_age_minutes": 5,
        },
        "signal_prices": [100.0, 101.0, 103.0],
        "backtest_prices": [100.0, 101.0, 103.0, 104.0, 106.0],
        "backtest_criteria": {
            "min_total_return": 0.01,
            "min_win_rate": 0.5,
        },
        "quantity": 2,
    }


def send_request(
    port: int,
    method: str,
    path: str,
    body: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object]]:
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        return response.status, payload
    finally:
        connection.close()


def test_http_healthcheck_returns_ok() -> None:
    server = build_http_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status_code, payload = send_request(server.server_port, "GET", "/health")

        assert status_code == 200
        assert payload == {"status": "ok", "service": "multica-quant-ops"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_daily_workflow_returns_structured_json() -> None:
    server = build_http_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status_code, payload = send_request(
            server.server_port,
            "POST",
            "/workflows/daily",
            body=json.dumps(build_sample_payload()),
            headers={"Content-Type": "application/json"},
        )

        assert status_code == 200
        assert payload["result"]["blocked_stage"] is None
        assert payload["result"]["paper_order"]["side"] == "buy"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_daily_workflow_returns_validation_error() -> None:
    server = build_http_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status_code, payload = send_request(
            server.server_port,
            "POST",
            "/workflows/daily",
            body=json.dumps({"symbol": "AAPL"}),
            headers={"Content-Type": "application/json"},
        )

        assert status_code == 400
        assert "Invalid request payload" in payload["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_unknown_route_returns_not_found() -> None:
    server = build_http_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status_code, payload = send_request(server.server_port, "GET", "/missing")

        assert status_code == 404
        assert payload["error"] == "Not found"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
