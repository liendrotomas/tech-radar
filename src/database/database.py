from sqlmodel import JSON, Column, SQLModel, create_engine, Session, Field, select
from sqlalchemy import delete, inspect, text
from typing import Optional
from datetime import datetime
from pydantic_core import PydanticUndefined


class Database:
    def __init__(self, filepath: str, recreate_on_schema_change: bool = True):
        self.filepath = filepath
        self.recreate_on_schema_change = recreate_on_schema_change
        self.engine = create_engine(f"sqlite:///{filepath}")
        SQLModel.metadata.create_all(self.engine)
        self._apply_schema_migrations()
        self._normalize_legacy_data()

    def _apply_schema_migrations(self):
        inspector = inspect(self.engine)

        with self.engine.begin() as connection:
            for table_name, table in SQLModel.metadata.tables.items():
                if table_name not in inspector.get_table_names():
                    continue

                existing_columns = {
                    column["name"]: column
                    for column in inspector.get_columns(table_name)
                }

                drift = self._get_schema_drift(table, existing_columns)
                if drift["extra"] or drift["incompatible"]:
                    if not self.recreate_on_schema_change:
                        raise RuntimeError(
                            f"Schema drift detected in table '{table_name}'. "
                            "Use recreate_on_schema_change=True in development to rebuild the table."
                        )

                    table.drop(bind=connection, checkfirst=True)
                    table.create(bind=connection, checkfirst=True)
                    continue

                for column in table.columns:
                    if column.name in existing_columns:
                        continue

                    statement = self._build_add_column_statement(table_name, column)
                    connection.execute(text(statement))

    def _get_schema_drift(self, table, existing_columns):
        model_columns = {column.name: column for column in table.columns}
        extra_columns = set(existing_columns) - set(model_columns)
        incompatible_columns = set()

        for column_name, existing_column in existing_columns.items():
            model_column = model_columns.get(column_name)
            if model_column is None:
                continue

            existing_type = existing_column["type"].compile(dialect=self.engine.dialect)
            model_type = model_column.type.compile(dialect=self.engine.dialect)
            nullable_mismatch = (
                not model_column.primary_key
                and existing_column["nullable"] != model_column.nullable
            )
            if existing_type != model_type or nullable_mismatch:
                incompatible_columns.add(column_name)

        return {
            "extra": extra_columns,
            "incompatible": incompatible_columns,
        }

    def _build_add_column_statement(self, table_name, column):
        column_parts = [
            f"ALTER TABLE {table_name} ADD COLUMN {column.name}",
            column.type.compile(dialect=self.engine.dialect),
        ]

        default_sql = self._get_column_default_sql(table_name, column.name, column)
        if not column.nullable:
            column_parts.append("NOT NULL")
        if default_sql is not None:
            column_parts.append(f"DEFAULT {default_sql}")

        return " ".join(column_parts)

    def _get_column_default_sql(self, table_name, column_name, column):
        model_class = self._get_model_class_for_table(table_name)
        if model_class is not None:
            field_info = model_class.model_fields.get(column_name)
            if field_info is not None:
                if field_info.default_factory is dict:
                    return "'{}'"
                if field_info.default_factory is list:
                    return "'[]'"
                if field_info.default_factory is datetime.utcnow:
                    return self._format_default_sql(datetime.utcnow().isoformat())
                if (
                    field_info.default is not PydanticUndefined
                    and field_info.default is not None
                ):
                    return self._format_default_sql(field_info.default)

        if column.default is not None and getattr(column.default, "is_scalar", False):
            return self._format_default_sql(column.default.arg)

        if column.nullable:
            return None

        python_type = getattr(column.type, "python_type", None)
        fallback_defaults = {
            str: "''",
            int: "0",
            float: "0",
            bool: "0",
            dict: "'{}'",
            list: "'[]'",
        }
        return fallback_defaults.get(python_type, "''")

    def _format_default_sql(self, value):
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (dict, list)):
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def _get_model_class_for_table(self, table_name):
        for model_class in SQLModel.__subclasses__():
            table = getattr(model_class, "__table__", None)
            if table is not None and table.name == table_name:
                return model_class
        return None

    def _normalize_legacy_data(self):
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE opportunity SET created_at = :timestamp "
                    "WHERE created_at IS NULL OR created_at = '' OR created_at = 'PydanticUndefined'"
                ),
                {"timestamp": datetime.utcnow().isoformat()},
            )
            connection.execute(
                text(
                    "UPDATE feed SET enriched = '{}' "
                    "WHERE enriched IS NULL "
                    "OR enriched = '' "
                    "OR enriched = 'N/A' "
                    "OR enriched = 'null' "
                    "OR enriched = 'PydanticUndefined' "
                    "OR enriched = '\"N/A\"'"
                )
            )
            connection.execute(
                text(
                    "UPDATE feed SET processing_metadata = '{}' "
                    "WHERE processing_metadata IS NULL "
                    "OR processing_metadata = '' "
                    "OR processing_metadata = 'null' "
                    "OR processing_metadata = 'PydanticUndefined'"
                )
            )
            connection.execute(
                text(
                    "UPDATE founder SET profile = '{}' "
                    "WHERE profile IS NULL "
                    "OR profile = '' "
                    "OR profile = 'null' "
                    "OR profile = 'PydanticUndefined'"
                )
            )

    def get_session(self):
        with Session(self.engine) as session:
            return session

    def get_engine(self):
        return self.engine

    def add_item(self, item):
        with Session(self.engine) as session:
            session.merge(item)
            session.commit()

    def remove_item(self, item):
        with Session(self.engine) as session:
            session.delete(item)
            session.commit()

    def clear_items(self, item_type):
        with Session(self.engine) as session:
            session.exec(delete(item_type))
            session.commit()

    def retrieve_items(self, item):
        with Session(self.engine) as session:
            results = session.exec(select(item)).all()
            return results


class Founder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    profile: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Feed(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    link: str
    summary: str
    published_at: str
    source: str
    keywords: list = Field(default_factory=list, sa_column=Column(JSON))
    signal_score: float = 0
    noise_score: float = 0
    is_noise: bool = False
    processing_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    enriched: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Opportunity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    founder_name: str
    title: str
    description: str
    score: float = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    why_now: str = Field(default="")
    founder_fit: str = Field(default="")
    founder_fit_score: int = Field(default=0)
    wedge: str = Field(default="")
    wedge_score: float = Field(default=0)
    risk: str = Field(default="")
    required_insight: str = Field(default="")
    # scoring fields
    final_score: float = Field(default=0.0)
    market_size: int = Field(default=0)
    technical_advantage: int = Field(default=0)
    timing: int = Field(default=0)
    defensibility: int = Field(default=0)
    notes: str = Field(default="")


class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    opportunity_id: int
    label: str = Field(default=None)  # liked / rejected / neutral
    notes: Optional[str] = Field(default=None)
