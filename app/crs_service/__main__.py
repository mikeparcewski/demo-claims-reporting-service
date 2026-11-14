"""Entry point: ``python -m crs_service``."""

from __future__ import annotations

import logging
import os
import sys

from .config import load_config
from .dependencies import DependencyMonitor
from .server import serve


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("CRS_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    config = load_config()
    logging.getLogger("crs").info(
        "starting %s (%s) with %d dependencies: %s",
        config.name, config.code, len(config.dependencies),
        ", ".join(d.target for d in config.dependencies),
    )
    monitor = DependencyMonitor(config.dependencies, config.probe_interval_seconds,
                                config.probe_timeout_seconds)
    monitor.start()
    serve(config, monitor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
