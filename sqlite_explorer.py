from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.database.database import Database
from src.database.import_db import import_db
from src.database.explorer import (
    TEXT_CATEGORIES,
    build_table_query,
    connect_sqlite,
    get_table_schema,
    list_tables,
)


DEFAULT_DB_PATH = "outputs/tech_radar.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--page-size", type=int, default=250)
    known_args, _ = parser.parse_known_args()
    return known_args


def read_dataframe(connection, query_spec):
    dataframe = pd.read_sql_query(query_spec.sql, connection, params=query_spec.params)
    total_rows = connection.execute(
        query_spec.count_sql, query_spec.count_params
    ).fetchone()[0]
    return dataframe, total_rows


def render_filter_inputs(schema: list[dict]) -> dict[str, dict]:
    filters: dict[str, dict] = {}
    with st.expander("Filtros por columna", expanded=False):
        for column in schema:
            column_name = column["name"]
            category = column["category"]
            st.markdown(f"**{column_name}** ({column['type']})")

            if category in TEXT_CATEGORIES:
                mode = st.selectbox(
                    f"Modo para {column_name}",
                    ["contains", "equals", "starts_with"],
                    key=f"mode::{column_name}",
                )
                value = st.text_input(
                    f"Valor para {column_name}", key=f"value::{column_name}"
                )
                if value.strip():
                    filters[column_name] = {"mode": mode, "value": value}
            elif category == "number":
                control_columns = st.columns(3)
                equals = control_columns[0].text_input(
                    f"{column_name} =",
                    key=f"equals::{column_name}",
                )
                minimum = control_columns[1].text_input(
                    f"{column_name} min",
                    key=f"min::{column_name}",
                )
                maximum = control_columns[2].text_input(
                    f"{column_name} max",
                    key=f"max::{column_name}",
                )
                filter_payload = {}
                if equals.strip():
                    filter_payload["equals"] = float(equals)
                if minimum.strip():
                    filter_payload["min"] = float(minimum)
                if maximum.strip():
                    filter_payload["max"] = float(maximum)
                if filter_payload:
                    filters[column_name] = filter_payload
            elif category == "boolean":
                choice = st.selectbox(
                    f"Valor para {column_name}",
                    ["Todos", "True", "False"],
                    key=f"bool::{column_name}",
                )
                if choice != "Todos":
                    filters[column_name] = {"value": choice == "True"}

    return filters


def main() -> None:
    args = parse_args()
    st.set_page_config(page_title="SQLite Explorer", layout="wide")
    st.title("SQLite Explorer")
    st.caption("UI simple para explorar, filtrar y ordenar tu base de datos SQLite.")

    database_path = st.sidebar.text_input("Ruta de la base", value=args.db)
    # Create databse from json files if it doesn't exist
    BASE_DIR = os.path.dirname(getattr(args, "database_file", DEFAULT_DB_PATH))

    import_db(
        base_path=BASE_DIR,
        source_db=database_path,
        founder_name=[getattr(args, "founder", "")],
    )
    database_file = Path(database_path)
    if not database_file.exists():
        st.error(f"No existe la base: {database_file}")
        st.stop()

    connection = connect_sqlite(database_file)
    tables = list_tables(connection)
    if not tables:
        st.warning("La base no tiene tablas de usuario.")
        st.stop()

    table_name = st.sidebar.selectbox("Tabla", tables)
    schema = get_table_schema(connection, table_name)
    all_columns = [column["name"] for column in schema]
    default_columns = all_columns[: min(len(all_columns), 8)] or all_columns

    selected_columns = st.sidebar.multiselect(
        "Columnas visibles",
        all_columns,
        default=default_columns,
    )
    if not selected_columns:
        selected_columns = all_columns

    sort_column = st.sidebar.selectbox("Ordenar por", all_columns)
    sort_direction = st.sidebar.radio("Dirección", ["asc", "desc"], horizontal=True)
    page_size = st.sidebar.selectbox(
        "Filas por página",
        [25, 50, 100, 250],
        index=(
            [25, 50, 100, 250].index(args.page_size)
            if args.page_size in [25, 50, 100, 250]
            else 1
        ),
    )

    global_search = st.text_input(
        "Búsqueda rápida",
        placeholder="Busca texto en columnas tipo texto/json/datetime",
    )
    filters = render_filter_inputs(schema)

    query_preview_placeholder = st.empty()

    try:
        preview_spec = build_table_query(
            table_name=table_name,
            schema=schema,
            selected_columns=selected_columns,
            filters=filters,
            global_search=global_search,
            sort_column=sort_column,
            sort_direction=sort_direction,
            limit=page_size,
            offset=0,
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    total_rows = connection.execute(
        preview_spec.count_sql, preview_spec.count_params
    ).fetchone()[0]
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = st.number_input("Página", min_value=1, max_value=total_pages, value=1)

    query_spec = build_table_query(
        table_name=table_name,
        schema=schema,
        selected_columns=selected_columns,
        filters=filters,
        global_search=global_search,
        sort_column=sort_column,
        sort_direction=sort_direction,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    dataframe, total_rows = read_dataframe(connection, query_spec)

    metrics = st.columns(3)
    metrics[0].metric("Tabla", table_name)
    metrics[1].metric("Filas encontradas", total_rows)
    metrics[2].metric("Página actual", f"{page}/{total_pages}")

    st.dataframe(dataframe, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar CSV de esta vista",
        dataframe.to_csv(index=False).encode("utf-8"),
        file_name=f"{table_name}_page_{page}.csv",
        mime="text/csv",
    )

    with query_preview_placeholder.container():
        with st.expander("SQL generado", expanded=False):
            st.code(query_spec.sql, language="sql")
            st.write(query_spec.params)

    with st.expander("Esquema de la tabla", expanded=False):
        st.dataframe(pd.DataFrame(schema), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
