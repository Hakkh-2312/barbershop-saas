
# Barbershop SaaS

Multi-tenant booking platform: FastAPI + PostgreSQL + SQLAlchemy + Alembic
backend, with a Next.js dashboard for shop owners. This replaces the earlier
Flask + Google Sheets prototype.

## What's here

```
app/
  core/config.py       # Settings, loaded from .env
  core/security.py     # Password hashing (argon2) + JWT issuing/verification
  core/logging.py      # Root logger configuration
  db/session.py        # SQLAlchemy engine + DB session dependency
  db/base.py            # Declarative Base — all models inherit from this
  db/mixins.py           # TimestampMixin (created_at/updated_at)
  db/seed.py               # One-off script seeding a demo tenant
  models/                   # Tenant, User, Customer, Service, WorkingHours, Appointment, WhatsappConversation
  schemas/                   # Pydantic request/response models
  services/                    # booking.py (shared booking/slot logic), whatsapp_flow.py
                                # (conversation state machine), whatsapp_i18n.py (ar/he/en),
                                # whatsapp_client.py (Meta API calls)
  api/deps.py                  # get_current_user / get_current_tenant_id
  api/routes/
    health.py                    # /api/health, /api/health/db
    auth.py                      # /api/auth/signup, /api/auth/login
    availability.py              # /api/availability
    appointments.py              # /api/appointments (create, list, get, cancel, reschedule)
    customers.py                 # /api/customers (full CRUD)
    services.py                  # /api/services (full CRUD)
    working_hours.py             # /api/working-hours (get + upsert per day)
    tenants.py                   # /api/tenants/me (shop name/phone/address)
    whatsapp.py                  # /api/whatsapp/webhook (Meta Cloud API)
  main.py                         # FastAPI app entrypoint, CORS, error handling
alembic/                           # DB migrations, wired to app.core.config
tests/                              # pytest + httpx, runs against real Postgres
Dockerfile, docker-compose.yml       # Containerized app + local Postgres
.github/workflows/ci.yml              # Lint, migrate, test on every push/PR
pyproject.toml
.env.example

dashboard/                            # Next.js shop-owner UI (separate app, see below)
```

Every tenant-owned table is scoped by `tenant_id`, resolved from the caller's
JWT (not a hardcoded value) via `get_current_tenant_id`. A tenant cannot read,
modify, or book against another tenant's data — covered by
`tests/test_tenant_isolation.py`. Double-booking is prevented both at the
application level (an overlap check before insert) and at the database level
(a Postgres exclusion constraint on `appointments`), so even two truly
simultaneous requests for the same slot can't both succeed.

## 1. Install locally

You'll need Python 3.11+ and `uv` (fast Python package manager).

```bash
# Install uv (pick one)
pip install uv
# or: curl -LsSf https://astral.sh/uv/install.sh | sh

cd barbershop-saas
cp .env.example .env
uv sync
```

## 2. Create your Supabase project (managed Postgres)

1. Go to https://supabase.com → sign up (GitHub login is easiest) → "New project"
2. Pick a name (e.g. `barbershop-saas`), a strong DB password (save it), and a region close to Israel (e.g. `eu-central-1`)
3. Once it's provisioned: **Project Settings → Database → Connection string → URI**
   - Use the **Session pooler** connection string for local dev (port 5432 direct connection also works)
4. Paste that into your `.env` as `DATABASE_URL`, replacing the placeholder

Alternatively, run `docker compose up -d db` for a local Postgres instead of Supabase (see "Running with Docker" below).

## 3. Generate a real JWT secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Put the output in `.env` as `JWT_SECRET_KEY`.

## 4. Apply database migrations

```bash
uv run alembic upgrade head
```

## 5. Run it

```bash
uv run uvicorn app.main:app --reload
```

Then check:
- http://localhost:8000/ → `{"message": "Barbershop SaaS API is running", ...}`
- http://localhost:8000/api/health/db → confirms it can reach your database
- http://localhost:8000/docs → interactive API docs, including a working "Authorize"
  button — sign up via `POST /api/auth/signup` or paste a token you already have

If `/api/health/db` fails, double check the `DATABASE_URL` — this is the #1 place
people get tripped up (wrong password, wrong host, or the pooler vs. direct port).

## Running tests

Tests need a real Postgres (the double-booking exclusion constraint uses
`gist`/`tsrange`, which has no SQLite equivalent) and isolate everything into
their own `test` schema, so they never touch whatever else lives in the
target database:

```bash
docker compose up -d db
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/barbershop uv run pytest
```

(Omit `TEST_DATABASE_URL` to default to `localhost:5432/postgres`.)

## Running with Docker

```bash
docker compose up -d db
docker compose run --rm api uv run alembic upgrade head   # first time, and after new migrations
docker compose up
```

This runs the API against a local Postgres container rather than Supabase —
`docker-compose.yml` overrides `DATABASE_URL` for the `api` service regardless
of what's in `.env`.

## Running the dashboard

```bash
cd dashboard
npm install
cp .env.local.example .env.local   # defaults to http://localhost:8000, fine for local dev
npm run dev
```

