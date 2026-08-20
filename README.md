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
│   ├── main.py         # FastAPI app, routes, and short-code generation
│   ├── database.py     # asyncpg connection pool + table/index creation
│   └── schema.py       # Pydantic request/response models
├── requirements.txt
├── .env.example
└── README.md
\```

## How It Works

1.
