"""Configuration loading for the Claims Reporting Service.

The service ships without third-party dependencies, so this module reads the
small YAML subset that ``config/application.yaml`` uses: nested mappings by
two-space indentation, ``key: value`` scalars and ``#`` comments.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "application.yaml",
)


def _scalar(raw: str) -> Any:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def parse_yaml_subset(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.split(" #", 1)[0].rstrip() if not line.lstrip().startswith("#") else ""
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        key, sep, rest = stripped.strip().partition(":")
        if not sep:
            raise ValueError(f"application.yaml line {lineno}: expected 'key: value'")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if rest.strip() == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(rest)
    return root


@dataclass(frozen=True)
class Dependency:
    name: str
    kind: str
    host: str
    port: int

    @property
    def target(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    code: str
    listen_port: int
    dependencies: tuple[Dependency, ...]
    probe_interval_seconds: int
    probe_timeout_seconds: float
    raw: dict


def load_config(path: str | None = None) -> ServiceConfig:
    path = path or os.environ.get("CRS_CONFIG", DEFAULT_CONFIG_PATH)
    with open(path, encoding="utf-8") as handle:
        raw = parse_yaml_subset(handle.read())
    deps = tuple(
        Dependency(name=name, kind=str(spec["kind"]), host=str(spec["host"]), port=int(spec["port"]))
        for name, spec in raw.get("dependencies", {}).items()
    )
    monitoring = raw.get("monitoring", {})
    service = raw["service"]
    return ServiceConfig(
        name=service["name"],
        code=service["code"],
        listen_port=int(service.get("listen_port", 8080)),
        dependencies=deps,
        probe_interval_seconds=int(monitoring.get("dependency_probe_interval_seconds", 30)),
        probe_timeout_seconds=float(monitoring.get("probe_timeout_seconds", 3)),
        raw=raw,
    )