Then open http://localhost:3000 — sign up (creates a tenant + logs you in),
and manage appointments/customers/services/working hours. It talks to
whatever `NEXT_PUBLIC_API_URL` points at, so make sure the backend (either
`uv run uvicorn ...` or `docker compose up`) is running first. CORS is
already configured backend-side for `http://localhost:3000` by default.

## WhatsApp Cloud API webhook

A customer can message the shop's WhatsApp number and book entirely by
tapping clickable options — no manual dashboard entry needed. The flow:
a welcome menu (book / change language / call the shop / the address) →
pick a service → pick a date (up to 2 weeks out) → pick an open time →
booked, with a summary message and the conversation ending there. Their
`Customer` record is created automatically from their WhatsApp number and
profile name the first time they book. Defaults to Arabic, with Hebrew and
English available from the menu — the chosen language is remembered per
phone number across visits. Every list (services/dates/times) pages past
10 items via a "more options" row, since WhatsApp caps list messages at 10
rows. Reuses the exact same validation as the REST API
(`app/services/booking.py`) so working hours, overlaps, and the
double-booking exclusion constraint all apply identically.

The shop's phone number and address (used by the "call"/"address" menu
options) are set on the **Settings** page in the dashboard.

Not tenant-scoped yet — `WHATSAPP_TENANT_ID` says which single shop this
WhatsApp number belongs to (there's no phone-number-to-tenant mapping until
multiple real shops are on WhatsApp). Also not in scope yet: cancelling or
rescheduling via WhatsApp (use the dashboard/API for that), and conversation
state doesn't expire — an abandoned flow just continues from where it left
off the next time that number messages in.

To set it up:
1. [developers.facebook.com/apps](https://developers.facebook.com/apps) → create an app → add the **WhatsApp** product.
2. WhatsApp → API Setup gives you a test phone number, its **Phone Number ID**, and a temporary **access token**.
3. WhatsApp → Configuration → Webhook: callback URL `https://<public-url>/api/whatsapp/webhook` (needs real HTTPS — use `ngrok http 8000` locally, or your Render URL once deployed), verify token = anything you choose.
4. Put the verify token, access token, phone number ID, and the id of the tenant this number belongs to into `.env` as `WHATSAPP_VERIFY_TOKEN` / `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_TENANT_ID`.

If `WHATSAPP_TENANT_ID` is unset, incoming messages just get a static
"coming soon" reply instead of the booking flow — safe default until you've
set up a real shop to receive bookings.

## Configuration reference

Beyond `DATABASE_URL` and `JWT_SECRET_KEY`, see `.env.example` for:
- `CORS_ALLOWED_ORIGINS` — comma-separated origins allowed to call this API (e.g. the dashboard's dev/prod URLs)
- `DEBUG` — leave `true` locally; a deployment that leaves this unset defaults to `false` so stack traces never leak to clients
- `SENTRY_DSN` — optional; once set, unhandled exceptions are reported to Sentry
- `WHATSAPP_VERIFY_TOKEN` / `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_TENANT_ID` — see "WhatsApp Cloud API webhook" above

## Set up GitHub

```bash
git init
git add .
git commit -m "Initial FastAPI skeleton"
```
Create a new repo at https://github.com/new, then:
```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```
`.gitignore` is already set up to exclude `.env`, `.venv/`, and any service-account
JSON/PEM files. Pushing to `main` or opening a PR runs `.github/workflows/ci.yml`
(lint, migrate, test against a fresh Postgres container).

## Next steps (in order)

1. ~~Design the multi-tenant schema~~ — done: `Tenant`, `User`, `Customer`, `Service`,
   `WorkingHours`, `Appointment`, every tenant-owned table carrying a `tenant_id`.
2. ~~Auth: signup/login issuing a JWT that carries the tenant~~ — done.
3. ~~Core CRUD + availability/booking logic~~ — done, including double-booking
   protection and full CRUD for customers/services/working hours.
4. ~~Automated tests, DB hardening, CORS, logging/Sentry, Docker, CI~~ — done.
5. ~~Next.js dashboard, WhatsApp Cloud API webhook~~ — done. WhatsApp needs
   your own Meta app credentials in `.env` to actually talk to real
   WhatsApp (see "WhatsApp Cloud API webhook" above) — the handshake and
   message-receiving logic are verified, sending just needs real
   credentials to complete the loop.
6. **Next up:** deploy for real (Render for the API, Vercel for the
   dashboard) so the WhatsApp webhook has a stable public URL, then
   multi-staff availability and timezone handling if/when they matter.

## Accounts you'll still need to create yourself (no rush — only when we get there)

| When | Service | Why |
|---|---|---|
| Now | Supabase | Postgres hosting |
| Now | GitHub | Version control |
| Milestone 1 end | Render | Backend hosting |
| Milestone 1 end | Vercel | Next.js dashboard hosting |
| Milestone 2 | Meta Developer account + WhatsApp Cloud API app | Customer-facing WhatsApp bot |
| Whenever you want error alerts | Sentry | Error monitoring (`SENTRY_DSN` in `.env`) |
| Later | Domain registrar | Your own domain |
