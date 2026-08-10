# Operations

Runbook for deploying, monitoring, and recovering the Home Manager stack. See
`ARCHITECTURE.md` for how the system is put together.

## Deployment

The stack is a single `docker-compose.yml`: `postgres`, `backend`, `nginx`. All three
containers run `read_only` filesystems (except explicit tmpfs/volume mounts),
`no-new-privileges`, and per-service CPU/memory limits.

For local/dev use, `nginx` is published on `127.0.0.1:8080` — loopback only. For a
real deployment (reachable from the internet), put a TLS-terminating reverse proxy
(e.g. Caddy, or nginx with certbot) in front of it:

- Terminate TLS there; proxy plaintext HTTP to `127.0.0.1:8080`.
- Enable HSTS at that layer — `frontend/nginx.conf` deliberately does *not* send
  `Strict-Transport-Security` itself, since it only ever speaks plain HTTP on the
  loopback interface and doesn't know whether the layer in front of it is TLS.
- Set `CORS_ALLOWED_ORIGINS` in `.env` to the real public origin (not
  `http://localhost:5173`).

### Environment variables

See `.env.example` for the full list with defaults. Required with no default:
`POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`. Everything else (AI provider, web
push, smart home provider) is optional and disables the corresponding feature
(falls back to `mock`/no-op) when unset.

## Logging

The backend logs structured JSON, one object per line, to stdout — no separate
logging stack (no ELK/Loki) is bundled; forward container stdout to whatever log
aggregator the deployment already has (`docker compose logs`, journald, etc.).

Two loggers matter operationally:

- `home_manager.access` — one line per request: `method`, `path`, `status_code`,
  `duration_ms`, `request_id`, `client_ip`.
- `home_manager.errors` — unhandled exceptions, with `exc_info` (stack trace) and the
  same `request_id`, at `ERROR` level.

Every response carries an `X-Request-ID` header (client-supplied if present,
otherwise generated) that also appears in the JSON error envelope and in these log
lines — use it to correlate a user-reported error with the corresponding log entry.

```bash
docker compose logs -f backend | jq 'select(.level=="ERROR")'
```

## Health checks

- `GET /api/v1/health/live` — process is up. Used by the container `HEALTHCHECK`.
- `GET /api/v1/health/ready` — process is up *and* the database is reachable
  (`SELECT 1`). Use this for readiness probes / load-balancer health checks.
- `GET /health/edge` on nginx (port 8080) — nginx itself is serving traffic,
  independent of the backend.

## Rate limiting

Defense in depth at two layers:

- **nginx** (`frontend/nginx.conf`): `limit_req` on `/api/*`, 10 req/s per client IP
  with a burst of 20 — caps abusive/scripted traffic before it reaches the backend.
- **Backend** (`auth/rate_limit.py`): a stricter, endpoint-specific throttle on login
  (5 attempts / 5 minutes per IP+email) — in-memory, single-process only. If the
  backend is ever scaled to more than one instance, this needs to move to shared
  state (Postgres or Redis) to stay effective.

## Backups

`scripts/backup_db.sh` runs `pg_dump` inside the running `postgres` container and
writes a gzipped SQL dump to `./backups/` (gitignored):

```bash
./scripts/backup_db.sh                 # ./backups/home_manager_<timestamp>.sql.gz
./scripts/backup_db.sh /path/to/dir    # custom output directory
```

Schedule it with cron for unattended backups, e.g. nightly at 03:00, keeping the
last 14 days:

```cron
0 3 * * * cd /path/to/home_manager && ./scripts/backup_db.sh && find backups -mtime +14 -delete
```

### Restore

`scripts/restore_db.sh` is destructive — it drops and recreates the target database
before loading the dump. It prompts for confirmation before doing so:

```bash
./scripts/restore_db.sh backups/home_manager_20260810T030000Z.sql.gz
```

Run this against a *new* environment (e.g. a freshly restored host) before pointing
real traffic at it, and always verify `alembic upgrade head` afterwards matches the
schema the dump was taken from — a restore is not a substitute for keeping migrations
in sync with what's actually in the dump.

## Container vulnerability scanning

CI (`docker-build` job in `.github/workflows/ci.yml`) builds both images and scans
them with Trivy on every PR, failing the build on any CRITICAL/HIGH vulnerability
with a known fix. Dependabot keeps base images and dependencies patched
(`.github/dependabot.yml`); review and merge its PRs regularly rather than letting
them queue up.
