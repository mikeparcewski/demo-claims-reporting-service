#!/usr/bin/env python3
"""Nightly claims file transfer to Northwind Clearinghouse.

Builds ``claims_daily_<YYYYMMDD>.csv`` for the prior business day, writes it to
the outbound spool and uploads it to the partner gateway. The partner answers
each upload with a receipt: ``accepted`` with an ``ack_id``, or ``rejected``
with a reason (for example, a source address that is not on its allowlist).

Usage:
  partner_transfer.py --env transfer.env            # build + send the daily file
  partner_transfer.py --env transfer.env --check    # connectivity check: send a
                                                    # small test file, report result

Every step logs one JSON line to stdout. The final line carries
``target``, ``file``, ``bytes`` and the partner's answer.

Exit codes: 0 accepted, 3 rejected by partner, 4 transport error, 2 bad config.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import random
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

REQUIRED_KEYS = ("PARTNER_URL", "PARTNER_ACCOUNT", "FILE_PREFIX", "OUTBOUND_DIR")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def log(event: str, **fields) -> None:
    print(json.dumps({"ts": now_iso(), "event": event, **fields}), flush=True)


def load_env(path: str) -> dict:
    settings: dict = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            settings[key.strip()] = value.strip().strip('"').strip("'")
    missing = [k for k in REQUIRED_KEYS if not settings.get(k)]
    if missing:
        raise SystemExit(f"transfer.env missing {', '.join(missing)}")
    return settings


def target_of(url: str) -> str:
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return f"{parsed.hostname}:{port}"


def prior_business_date(tz_name: str) -> date:
    local_now = datetime.now(ZoneInfo(tz_name))
    return (local_now - timedelta(days=1)).date()


def build_daily_extract(business_date: date) -> bytes:
    """Rows of the daily claims extract.

    Production reads ``reporting.v_claims_daily``. In the reference estate the
    database is a protocol stub, so rows are generated deterministically from
    the business date (synthetic data, no real members or providers).
    """
    rng = random.Random(business_date.toordinal())
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["claim_id", "member_ref", "provider_ref", "service_date",
                     "status", "billed_amount", "paid_amount"])
    for n in range(1, 251):
        billed = round(rng.uniform(80, 4200), 2)
        status = rng.choice(("PAID", "PAID", "PAID", "PENDED", "DENIED"))
        paid = round(billed * rng.uniform(0.55, 0.95), 2) if status == "PAID" else 0.0
        writer.writerow([
            f"CLM-{business_date:%Y%m%d}-{n:05d}",
            f"MBR-{rng.randint(100000, 999999)}",
            f"PRV-{rng.randint(1000, 9999)}",
            (business_date - timedelta(days=rng.randint(0, 20))).isoformat(),
            status, f"{billed:.2f}", f"{paid:.2f}",
        ])
    return out.getvalue().encode("utf-8")


def upload(settings: dict, filename: str, body: bytes, test: bool) -> tuple[int, dict]:
    request = urllib.request.Request(
        settings["PARTNER_URL"],
        data=body,
        method="POST",
        headers={
            "Content-Type": "text/csv",
            "X-Filename": filename,
            "X-Partner-Account": settings["PARTNER_ACCOUNT"],
            "X-Test-Upload": "true" if test else "false",
        },
    )
    timeout = float(settings.get("PARTNER_TIMEOUT_SECONDS", 30))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as err:
        try:
            payload = json.loads(err.read() or b"{}")
        except ValueError:
            payload = {}
        return err.code, payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", required=True, help="path to transfer.env")
    parser.add_argument("--check", action="store_true", help="send a small test file only")
    args = parser.parse_args(argv)

    try:
        settings = load_env(args.env)
    except (OSError, SystemExit) as exc:
        log("config_error", detail=str(exc))
        return 2

    target = target_of(settings["PARTNER_URL"])
    if args.check:
        filename = f"connectivity_check_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.csv"
        body = b"check\nok\n"
    else:
        business_date = prior_business_date(settings.get("BUSINESS_TIMEZONE", "America/New_York"))
        filename = f"{settings['FILE_PREFIX']}{business_date:%Y%m%d}.csv"
        body = build_daily_extract(business_date)
        os.makedirs(settings["OUTBOUND_DIR"], exist_ok=True)
        with open(os.path.join(settings["OUTBOUND_DIR"], filename), "wb") as handle:
            handle.write(body)
        log("extract_written", file=filename, bytes=len(body), business_date=business_date.isoformat())

    log("upload_started", target=target, file=filename, bytes=len(body), test=args.check)
    try:
        status, receipt = upload(settings, filename, body, test=args.check)
    except OSError as exc:
        log("transfer_failed", target=target, file=filename, bytes=len(body),
            status="transport_error", detail=f"{type(exc).__name__}: {exc}")
        return 4

    result = {
        "target": target,
        "file": filename,
        "bytes": len(body),
        "http_status": status,
        "status": receipt.get("status", "unknown"),
        "reason": receipt.get("reason"),
        "ack_id": receipt.get("ack_id"),
        "test": args.check,
    }
    if status == 200 and receipt.get("status") == "accepted":
        log("transfer_accepted", **result)
        return 0
    log("transfer_rejected", **result)
    return 3


if __name__ == "__main__":
    sys.exit(main())
