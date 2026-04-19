from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

from src.database.database import Database
from src.database.export_db import export_db
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


def _normalize_feedback_label(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"liked", "rejected", "explore"}:
        return normalized
    return None


def _normalize_feedback_notes(value: object) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def load_feedback_editor_dataframe(connection, founder_name: str | None = None) -> pd.DataFrame:
    query = """
        SELECT
            o.id AS opportunity_id,
            o.founder_name,
            o.title AS opportunity_title,
            o.description AS opportunity_summary,
            o.final_score AS opportunity_final_score,
            f.label AS feedback_label,
            f.notes AS feedback_notes
        FROM opportunity o
        LEFT JOIN feedback f ON f.opportunity_id = o.id
    """
    params = []
    if founder_name:
        query += " WHERE o.founder_name = ?"
        params.append(founder_name)
    query += " ORDER BY o.created_at DESC, o.id DESC"

    dataframe = pd.read_sql_query(query, connection, params=params)
    if "feedback_label" in dataframe.columns:
        dataframe["feedback_label"] = dataframe["feedback_label"].fillna("")
    if "feedback_notes" in dataframe.columns:
        dataframe["feedback_notes"] = dataframe["feedback_notes"].fillna("")
    return dataframe


def save_feedback_rows(connection, edited_rows: pd.DataFrame) -> tuple[int, int, int]:
    created = 0
    updated = 0
    deleted = 0
    for row in edited_rows.to_dict(orient="records"):
        opportunity_id = int(row["opportunity_id"])
        feedback_id = row.get("feedback_id")
        label = _normalize_feedback_label(row.get("feedback_label"))
        notes = _normalize_feedback_notes(row.get("feedback_notes"))
        title = str(row.get("opportunity_title", "") or "")
        summary = str(row.get("opportunity_summary", "") or "")
        final_score = row.get("opportunity_final_score")

        if feedback_id and (label is None and notes is None):
            connection.execute("DELETE FROM feedback WHERE id = ?", [int(feedback_id)])
            deleted += 1
            continue

        if label is None and notes is None:
            continue

        if feedback_id:
            connection.execute(
                """
                UPDATE feedback
                SET label = ?, notes = ?, title = ?, summary = ?, final_score = ?
                WHERE id = ?
                """,
                [label, notes, title, summary, final_score, int(feedback_id)],
            )
            updated += 1
        else:
            connection.execute(
                """
                INSERT INTO feedback (opportunity_id, title, label, notes)
                VALUES (?, ?, ?, ?)
                """,
                [opportunity_id, title, label, notes],
            )
            created += 1

    connection.commit()
    return created, updated, deleted


def run_git_commit(database_path: str, commit_message: str, push: bool) -> tuple[bool, str]:
    repo_root = Path(__file__).resolve().parent
    outputs_root = Path(database_path).resolve().parent
    if not (repo_root / ".git").exists():
        return False, "No se encontro un repositorio git en la raiz del proyecto."

    try:
        subprocess.run(
            ["git", "add", str(outputs_root)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        if not status_result.stdout.strip():
            return False, "No hay cambios para commitear despues de exportar."

        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        if push:
            subprocess.run(
                ["git", "push"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        return True, "Commit completado correctamente."
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        details = stderr or stdout or str(exc)
        return False, f"Fallo git: {details}"


def render_feedback_editor(connection, database_path: str) -> None:
    table_names = list_tables(connection)
    if "opportunity" not in table_names:
        st.info("No existe tabla opportunity, no se puede editar feedback.")
        return

    st.subheader("Feedback desde la tabla de oportunidades")
    founder_rows = connection.execute(
        "SELECT DISTINCT founder_name FROM opportunity ORDER BY founder_name"
    ).fetchall()
    founder_options = ["Todos"] + [row[0] for row in founder_rows if row[0]]
    selected_founder = st.selectbox("Filtrar por founder", founder_options)

    feedback_df = load_feedback_editor_dataframe(
        connection,
        founder_name=None if selected_founder == "Todos" else selected_founder,
    )
    if feedback_df.empty:
        st.info("No hay oportunidades para registrar feedback.")
        return

    edited_df = st.data_editor(
        feedback_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "opportunity_id": st.column_config.NumberColumn(disabled=True),
            "opportunity_title": st.column_config.TextColumn(disabled=True),
            "opportunity_summary": st.column_config.TextColumn(disabled=True),
            "feedback_label": st.column_config.SelectboxColumn(
                "feedback_label",
                options=["", "liked", "rejected", "explore"],
            ),
            "feedback_notes": st.column_config.TextColumn("feedback_notes"),
            "founder_name": st.column_config.TextColumn(disabled=True),
        },
    )

    action_cols = st.columns(3)
    if action_cols[0].button("Guardar feedback en DB", type="primary"):
        created, updated, deleted = save_feedback_rows(connection, edited_df)
        st.success(
            f"Feedback guardado. Creados: {created}, actualizados: {updated}, eliminados: {deleted}."
        )

    if action_cols[1].button("Exportar DB -> JSON"):
        export_db(base_path=str(Path(database_path).resolve().parent), source_db=database_path)
        st.success("JSON actualizado desde la base de datos.")

    commit_message = action_cols[2].text_input(
        "Mensaje git",
        value="Update feedback from sqlite explorer",
    )
    push_changes = st.checkbox("Hacer git push despues del commit", value=False)
    if st.button("Commit de cambios exportados"):
        ok, message = run_git_commit(
            database_path=database_path,
            commit_message=commit_message,
            push=push_changes,
        )
        if ok:
            st.success(message)
        else:
            st.warning(message)


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

    with st.expander("Editor de feedback", expanded=True):
        render_feedback_editor(connection, database_path)


if __name__ == "__main__":
    main()
