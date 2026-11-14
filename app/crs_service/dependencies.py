"""Dependency health probes.

Each probe opens a real TCP connection to the configured endpoint and, where the
protocol makes it cheap, exchanges a greeting (Redis PING, SMTP banner). Results
feed the ``/health`` endpoint.
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import Dependency

log = logging.getLogger("crs.dependencies")


@dataclass
class ProbeResult:
    dependency: str
    target: str
    ok: bool
    latency_ms: float
    detail: str
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _probe_postgres(sock: socket.socket) -> str:
    # A full startup handshake needs credentials; reachability is what /health reports.
    return "tcp connected"


def _probe_redis(sock: socket.socket) -> str:
    sock.sendall(b"PING\r\n")
    reply = sock.recv(64)
    if not reply.startswith(b"+PONG"):
        raise ConnectionError(f"unexpected PING reply {reply[:32]!r}")
    return "PONG"


def _probe_smtp(sock: socket.socket) -> str:
    banner = sock.recv(256)
    if not banner.startswith(b"220"):
        raise ConnectionError(f"unexpected SMTP banner {banner[:32]!r}")
    sock.sendall(b"QUIT\r\n")
    return banner.decode("ascii", "replace").strip()


def _probe_oidc(sock: socket.socket) -> str:
    return "tcp connected"


PROBES = {
    "postgres": _probe_postgres,
    "redis": _probe_redis,
    "smtp": _probe_smtp,
    "oidc": _probe_oidc,
}


def probe(dep: Dependency, timeout: float) -> ProbeResult:
    started = time.monotonic()
    try:
        with socket.create_connection((dep.host, dep.port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            detail = PROBES.get(dep.kind, _probe_oidc)(sock)
        ok = True
    except OSError as exc:
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    latency = round((time.monotonic() - started) * 1000, 1)
    return ProbeResult(dep.name, dep.target, ok, latency, detail)


class DependencyMonitor(threading.Thread):
    """Probes every dependency on a fixed interval and keeps the latest results."""

    def __init__(self, deps, interval: int, timeout: float):
        super().__init__(name="dependency-monitor", daemon=True)
        self._deps = deps
        self._interval = interval
        self._timeout = timeout
        self._lock = threading.Lock()
        self._latest: dict[str, ProbeResult] = {}

    def run(self) -> None:
        while True:
            for dep in self._deps:
                result = probe(dep, self._timeout)
                with self._lock:
                    self._latest[dep.name] = result
                level = logging.INFO if result.ok else logging.WARNING
                log.log(level, "probe %s %s ok=%s %.1fms %s",
                        dep.name, dep.target, result.ok, result.latency_ms, result.detail)
            time.sleep(self._interval)

    def snapshot(self) -> list[ProbeResult]:
        with self._lock:
            return list(self._latest.values())
