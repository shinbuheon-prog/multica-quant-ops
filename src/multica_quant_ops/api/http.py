import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from multica_quant_ops.api.service import WorkflowAPI
from multica_quant_ops.cli import build_default_workflow


class WorkflowHTTPRequestHandler(BaseHTTPRequestHandler):
    api: WorkflowAPI

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        status_code, payload = self.api.healthcheck()
        self.write_json(status_code, payload)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/workflows/daily":
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": "Missing Content-Length header"})
            return

        try:
            raw_body = self.rfile.read(int(content_length))
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON body: {exc}"})
            return

        status_code, response_payload = self.api.run_daily_workflow(payload)
        self.write_json(status_code, response_payload)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_http_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    handler = type(
        "ConfiguredWorkflowHTTPRequestHandler",
        (WorkflowHTTPRequestHandler,),
        {"api": WorkflowAPI(build_default_workflow())},
    )
    return ThreadingHTTPServer((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = build_http_server(host=host, port=port)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> int:
    serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
