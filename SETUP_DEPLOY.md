# Local setup, testing and deployment

## 0. Prerequisites

- Git, Docker Desktop with Compose V2, and a terminal. On macOS install Docker Desktop and start the Docker engine.
- For running without containers: Node.js 22+, npm, Python 3.12+, PostgreSQL 16+, Redis 7+.
- A GitHub account and Railway account (or another Docker-compatible host) if you need the deployed URL.

Repo layout:

```text
bike-auction-platform/
├── apps/
│   ├── api/
│   │   ├── app/{routers/,config.py,db.py,models.py,schemas.py,security.py,worker.py,seed.py}
│   │   ├── alembic/{env.py,versions/0001_init.py}
│   │   ├── tests/
│   │   ├── Dockerfile, requirements.txt, alembic.ini
│   └── web/
│       ├── app/{page.tsx,auctions/[id]/page.tsx,admin/,login/,register/,api/,runtime-config/}
│       ├── components/, lib/, Dockerfile, package.json
├── docs/{ARCHITECTURE.md,SETUP_DEPLOY.md}
├── .github/workflows/ci.yml
├── compose.yaml
├── .env.example
└── README.md
```

## 1. Run locally in Docker

```bash
# Run from repo root
cp .env.example .env
# Edit .env if needed. Sample settings are for LOCAL DEVELOPMENT ONLY.
docker compose up --build -d
docker compose ps

# IMPORTANT: schema migrations are intentionally a separate step
docker compose exec api alembic upgrade head

# Idempotent sample content plus development admin (reads env vars)
docker compose exec api python -m app.seed

# Verify dependencies and view logs
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/readyz
docker compose logs -f api worker web
```

Open <http://localhost:3000>. Seeded admin credentials are sourced from the **local** `.env` (`ADMIN_EMAIL`, `ADMIN_PASSWORD`). Sign in, go to **Admin studio**, and publish at least one draft auction. Sign out, register another email as a buyer, and bid on a live auction. 

For container cleanup without losing DB: `docker compose down`. For total reset (DELETES your local data): `docker compose down -v`.

## 2. Exercise the product end to end

1. Open the buyer landing page; inspect status filters, live bids, and no-results states.
2. Log in as the seeded admin and publish a `draft`. A start time in the past goes immediately `active` if end time is still in the future; otherwise publishing rejects the listing. Future drafts become `scheduled`.
3. Register two buyers in separate browser profiles. Submit a bid equal to the starting price from buyer A, then an incremented bid from buyer B. Both screens should update via WebSockets or the 10-second recovery poll.
4. From admin, close the auction; the detail screen should stop accepting bids.
5. Create another auction starting in about a minute, publish it, and watch the background worker automatically activate it. To test expiry, choose a short start/end interval for a new test listing.
6. Confirm that no real payment, purchase, physical bike transfer, or contact workflow occurs. This is an engineering demonstration.

## 3. Run tests

Quick Python unit tests (no PostgreSQL needed):

```bash
docker compose exec api pytest -q tests/test_logic.py
```

Integration tests require an **isolated database explicitly named** `auction_test`; they reset its tables. Do NOT target the standard `auction` DB, any production DB, or a shared database.

```bash
# Create a dedicated test DB in Docker. Only run once (ignore 'already exists').
docker compose exec db createdb -U auction auction_test

# Run tests from a short-lived API container configured for auction_test.
# Existing production/local app services remain pointed at the regular auction DB.
docker compose run --rm \
  -e DATABASE_URL=postgresql+asyncpg://auction:local_dev_only@db:5432/auction_test \
  -e TEST_DATABASE_URL=postgresql+asyncpg://auction:local_dev_only@db:5432/auction_test \
  api pytest -q
```

GitHub Actions CI also runs `alembic upgrade head`, backend tests with PostgreSQL and Redis services, TypeScript typecheck and Next.js build. It is intentionally normal that integration tests skip when `TEST_DATABASE_URL` is not specified.

## 4. Local development without rebuilding containers

