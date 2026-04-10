import sqlite3, os, sys

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, ".."))
from src.database.database import Database, Founder, Opportunity


def test_database_get_engine(tmp_path):
    database = Database(str(tmp_path / "test.db"))

    assert database.get_engine() is database.engine


def test_database_add_and_retrieve_items(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    founder = Founder(name="Tomas Liendro", profile={"archetype": "builder"})

    database.add_item(founder)
    founders = database.retrieve_items(Founder)

    assert len(founders) == 1
    assert founders[0].name == "Tomas Liendro"
    assert founders[0].profile == {"archetype": "builder"}


def test_database_remove_item(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    founder = Founder(name="Tomas Liendro", profile={"archetype": "builder"})

    database.add_item(founder)
    stored_founder = database.retrieve_items(Founder)[0]

    database.remove_item(stored_founder)

    assert database.retrieve_items(Founder) == []


def test_database_clear_items(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    founders = [
        Founder(name="Tomas Liendro", profile={"archetype": "builder"}),
        Founder(name="Ada Lovelace", profile={"archetype": "researcher"}),
    ]

    for founder in founders:
        database.add_item(founder)

    database.clear_items(Founder)

    assert database.retrieve_items(Founder) == []


def test_database_add_opportunity_with_defaults(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    opportunity = Opportunity(
        founder_name="Tomas Liendro",
        title="AI workflow ops",
        description="Automates internal ops with agents",
    )

    database.add_item(opportunity)
    opportunities = database.retrieve_items(Opportunity)

    assert len(opportunities) == 1
    assert opportunities[0].founder_name == "Tomas Liendro"
    assert opportunities[0].title == "AI workflow ops"
    assert opportunities[0].description == "Automates internal ops with agents"


def test_database_rebuilds_table_with_extra_columns_in_dev_mode(tmp_path):
    database_path = tmp_path / "legacy_with_extra_columns.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        "CREATE TABLE opportunity (id INTEGER PRIMARY KEY, founder_name VARCHAR NOT NULL, title VARCHAR NOT NULL, description VARCHAR NOT NULL, score FLOAT NOT NULL, created_at DATETIME NOT NULL, legacy_field VARCHAR NOT NULL DEFAULT '')"
    )
    connection.commit()
    connection.close()

    Database(str(database_path), recreate_on_schema_change=True)

    connection = sqlite3.connect(database_path)
    opportunity_columns = {
        column[1]
        for column in connection.execute("PRAGMA table_info(opportunity)").fetchall()
    }
    connection.close()

    assert "legacy_field" not in opportunity_columns
    assert "created_at" in opportunity_columns
    assert "required_insight" in opportunity_columns
