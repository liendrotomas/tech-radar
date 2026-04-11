import sqlite3

from src.database.explorer import build_table_query, get_table_schema


def test_get_table_schema_classifies_sqlite_columns(tmp_path):
    database_path = tmp_path / "explorer.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE feed (
            id INTEGER PRIMARY KEY,
            title VARCHAR NOT NULL,
            score FLOAT NOT NULL,
            is_noise BOOLEAN NOT NULL,
            enriched JSON,
            created_at DATETIME NOT NULL
        )
        """
    )
    connection.commit()

    schema = get_table_schema(connection, "feed")

    categories = {column["name"]: column["category"] for column in schema}
    assert categories == {
        "id": "number",
        "title": "text",
        "score": "number",
        "is_noise": "boolean",
        "enriched": "json",
        "created_at": "datetime",
    }


def test_build_table_query_builds_filters_and_sorting():
    schema = [
        {"name": "id", "category": "number"},
        {"name": "title", "category": "text"},
        {"name": "score", "category": "number"},
        {"name": "is_noise", "category": "boolean"},
    ]

    query = build_table_query(
        table_name="feed",
        schema=schema,
        selected_columns=["id", "title"],
        filters={
            "title": {"mode": "contains", "value": "robot"},
            "score": {"min": 0.5, "max": 0.9},
            "is_noise": {"value": False},
        },
        global_search="space",
        sort_column="score",
        sort_direction="desc",
        limit=25,
        offset=50,
    )

    assert 'SELECT "id", "title" FROM "feed"' in query.sql
    assert 'CAST("title" AS TEXT) LIKE ?' in query.sql
    assert '"score" >= ?' in query.sql
    assert '"score" <= ?' in query.sql
    assert '"is_noise" = ?' in query.sql
    assert 'ORDER BY "score" DESC' in query.sql
    assert query.params == ["%space%", "%robot%", 0.5, 0.9, 0, 25, 50]
    assert query.count_params == ["%space%", "%robot%", 0.5, 0.9, 0]
