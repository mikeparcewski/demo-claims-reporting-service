# Claims Reporting Service (DEMO-CRS)

> **Fictional application.** Part of the migration-console reference estate. All hosts, people
> and data are synthetic. `corp.test` is a reserved test domain.

The Claims Reporting Service produces claims summary reports for the claims analytics team. It
serves a small HTTP API and monitors the health of the systems it depends on.

## Layout

| Path | What |
|---|---|
| `app/crs_service/` | The service (Python 3.12, standard library only) |
| `config/application.yaml` | Runtime configuration: listen port, dependencies, probe interval |
| `Dockerfile` | Container image for the service |
| `ops/batch/` | Batch jobs installed on the shared batch host (see below) |
| `tests/` | Unit tests (`PYTHONPATH=app python3 -m unittest discover tests`) |

## Runtime dependencies (`config/application.yaml`)

| Dependency | Endpoint | Use |
|---|---|---|
| database | `crs-db:5432` | PostgreSQL reporting database |
| cache | `crs-cache:6379` | Redis report cache |
| identity | `idp.corp.test:443` | Corporate OIDC sign-on |
| mail | `smtp-relay.corp.test:25` | Report notification mail |

The service probes each dependency every 30 seconds (`monitoring.dependency_probe_interval_seconds`).

## API

| Route | Response |
|---|---|
| `GET /health` | Dependency health; 200 when all ok, 503 when any is down |
| `GET /api/v1/reports/claims-summary?date=YYYY-MM-DD` | Claims summary by line of business and status |

Run locally: `PYTHONPATH=app python3 -m crs_service` (listens on 8080).

## Batch jobs

Jobs that run on the shared batch host live in `ops/batch/` (see `ops/batch/README.md`).

In the reference estate the database, cache, identity provider and mail relay are protocol stubs:
they accept connections and answer the health probes, nothing more.
