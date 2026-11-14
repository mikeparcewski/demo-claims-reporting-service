# ops/batch: nightly partner transfer

> Fictional. Part of the migration-console reference estate.

| File | What |
|---|---|
| `crontab` | System crontab entry: `15 2 * * *` as service account `svc_rptxfer` on the shared batch host `batch01` |
| `partner_transfer.py` | Builds `claims_daily_<YYYYMMDD>.csv` for the prior business day and uploads it to Northwind Clearinghouse |
| `transfer.env` | Partner endpoint (`partner-gw.northwind-clearing.test:443`), account, file prefix, spool directory |

Northwind's cut-off for the daily file is **06:00 America/New_York**. The partner answers each upload
with a receipt: `accepted` with an `ack_id`, or `rejected` with a reason (for example, a source IP that
is not on its allowlist). `partner_transfer.py --check` sends a small test file to verify connectivity
and allowlisting without sending claims data.

In the reference estate the reporting database is a protocol stub, so the extract rows are generated
deterministically from the business date, and the gateway speaks plain HTTP on port 443 (no TLS).
