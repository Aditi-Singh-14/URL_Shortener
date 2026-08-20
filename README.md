# URL Shortener API

A basic URL shortener built with **FastAPI** and **PostgreSQL** via the async `asyncpg` driver.

## Features

- `POST /shorten` — accepts a long URL, returns a shortened URL
- `GET /{short_code}` — redirects to the original URL
- `GET /info/{short_code}` — (bonus) returns metadata/stats for a short code without redirecting
- Duplicate long URLs reuse their existing short code instead of creating a new one
- Visit counter incremented atomically on every redirect (single `UPDATE ... RETURNING` query)
- Fully asynchronous route handlers, backed by an `asyncpg` connection pool
- Auto-generated interactive API docs via FastAPI (`/docs`)

## Tech Stack

- **FastAPI** — async web framework
- **PostgreSQL** — persistent storage
- **asyncpg** — async, raw-SQL PostgreSQL driver
- **Pydantic** — request/response validation
- **Uvicorn** — ASGI server

## Project Structure

\```
url-shortener/
├── app/
│   ├── __init__.py
│   ├── main.py       # FastAPI app, routes, and short-code generation
│   ├── database.py    # asyncpg connection pool + table/index creation
│   └── schema.py      # Pydantic request/response models
├── requirements.txt
├── .env.example
└── README.md
\```

## How It Works

1. `POST /shorten` receives a JSON body `{ "url": "https://example.com/some/long/path" }`.
2. The API checks (via `SELECT`) whether that exact URL was already shortened; if so, it returns the existing short code.
3. Otherwise, it generates a random 6-character alphanumeric code (62^6 ≈ 56 billion possible combinations) and inserts a new row with `INSERT ... RETURNING`. If a code collision occurs (`UniqueViolationError`), it retries with a new code, up to 5 times.
4. It returns the short code and the full short URL, e.g. `http://localhost:8000/aZ3kLQ`.
5. `GET /{short_code}` runs a single `UPDATE urls SET visit_count = visit_count + 1 WHERE short_code = $1 RETURNING original_url` — this increments the visit count and fetches the original URL in one atomic round-trip, then issues an HTTP 307 redirect to it.

## Setup & Running Locally

### 1. Prerequisites

- Python 3.10+
- PostgreSQL installed and running locally (or a connection string to a remote instance)

### 2. Create the database

\```bash
createdb url_shortener
\```

If that fails with a role/permission error, try:

\```bash
psql postgres -c "CREATE DATABASE url_shortener;"
\```

### 3. Install dependencies

\```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
\```

### 4. Configure environment variables

\```bash
cp .env.example .env
\```

Edit `.env` with your PostgreSQL credentials. On macOS with a Homebrew
install, the default user is usually your system username with no password
rather than `postgres:postgres`:

\```
DATABASE_URL=postgresql://<your_username>@localhost:5432/url_shortener
BASE_URL=http://localhost:8000
SHORT_CODE_LENGTH=6
\```

### 5. Run the server

\```bash
uvicorn app.main:app --reload
\```

The API will be available at `http://localhost:8000`. The `urls` table and
its index are created automatically on startup (see `connect_to_db()` in
`app/database.py`) — no separate migration step is needed for this
project's scope.

### 6. Try it out

Interactive docs (Swagger UI): `http://localhost:8000/docs`

**Shorten a URL:**

\```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.example.com/some/very/long/path"}'
\```

Response:

\```json
{
  "short_code": "aZ3kLQ",
  "short_url": "http://localhost:8000/aZ3kLQ",
  "original_url": "https://www.example.com/some/very/long/path"
}
\```

**Visit the short link (redirects):**

\```bash
curl -L http://localhost:8000/aZ3kLQ
\```

**Check stats without redirecting:**

\```bash
curl http://localhost:8000/info/aZ3kLQ
\```

## Design Notes / Trade-offs

- **Short code generation**: random 6-character alphanumeric strings rather
  than a base62-encoded auto-increment ID. This avoids leaking the total
  number of URLs created and makes codes less guessable. Collisions are
  handled by catching `asyncpg.exceptions.UniqueViolationError` and retrying
  with a new code (extremely unlikely at this length, but not ignored).
- **Duplicate URLs**: shortening the same long URL twice returns the same
  short code rather than creating redundant rows.
- **Redirect status code**: uses a `307 Temporary Redirect` rather than
  `301`/`308` permanent, so browsers/clients don't cache the redirect
  aggressively — useful in case a URL entry is ever updated.
- **Atomic visit counting**: the redirect endpoint updates `visit_count` and
  fetches `original_url` in a single `UPDATE ... RETURNING` statement rather
  than a separate `SELECT` followed by `UPDATE`, avoiding a race condition
  under concurrent requests to the same short code.
- **Connection pooling**: a single `asyncpg` pool is created on app startup
  (via FastAPI's `lifespan` context manager) and shared across all requests,
  rather than opening a new database connection per request.
- **Schema management**: the `urls` table is created with a plain
  `CREATE TABLE IF NOT EXISTS` on startup, which is fine for the scope of
  this assessment. In a production system this would be replaced with
  proper migrations (e.g. Alembic or raw versioned SQL migration files).
- **Validation**: Pydantic's `HttpUrl` type validates that submitted URLs are
  well-formed before they ever reach the database.

## Possible Extensions (not implemented, out of scope for this assessment)

- Custom/vanity short codes chosen by the user
- Expiring links (TTL)
- Rate limiting
- Authentication so users can manage only their own links
- Analytics beyond a simple visit counter (referrers, timestamps per visit)
- Dockerized setup (`Dockerfile` + `docker-compose.yml`) for one-command local startup