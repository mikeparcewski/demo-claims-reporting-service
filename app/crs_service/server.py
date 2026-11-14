"""HTTP API for the Claims Reporting Service.

Routes:
  GET /health                               dependency health (200 when all ok, 503 otherwise)
  GET /api/v1/reports/claims-summary?date=  claims summary for a business date (JSON)
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import __version__
from .reports import claims_summary

log = logging.getLogger("crs.http")


def make_handler(config, monitor):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"crs-service/{__version__}"

        def log_message(self, fmt, *args):  # route access logs through logging
            log.info("%s %s", self.client_address[0], fmt % args)

        def _send(self, status: int, body: dict) -> None:
            payload = json.dumps(body, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):  # noqa: N802 (http.server naming)
            url = urlparse(self.path)
            if url.path == "/health":
                results = monitor.snapshot()
                healthy = bool(results) and all(r.ok for r in results)
                self._send(200 if healthy else 503, {
                    "service": config.name,
                    "version": __version__,
                    "status": "ok" if healthy else "degraded",
                    "dependencies": [asdict(r) for r in results],
                })
                return
            if url.path == "/api/v1/reports/claims-summary":
                raw = parse_qs(url.query).get("date", [None])[0]
                try:
                    business_date = date.fromisoformat(raw) if raw else datetime.now(timezone.utc).date()
                except ValueError:
                    self._send(400, {"error": "date must be YYYY-MM-DD"})
                    return
                self._send(200, {"business_date": business_date.isoformat(),
                                 "rows": claims_summary(business_date)})
                return
            self._send(404, {"error": "not found"})

    return Handler


def serve(config, monitor) -> None:
    httpd = ThreadingHTTPServer(("0.0.0.0", config.listen_port), make_handler(config, monitor))
    log.info("listening on :%d", config.listen_port)
    httpd.serve_forever()
