
from task1_knowledge_brain.database import (
    initialize_database,
    get_connection,
)

initialize_database()

with get_connection() as connection:
    rows = connection.execute(
        "SELECT title, url FROM articles"
    ).fetchall()

print(f"\nTotal articles in database: {len(rows)}")

for row in rows:
    print(f"- {row['title']}")
    print(f"  {row['url']}")
