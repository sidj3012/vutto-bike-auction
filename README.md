# Vutto — production-minded motorcycle auctions

Full-stack auction demo. See [Setup and Deployment](docs/SETUP_DEPLOY.md) and [Architecture & Trade-offs](docs/ARCHITECTURE.md).

> This project is a deployment-ready *reference implementation*, not a claim that it has undergone a security audit, load test, or production certification. No live public URL is included; deployment requires your own hosting credentials.

## Seven commits

1. Infrastructure, schema and migrations.
2. Authentication, catalog and admin APIs.
3. Transactional bidding, worker and live events.
4. Buyer-facing pages and auction room.
5. Admin dashboard and listing management.
6. Testing, CI, security and deployment documentation.
7. UI fixes: account-aware bidding, countdowns, navigation, error messages and Vutto branding.

The API and database retain the `mileage_km` field for backward compatibility; the UI labels it **Km driven**.

## Quickstart

```bash
cp .env.example .env
# optionally change development-only secrets in .env
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
# open http://localhost:3000
```

Admin login is controlled by `ADMIN_EMAIL` and `ADMIN_PASSWORD` set in `.env`. `seed` adds sample auctions; publish them from the admin console. A regular buyer registers via the app. Do not reuse the demo credentials online.

## Verification status

- The Python code was syntax-checked, and 10 backend pure-rule tests passed in the creation environment.
- The integration test requires a disposable PostgreSQL database and Redis, and is wired into CI; it was not executed here.
- TypeScript/TSX files passed a syntax transpilation check, but **a complete Next.js build could not be run here**, because this environment could not fetch npm packages.
- No public project deployment or reviewer credentials have been created. Follow `docs/SETUP_DEPLOY.md` to obtain the hosted URL.
