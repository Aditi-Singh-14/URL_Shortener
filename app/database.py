import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

pool: asyncpg.pool.Pool | None = None

async def connect_to_db():
    global pool
    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usls (
                id SERIAL PRIMARY KEY,
                short_code VARCHAR(16) UNIQUE NOT NULL,
                original_url VARCHAR(2048) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                visit_count INTEGER NOT NULL DEFAULT 0
            );
            """
        )

        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls (short_code);"
        )

async def close_db_connection():
    global pool
    if pool:
        await pool.close()
    
def get_db_pool() -> asyncpg.pool.Pool:
    return pool