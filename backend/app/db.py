"""Postgres access. Columns are snake_case in SQL and camelCase in Python."""

from collections.abc import Iterable

import psycopg

from app.config import getSettings

UPSERT_RECIPE_SQL = """
insert into recipes (id, title, ingredients, steps, cook_minutes, tags)
values (%(id)s, %(title)s, %(ingredients)s, %(steps)s, %(cookMinutes)s, %(tags)s)
on conflict (id) do update set
  title = excluded.title,
  ingredients = excluded.ingredients,
  steps = excluded.steps,
  cook_minutes = excluded.cook_minutes,
  tags = excluded.tags
"""


def getConnection() -> psycopg.Connection:
    databaseUrl = getSettings().databaseUrl
    if not databaseUrl:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
    return psycopg.connect(databaseUrl)


def upsertRecipes(recipeRows: Iterable[dict], batchSize: int = 500) -> int:
    """Insert or update recipe rows (embeddings untouched). Returns rows written."""
    written = 0
    batch: list[dict] = []
    with getConnection() as conn, conn.cursor() as cur:
        for row in recipeRows:
            batch.append(row)
            if len(batch) >= batchSize:
                cur.executemany(UPSERT_RECIPE_SQL, batch)
                written += len(batch)
                batch.clear()
        if batch:
            cur.executemany(UPSERT_RECIPE_SQL, batch)
            written += len(batch)
        conn.commit()
    return written


def countRecipes() -> int:
    """Number of rows in recipes. Handy for checking the connection works."""
    with getConnection() as conn, conn.cursor() as cur:
        cur.execute("select count(*) from recipes")
        return cur.fetchone()[0]