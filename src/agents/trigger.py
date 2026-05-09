"""HTTP trigger server — manually fire a scoring cycle from anywhere.

Runs in a background thread alongside the APScheduler in monitor.py.

Endpoints:
    GET  /health          — liveness check, returns {"status": "ok"}
    POST /run?token=TOKEN — fires run_daily_cycle() in a background thread

Set TRIGGER_SECRET env var to protect the /run endpoint.
"""

from __future__ import annotations

import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

_running = False


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        logger.info("trigger: %s", format % args)

    def _send(self, status: int, body: str) -> None:
        encoded = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            self._send(200, '{"status":"ok"}')
        else:
            self._send(404, '{"error":"not found"}')

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/run":
            self._send(404, '{"error":"not found"}')
            return

        secret = os.getenv("TRIGGER_SECRET", "")
        if secret:
            token = parse_qs(parsed.query).get("token", [""])[0]
            if token != secret:
                self._send(401, '{"error":"unauthorized"}')
                return

        global _running
        if _running:
            self._send(409, '{"error":"cycle already running"}')
            return

        def _run() -> None:
            global _running
            _running = True
            try:
                from src.agents.monitor import run_daily_cycle
                run_daily_cycle()
            finally:
                _running = False

        threading.Thread(target=_run, daemon=True).start()
        self._send(202, '{"status":"cycle started"}')


def start_trigger_server(port: int | None = None) -> None:
    """Start the trigger HTTP server in a daemon thread."""
    p = port or int(os.getenv("TRIGGER_PORT", "8080"))
    server = HTTPServer(("0.0.0.0", p), _Handler)  # noqa: S104

    def _serve() -> None:
        logger.info("trigger: listening on port %d", p)
        server.serve_forever()

    threading.Thread(target=_serve, daemon=True).start()
