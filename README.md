# Barbershop SaaS — Backend

Multi-tenant booking backend: FastAPI + PostgreSQL + SQLAlchemy + Alembic.
This replaces the earlier Flask + Google Sheets prototype.

## What's here

```
app/
  core/config.py     # Settings, loaded from .env
  db/session.py       # SQLAlchemy engine + DB session dependency
  db/base.py           # Declarative Base — all models will inherit from this
  models/                # (empty for now — schema design is next)
  schemas/               # Pydantic request/response models will go here
  api/routes/health.py   # /api/health and /api/health/db
  main.py                 # FastAPI app entrypoint
alembic/                   # DB migrations, already wired to app.core.config
pyproject.toml
.env.example
```

Verified working: dependency install, app boot, `/` and `/api/health` endpoints,
and Alembic autogenerate — all tested end to end before handing this to you.

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

I can't sign up for accounts on your behalf, so this part's on you — it's quick:

1. Go to https://supabase.com → sign up (GitHub login is easiest) → "New project"
2. Pick a name (e.g. `barbershop-saas`), a strong DB password (save it), and a region close to Israel (e.g. `eu-central-1`)
3. Once it's provisioned: **Project Settings → Database → Connection string → URI**
   - Use the **Session pooler** connection string for local dev (port 5432 direct connection also works)
4. Paste that into your `.env` as `DATABASE_URL`, replacing the placeholder

## 3. Generate a real JWT secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Put the output in `.env` as `JWT_SECRET_KEY`.

## 4. Run it

```bash
uv run uvicorn app.main:app --reload
```

Then check:
- http://localhost:8000/ → `{"message": "Barbershop SaaS API is running", ...}`
- http://localhost:8000/api/health/db → confirms it can reach your Supabase DB
- http://localhost:8000/docs → interactive API docs (built in, courtesy of FastAPI)

If `/api/health/db` fails, double check the `DATABASE_URL` — this is the #1 place
people get tripped up (wrong password, wrong host, or the pooler vs. direct port).

## 5. Set up GitHub

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
JSON/PEM files — same mistake that bit the old Flask project won't happen here.

## Next steps (in order)

1. **Design the multi-tenant schema** — `Barbershop`, `User`, `Client`, `Service`,
   `Appointment`, etc., every tenant-owned table carrying a `barbershop_id`. This is
   the next thing to build, and everything else (auth, booking logic, WhatsApp) sits
   on top of it.
2. Wire up Alembic's first real migration once models exist (`uv run alembic revision --autogenerate -m "initial schema"`).
3. Auth: signup/login issuing a JWT that carries `barbershop_id`.
4. Core CRUD + availability logic.
5. WhatsApp webhook (Milestone 2 from the plan).

## Accounts you'll still need to create yourself (no rush — only when we get there)

| When | Service | Why |
|---|---|---|
| Now | Supabase | Postgres hosting |
| Now | GitHub | Version control |
| Milestone 1 end | Render | Backend hosting |
| Milestone 1 end | Vercel | Next.js dashboard hosting |
| Milestone 2 | Meta Developer account + WhatsApp Cloud API app | Customer-facing WhatsApp bot |
| Later | Sentry | Error monitoring |
| Later | Domain registrar | Your own domain |
