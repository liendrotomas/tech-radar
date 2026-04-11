from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TEXT_CATEGORIES = {"text", "json", "datetime"}


@dataclass(frozen=True)
class QuerySpec:
    sql: str
    params: list[Any]
    count_sql: str
    count_params: list[Any]


def connect_sqlite(database_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    return connection


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def classify_declared_type(declared_type: str | None) -> str:
    normalized = (declared_type or "").upper()
    if "JSON" in normalized:
        return "json"
    if any(token in normalized for token in ("BOOL",)):
        return "boolean"
    if any(token in normalized for token in ("DATE", "TIME")):
        return "datetime"
    if any(
        token in normalized for token in ("INT", "REAL", "FLOA", "DOUB", "NUM", "DEC")
    ):
        return "number"
    return "text"


def list_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def get_table_schema(
    connection: sqlite3.Connection, table_name: str
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()
    return [
        {
            "cid": row[0],
            "name": row[1],
            "type": row[2] or "TEXT",
            "nullable": not bool(row[3]),
            "default": row[4],
            "primary_key": bool(row[5]),
            "category": classify_declared_type(row[2]),
        }
        for row in rows
    ]


def build_table_query(
    table_name: str,
    schema: list[dict[str, Any]],
    selected_columns: list[str] | None = None,
    filters: dict[str, dict[str, Any]] | None = None,
    global_search: str | None = None,
    sort_column: str | None = None,
    sort_direction: str = "asc",
    limit: int = 100,
    offset: int = 0,
) -> QuerySpec:
    if not schema:
        raise ValueError("Table schema cannot be empty")

    available_columns = {column["name"]: column for column in schema}
    visible_columns = selected_columns or list(available_columns)
    unknown_columns = [
        name for name in visible_columns if name not in available_columns
    ]
    if unknown_columns:
        raise ValueError(f"Unknown columns requested: {unknown_columns}")

    clauses: list[str] = []
    params: list[Any] = []

    search_value = (global_search or "").strip()
    if search_value:
        searchable_columns = [
            column["name"] for column in schema if column["category"] in TEXT_CATEGORIES
        ]
        if searchable_columns:
            search_clauses = []
            for column_name in searchable_columns:
                search_clauses.append(
                    f"CAST({quote_identifier(column_name)} AS TEXT) LIKE ?"
                )
                params.append(f"%{search_value}%")
            clauses.append("(" + " OR ".join(search_clauses) + ")")

    for column_name, filter_spec in (filters or {}).items():
        column = available_columns.get(column_name)
        if column is None:
            continue

        column_sql = quote_identifier(column_name)
        category = column["category"]

        if category in TEXT_CATEGORIES:
            value = str(filter_spec.get("value", "")).strip()
            if not value:
                continue
            mode = filter_spec.get("mode", "contains")
            if mode == "equals":
                clauses.append(f"CAST({column_sql} AS TEXT) = ?")
                params.append(value)
            elif mode == "starts_with":
                clauses.append(f"CAST({column_sql} AS TEXT) LIKE ?")
                params.append(f"{value}%")
            else:
                clauses.append(f"CAST({column_sql} AS TEXT) LIKE ?")
                params.append(f"%{value}%")
        elif category == "number":
            equals = filter_spec.get("equals")
            minimum = filter_spec.get("min")
            maximum = filter_spec.get("max")
            if equals not in (None, ""):
                clauses.append(f"{column_sql} = ?")
                params.append(equals)
            else:
                if minimum not in (None, ""):
                    clauses.append(f"{column_sql} >= ?")
                    params.append(minimum)
                if maximum not in (None, ""):
                    clauses.append(f"{column_sql} <= ?")
                    params.append(maximum)
        elif category == "boolean":
            value = filter_spec.get("value")
            if value in (True, False):
                clauses.append(f"{column_sql} = ?")
                params.append(int(value))

    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    chosen_sort_column = (
        sort_column if sort_column in available_columns else visible_columns[0]
    )
    direction = "DESC" if str(sort_direction).lower() == "desc" else "ASC"
    safe_limit = max(1, min(int(limit), 1000))
    safe_offset = max(0, int(offset))
    select_sql = ", ".join(quote_identifier(column) for column in visible_columns)

    sql = (
        f"SELECT {select_sql} FROM {quote_identifier(table_name)}"
        f"{where_sql} ORDER BY {quote_identifier(chosen_sort_column)} {direction}"
        " LIMIT ? OFFSET ?"
    )
    count_sql = f"SELECT COUNT(*) FROM {quote_identifier(table_name)}{where_sql}"

    return QuerySpec(
        sql=sql,
        params=[*params, safe_limit, safe_offset],
        count_sql=count_sql,
        count_params=params.copy(),
    )
