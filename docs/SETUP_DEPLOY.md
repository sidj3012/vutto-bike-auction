# Vutto — local setup, testing and deployment (start to finish)

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

Open <http://localhost:3000>. Seeded admin credentials are sourced from the **local** `.env` (`ADMIN_EMAIL`, `ADMIN_PASSWORD`). Sign in, go to **Admin studio**, and publish at least one draft auction. Sign out, register another email as a buyer, and bid on a live auction. You can use an incognito browser profile for the second user. The example bikes' start dates are generated relative to **when the seed command runs**, not hardcoded to a calendar year.

> Demo admin credentials in `.env.example` are intentionally obvious and **must not be used online**. Do not commit `.env`; `.gitignore` excludes it. The seed command does not rotate an existing admin's password.

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

Integration tests require an **isolated database explicitly named `auction_test`**; they reset its tables. Do NOT target the standard `auction` DB, any production DB, or a shared database.

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

These steps require your Railway account. They do **not** constitute a live deployment from this repository export. Railway supports Dockerfiles, multiple monorepo services, private networking, and public domains; some dashboard control names may change.

**Step A — Push source to GitHub:**

```bash
# After extracting source ZIP:
git init
git add .
git commit -m "Vutto implementation"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

**To preserve the original 5-commit history instead**, use the separate `bike-auction-history.bundle` file: `git clone bike-auction-history.bundle bike-auction-platform && cd bike-auction-platform`, then add your GitHub remote and push the checked-out branch. Use either path, not both.

**Step B — Create Railway project and add services:**

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

**Crucial:** `WEB_ORIGIN` is the public **web** address, not the API address. Keep all application secrets in Railway variables, not in Git. The web service's `API_BACKEND_URL` remains private; `PUBLIC_WS_URL` is deliberately public. The browser connects to `/ws/auctions/{uuid}` on the public API domain.

**Step D — Apply migrations once BEFORE serving requests:**

- Railway provides remote service execution/one-off jobs depending on your plan and interface. Use a **one-off task** using the API image with environment variables set, command `alembic upgrade head`, working directory `/srv`.
- Alternatively, securely run `alembic upgrade head` from a machine with connectivity to the managed PostgreSQL endpoint by setting `DATABASE_URL` to the provider's public DB URL; restrict exposure/access as appropriate.
- Only after successful migration, start API and worker replicas. Never run migrations automatically in every horizontally scaled API container; backup DB before destructive migrations.
- Once API `/readyz` is healthy, deploy/redeploy the web service.

**Step E — Prepare secure demo credentials and content:**

- Temporarily set secret variables `ADMIN_EMAIL=your-demo-admin@example.com` and `ADMIN_PASSWORD=<a unique strong 16+ char password>` for a one-off job using the **API image**, then run `python -m app.seed`. Remove the password variable from the long-lived service environment after seeding if you do not need it later.
- Log in at `https://YOUR_WEB_DOMAIN/login` with your seeded admin, open `/admin`, and publish demo auction drafts. Create a separate buyer via `/register`. Never publish the admin credentials publicly unless they are a dedicated throwaway demo account without access to anything sensitive.
- If reviewers need credentials, provide a throwaway buyer login and an isolated demo admin login in your submission notes. Use no personal passwords.

**Step F — Verify externally:**

```bash
curl -fsS https://YOUR_API_PUBLIC_DOMAIN/healthz
curl -fsS https://YOUR_API_PUBLIC_DOMAIN/readyz
curl -I https://YOUR_WEB_DOMAIN/
# The API OpenAPI schema is available at https://YOUR_API_PUBLIC_DOMAIN/openapi.json
```

Then test login cookie persistence, two concurrent buyers, live websocket events, auction expiry, and restart recovery in the deployed environment. Check browser developer tools for the WS handshake (101 Switching Protocols), websocket `Origin`, and no mixed HTTP content. Test on mobile width.

**Railway troubleshooting:** If the browser sees `502 Backend unavailable`, check `API_BACKEND_URL` and private DNS/port. If bids work but real-time is offline, check `PUBLIC_WS_URL`, API's public domain and allowed `WEB_ORIGIN`. If all unsafe requests return 403, verify exact `WEB_ORIGIN` and reverse-proxy forwarding of the browser `Origin` header. If auth returns 401 after login, confirm `Set-Cookie` on the web origin, HTTPS, and Redis health. If auctions don't transition, inspect the **worker** logs and its database permissions.

## 6. Observability checks and operational playbook

```bash
curl -H 'X-Metrics-Token: local_metrics_secret' http://localhost:8000/metrics
# Note: this example token is from LOCAL .env.example, never use online.
docker compose logs -f worker api
```

A production metrics collector should scrape the API over a private network with a protected header. Configure alerts for high bid response latency, worker crashes, older unpublished outbox events, and auctions remaining `active` beyond their end time. Never expose `/metrics` or PostgreSQL publicly without network restrictions and authentication. See `docs/ARCHITECTURE.md` for sample SQL and monitoring thresholds.

**If API fails:** readiness fails, restart and inspect logs; committed bids remain in PostgreSQL. **If Redis fails:** read-only browsing may continue, session auth and notifications fail closed; repair Redis and monitor backlog in `outbox_events`. **If worker fails:** bidding still rejects expired auctions, but status changes and notifications lag until recovery. **If DB fails:** stop attempting client-side retries without idempotency keys; after recovery replay the *same* idempotency key for an uncertain bid response. **If persistent data is lost:** restore the managed PostgreSQL backup and validate consistency before reopening auctions.

## 7. Five logical commits and what to review

| Commit | Phase | Technical focus | Review checkpoints |
|---|---|---|---|
| 1 | Foundation | Docker Compose, schema, migrations, Python contracts | DB constraints, DB types, storage |
| 2 | API core | Registration/login, catalogue, role-restricted admin APIs | Cookies, authorization, status transitions |
| 3 | Auction engine | Locked bid writes, idempotency, outbox, worker, WebSockets | Simultaneous bids, clock boundary, retry |
| 4 | Product UX | Landing catalogue, auction room, admin studio, responsive styling | Loading/errors, accessibility, mobile |
| 5 | Verification/ops | Unit and integration tests, CI, hardening, deployment documentation | Tests, secrets, failure/recovery |

To see actual commits in the supplied Git bundle: `git log --oneline --reverse`. To review changes: `git show <commit>`; to run each stage: `git checkout <commit>` (earlier stages are **review checkpoints**, not individually deployable releases).

## 8. Hand-in checklist

- [ ] Real GitHub repository with five meaningful commits (use bundle if preserving history)
- [ ] Public web URL opening without errors
- [ ] Buyer demo login and **separate** protected admin demo login supplied privately
- [ ] Source code and `README.md`
- [ ] Architecture document and tradeoffs
- [ ] Local setup and Railway deployment guide
- [ ] CI green: Python tests, real PostgreSQL contention, TypeScript/build
- [ ] WebSocket connection and worker verified on hosting
- [ ] Replaced all sample secrets; `.env` absent from Git
- [ ] Screen recording optional, shows concurrent bids and timer-driven closure

## 9. References

- [Next.js route handlers](https://nextjs.org/docs/app/getting-started/route-handlers)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [PostgreSQL locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Railway monorepo deployments](https://docs.railway.com/deployments/monorepo)
- [Railway start commands](https://docs.railway.com/deployments/start-command)