Start dependencies only: `docker compose up -d db redis`. Set the following from repo root or a shell profile:

```bash
export DATABASE_URL='postgresql+asyncpg://auction:local_dev_only@localhost:5432/auction'
export REDIS_URL='redis://localhost:6379/0'
export APP_SECRET='local_example_secret_change_me_to_something_unique_012345'
export METRICS_TOKEN='local_metrics_token_123'
export WEB_ORIGIN='http://localhost:3000'
export COOKIE_SECURE='false'
export API_BACKEND_URL='http://localhost:8000'
export PUBLIC_WS_URL='ws://localhost:8000'

cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# In second terminal within apps/api: python -m app.worker

# In a third terminal
cd apps/web
npm install
npm run dev
```

When running the seed locally, supply `ADMIN_EMAIL` and `ADMIN_PASSWORD`, then run `python -m app.seed` inside `apps/api`. In Docker, `api` and `worker` run as separate processes; do not start a background scheduler inside every FastAPI replica.

## 5. Deploy to Railway (GitHub-connected monorepo)

 **Create Railway project and add services:**

1. Create an empty Railway project. Add PostgreSQL and Redis managed services (name them `Postgres`, `Redis`).
2. Add **API** service from GitHub, root directory `/apps/api`, using its Dockerfile; set service's listen/public port to **8000** (`PORT=8000`). Generate a public domain. Health check path `/readyz` after applying migrations.
3. Add **worker** service from the same GitHub repo, root directory `/apps/api`, using the same Dockerfile. Override its **start command** to `python -m app.worker`. No public domain. It must have the same database, Redis, and application config as API. Use one replica initially.
4. Add **web** service from the same repo, root directory `/apps/web`, using its Dockerfile; set `PORT=3000`, generate a public domain. Its API proxy runs in the Next.js Node server.
5. Enable private networking for services; use Railway's internal service hostname, e.g. `api.railway.internal`, or your actual generated private hostname. Refer to the Railway Networking page in the provider dashboard. Public API domain is **only required for browser WebSockets**; browser REST requests use the web proxy.

**Step C — Configure variables:**

| Service | Variable | Set to |
|---|---|---|
| API + worker | `APP_ENV` | `production` |
| API + worker | `DATABASE_URL` | Reference the managed Postgres `DATABASE_URL` (native `postgresql://` is normalized automatically) |
| API + worker | `REDIS_URL` | Reference managed Redis `REDIS_URL` |
| API + worker | `APP_SECRET` | Strong unique 32+ character random value (e.g. `openssl rand -hex 32`) |
| API + worker | `METRICS_TOKEN` | New random token (e.g. `openssl rand -hex 24`) |
| API + worker | `WEB_ORIGIN` | `https://YOUR_WEB_DOMAIN` exact scheme and host, no trailing slash |
| API + worker | `COOKIE_SECURE` | `true` |
| API + worker | `SENTRY_DSN` | Optional server-side Sentry DSN |
| API only | `PORT` | `8000` |
| Worker only | Start command | `python -m app.worker` |
| Web | `PORT` | `3000` |
| Web | `API_BACKEND_URL` | Private API address, e.g. `http://api.railway.internal:8000` |
| Web | `PUBLIC_WS_URL` | `wss://YOUR_API_PUBLIC_DOMAIN` (no trailing slash) |



**Apply migrations once BEFORE serving requests:**

- Railway provides remote service execution/one-off jobs depending on your plan and interface. Use a **one-off task** using the API image with environment variables set, command `alembic upgrade head`, working directory `/srv`.
- Alternatively, securely run `alembic upgrade head` from a machine with connectivity to the managed PostgreSQL endpoint by setting `DATABASE_URL` to the provider's public DB URL; restrict exposure/access as appropriate.
- Only after successful migration, start API and worker replicas. Never run migrations automatically in every horizontally scaled API container; backup DB before destructive migrations.
- Once API `/readyz` is healthy, deploy/redeploy the web service.
