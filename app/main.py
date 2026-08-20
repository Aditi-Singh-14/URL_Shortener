"""
URL Shortener API

POST /shorten           -> create a short code for a given long URL
GET  /{short_code}       -> redirect to the original long URL
GET  /info/{short_code}   -> (bonus) look up stats without redirecting

Run with:  uvicorn app.main:app --reload
"""

import os
import random
import string
from contextlib import asynccontextmanager
from asyncpg.exceptions import UniqueViolationError

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from app.database import connect_to_db, close_db_connection, get_pool
from app.schema import URLCreateRequest, URLCreateResponse, URLInfoResponse

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SHORT_CODE_LENGTH = int(os.getenv("SHORT_CODE_LENGTH", "6"))
ALPHABET = string.ascii_letters + string.digits


def generate_short_code(length: int = 6) -> str:
    return "".join(random.choices(ALPHABET, k=length))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    yield
    await close_db_connection()


app = FastAPI(
    title="URL Shortener API",
    description="A basic URL shortener built with FastAPI + raw SQL (asyncpg) on PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "URL Shortener API is running. See /docs for usage."}


@app.post("/shorten", response_model=URLCreateResponse, status_code=201)
async def shorten_url(payload: URLCreateRequest):
    long_url = str(payload.url)
    pool = get_pool()

    async with pool.acquire() as conn:
        existing_row = await conn.fetchrow(
            "SELECT short_code, original_url FROM urls WHERE original_url = $1",
            long_url,
        )
        if existing_row:
            return URLCreateResponse(
                short_code=existing_row["short_code"],
                short_url=f"{BASE_URL}/{existing_row['short_code']}",
                original_url=existing_row["original_url"],
            )

        for _ in range(5):
            code = generate_short_code(SHORT_CODE_LENGTH)
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO urls (short_code, original_url)
                    VALUES ($1, $2)
                    RETURNING short_code, original_url
                    """,
                    code,
                    long_url,
                )
                return URLCreateResponse(
                    short_code=row["short_code"],
                    short_url=f"{BASE_URL}/{row['short_code']}",
                    original_url=row["original_url"],
                )
            except UniqueViolationError:
                continue

    raise HTTPException(status_code=500, detail="Could not generate a unique short code, please retry.")


@app.get("/info/{short_code}", response_model=URLInfoResponse)
async def get_url_info(short_code: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT short_code, original_url, created_at, visit_count FROM urls WHERE short_code = $1",
            short_code,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Short code not found")
    return URLInfoResponse(**dict(row))


@app.get("/{short_code}")
async def redirect_to_original(short_code: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE urls
            SET visit_count = visit_count + 1
            WHERE short_code = $1
            RETURNING original_url
            """,
            short_code,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Short code not found")

    return RedirectResponse(url=row["original_url"], status_code=307)