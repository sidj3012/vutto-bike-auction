# Used Motorcycle Auction Platform

This is a full-stack auction app for used motorcycles. Buyers can browse listings and place bids while an administrator manages listings and auction status.

## What it includes

- Public auction listings and individual auction pages.
- Buyer registration and login, with cookie-based sessions.
- Bid submission with server-side validation and protection against simultaneous bids being accepted out of order for the same auction.
- Live auction updates over WebSockets, with periodic refresh as a fallback when a connection drops.
- Admin tools to create, publish, and close auctions.
- A background worker that activates scheduled auctions, closes expired auctions, and delivers queued events.
- Request logs, health/readiness endpoints,  metrics.
- Docker Compose for local development and GitHub Actions for automated checks.

## Tech stack

| Area | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript |
| Backend API | Python, FastAPI, Pydantic |
| Database | PostgreSQL 16, SQLAlchemy, Alembic |
| Sessions and event distribution | Redis |
| Live updates | WebSockets + Redis Pub/Sub |
| Background work | Separate Python worker |
| Tests and CI | pytest, GitHub Actions, TypeScript checks, Next.js build |
| Local environment | Docker Compose |

## Run it locally

### Requirements

Install Docker Desktop with Docker Compose, and make sure Docker is running. 

### 1. Configure environment variables

From the repository root:

```bash
cp .env.example .env
```

### 2. Start the services

```bash
docker compose up --build -d
docker compose ps
```

This starts the web app, FastAPI API, background worker, PostgreSQL, and Redis.

### 3. Create the database schema and demo data

Run the migration, then seed the local admin and sample auctions:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

The admin credentials come from `ADMIN_EMAIL` and `ADMIN_PASSWORD` in your local `.env`. 

### 4. Open the app

- Web app: <http://localhost:3000>
- API liveness: <http://localhost:8000/healthz>
- API readiness (checks PostgreSQL and Redis): <http://localhost:8000/readyz>
- Interactive API docs: <http://localhost:8000/docs>

If a page or request fails, check the service logs:

```bash
docker compose logs -f web api worker
```

Press `Ctrl+C` to stop following logs; this does not stop the containers.

To stop the services but keep local data:

```bash
docker compose down
```

To delete local data as well (destructive):

```bash
docker compose down -v
```

## How the architecture works

```text
Browser
  └── Next.js web app
        ├── Same-origin API proxy ──> FastAPI
        └── WebSocket connection ───> FastAPI
                                      ├── PostgreSQL
                                      └── Redis
                                            ▲
                               Background worker
```

- **Next.js** renders the buyer experience and admin dashboard. The same-origin API proxy keeps browser REST requests on the web origin and forwards them to FastAPI.
- **FastAPI** owns authentication, validation, authorization, auction state transitions, bid processing, and the WebSocket endpoint.
- **PostgreSQL is the source of truth.** Bid amounts are stored as integer paise rather than floating-point currency. A transaction locks the relevant auction row before validating and accepting a bid, so bids for one auction are serialized by the database.
- **Redis** stores revocable session state and distributes events between API instances. It is not the authority for the current price or winner.
- **The worker** processes scheduled starts, expired auctions, and pending outbox events. The outbox record is written with the bid transaction, so a committed bid can still be published after a temporary Redis/event-delivery failure.

See ARCHITECTURE.md for architecture design.  
See SETUP_DEPLOY.md for deployment setup

## Tests and checks

Run the backend unit tests in the API container:

```bash
docker compose exec api pytest -q tests/test_logic.py
```

The integration tests use a dedicated database named `auction_test` and can reset its tables. To create the test database and run the suite:

```bash
docker compose exec db createdb -U auction auction_test

docker compose run --rm \
  -e DATABASE_URL=postgresql+asyncpg://auction:local_dev_only@db:5432/auction_test \
  -e TEST_DATABASE_URL=postgresql+asyncpg://auction:local_dev_only@db:5432/auction_test \
  api pytest -q
```

Check the frontend types and production build locally:

```bash
cd apps/web
npm install
npm run lint
npm run build
```

The GitHub Actions workflow runs backend tests with PostgreSQL and Redis, then checks the frontend types and builds Next.js.

## API overview

The versioned REST API is under `/api/v1`.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Register a buyer |
| `POST` | `/auth/login` | Sign in |
| `POST` | `/auth/logout` | Sign out and revoke the session |
| `GET` | `/auth/me` | Get the current user |
| `GET` | `/auctions` | Browse public auctions |
| `GET` | `/auctions/{id}` | View an auction |
| `GET` | `/auctions/{id}/bids` | View recent bids |
| `POST` | `/auctions/{id}/bids` | Place a bid as a buyer |
| `GET` | `/admin/auctions` | List auctions, including drafts, as an admin |
| `POST` | `/admin/auctions` | Create a draft auction |
| `POST` | `/admin/auctions/{id}/publish` | Publish an auction |
| `POST` | `/admin/auctions/{id}/close` | Close an auction |
| `GET` | `/healthz` | Liveness check |
| `GET` | `/readyz` | Dependency readiness check |
| `GET` | `/metrics` | Prometheus metrics; requires `X-Metrics-Token` |

The WebSocket endpoint is `/ws/auctions/{id}` on the API host. WebSocket messages are for live updates; bids must go through the authenticated REST endpoint. The interactive OpenAPI page at `/docs` lists request and response schemas.

## Assumptions and trade-offs

A few choices were made to keep the assignment focused and the important behaviour auditable:

- **Admins manage auctions; buyers bid.** Admin accounts cannot place bids. This avoids mixing moderation privileges with participation in an auction.
- **One currency and integer amounts.** Prices are handled as integer paise to avoid floating-point rounding issues. Multi-currency support is out of scope.
- **PostgreSQL decides bid order.** A row lock makes the bid decision for a single auction serial. This is simple to reason about, but bids on a very popular auction will queue on that row.
- **Redis Pub/Sub is for delivery, not persistence.** The transactional outbox preserves the event to be published, while clients refresh state after reconnecting. Pub/Sub itself does not replay messages to disconnected clients.
- **A polling worker is used for lifecycle work.** It is straightforward to operate and recover, but auction transitions may happen a short time after their scheduled instant rather than with millisecond precision.
- **REST is used to submit bids; WebSockets are read-only.** This keeps authorization and validation in one request path and avoids accepting bids from a loosely controlled socket message.
- **The web proxy is an extra hop.** It simplifies same-origin cookie handling, at the cost of a small amount of additional latency and resource usage.
- **Payments and ownership transfer are out of scope.** This project demonstrates auctions, not a complete vehicle marketplace transaction. There is no payment provider, KYC, seller verification, email delivery, or legal transfer workflow.

## Repository layout

```text
.
├── apps/
│   ├── api/
│   │   ├── app/                 # FastAPI routes, models, security, worker
│   │   ├── alembic/             # Database migrations
│   │   ├── tests/               # Unit and integration tests
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── web/
│       ├── app/                 # Pages, API proxy, runtime config
│       ├── components/          # Shared UI components
│       ├── lib/                 # API client and frontend helpers
│       ├── Dockerfile
│       └── package.json
├── docs/
│   ├── ARCHITECTURE.md          # Architecture, data flow, decisions, limitations
│   └── SETUP_DEPLOY.md          # Full setup and deployment walkthrough
├── .github/workflows/ci.yml
├── compose.yaml
├── .env.example
└── README.md
```
