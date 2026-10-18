
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "knowledge.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                last_crawled TEXT NOT NULL
            )
        """)
        connection.commit()


def search_articles(query: str, limit: int = 5):
    words = [
        word.strip(".,?!:;()[]{}\"'")
        for word in query.lower().split()
    ]
    words = [word for word in words if len(word) > 2]

    if not words:
        return []

    conditions = " OR ".join(
        ["LOWER(title || ' ' || content) LIKE ?" for _ in words]
    )
    parameters = [f"%{word}%" for word in words]

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT title, url, content
            FROM articles
            WHERE {conditions}
            LIMIT ?
            """,
            (*parameters, limit),
        ).fetchall()

    return [dict(row) for row in rows]
