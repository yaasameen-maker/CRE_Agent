"""HTTP trigger server — manually fire a scoring cycle from anywhere.

Runs in a background thread alongside the APScheduler in monitor.py.

Endpoints:
    GET  /health          — liveness check
    GET  /status          — {"running": bool, "last_run": str | null}
    GET  /digest          — SignalDigest JSON from Gold layer
    GET  /alerts          — ActionAlertPayload JSON derived from digest
    GET|POST /run?token=  — fires run_daily_cycle() in a background thread

Set TRIGGER_SECRET env var to protect the /run endpoint.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

_running = False
_last_run: str | None = None

_ZIP_META: dict[str, tuple[str, str, str]] = {
    "10001": ("New York", "NY", "Midtown"),
    "10014": ("New York", "NY", "West Village"),
    "10036": ("New York", "NY", "Times Square"),
    "10128": ("New York", "NY", "Upper East Side"),
    "11201": ("Brooklyn", "NY", "Brooklyn Heights"),
}


def _build_digest() -> dict:
    from src.pipeline._db import gold_get_full

    rows = gold_get_full()
    if not rows:
        return {}

    zips = []
    for row in rows:
        z = row["zip_code"]
        score = row["overall_score"]
        action = "Model" if score >= 70 else "Monitor" if score >= 40 else "Ignore"
        city, state, neighborhood = _ZIP_META.get(z, ("New York", "NY", ""))

        vac = round(float(row["vacancy_rate"] or 0), 2)
        rent = round(float(row["rent_change_pct"] or 0), 2)
        price = round(float(row["price_index_change"] or 0), 2)
        emp = round(float(row["unemployment_rate"] or 0), 2)
        emp_chg = round(float(row["unemployment_mom_change"] or 0), 2)
        fcl = int(row["foreclosure_count"] or 0)

        zips.append({
            "zip": z,
            "city": city,
            "state": state,
            "neighborhood": neighborhood,
            "distress_score": score,
            "rank": row["rank"],
            "action": action,
            "signals": {
                "vacancy":      {"value": vac,   "change_30d": 0,    "flag": row["rent_vacancy_score"] > 0},
                "rent":         {"value": rent,  "change_30d": rent, "flag": row["rent_vacancy_score"] > 0},
                "price_growth": {"value": price, "annualized": price, "flag": row["price_score"] > 0},
                "employment":   {"value": emp,   "change_30d": emp_chg, "flag": row["employment_score"] > 0},
                "foreclosure":  {"count": fcl,   "flag": row["foreclosure_score"] > 0},
            },
            "brief_id": z,
        })

    return {
        "generated_at": rows[0]["scored_at"],
        "run_id": "live",
        "zips": zips,
    }


def _build_alerts(digest: dict) -> dict:
    alerts = []
    for entry in digest.get("zips", []):
        action = entry["action"]
        if action not in ("Model", "Monitor"):
            continue
        flagged = [k for k, v in entry["signals"].items() if v.get("flag")]
        primary = flagged[0] if flagged else "employment"
        area = entry.get("neighborhood") or entry["city"]
        if action == "Model":
            msg = (
                f"ZIP {entry['zip']} ({area}) scores {entry['distress_score']}/100 — "
                "distress threshold exceeded. Recommend underwriting review."
            )
        else:
            msg = (
                f"ZIP {entry['zip']} ({area}) trending toward distress at "
                f"{entry['distress_score']}/100. Continue monitoring."
            )
        alerts.append({
            "zip": entry["zip"],
            "action": action,
            "distress_score": entry["distress_score"],
            "primary_signal": primary,
            "brief_id": entry["zip"],
            "message": msg,
        })
    return {"generated_at": digest.get("generated_at", datetime.now(UTC).isoformat()), "alerts": alerts}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        logger.info("trigger: %s", format % args)

    def _send(self, status: int, body: str) -> None:
        encoded = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send(200, '{"status":"ok"}')

        elif parsed.path == "/status":
            self._send(200, json.dumps({"running": _running, "last_run": _last_run}))

        elif parsed.path == "/digest":
            try:
                self._send(200, json.dumps(_build_digest()))
            except Exception as exc:
                logger.exception("digest endpoint failed")
                self._send(500, json.dumps({"error": str(exc)}))

        elif parsed.path == "/alerts":
            try:
                self._send(200, json.dumps(_build_alerts(_build_digest())))
            except Exception as exc:
                logger.exception("alerts endpoint failed")
                self._send(500, json.dumps({"error": str(exc)}))

        elif parsed.path == "/run":
            self.do_POST()

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
            global _running, _last_run
            _running = True
            try:
                from src.agents.monitor import run_daily_cycle
                run_daily_cycle()
                _last_run = datetime.now(UTC).isoformat()
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
