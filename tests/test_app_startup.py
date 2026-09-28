import importlib
import sys


def test_app_composition_does_not_import_removed_advanced_modules():
    importlib.import_module("app.main")
    assert not any(
        name == "fatigue" or name.startswith("fatigue.")
        or name == "monitoring" or name.startswith("monitoring.")
        for name in sys.modules
    )


def test_historical_tables_remain_in_database_schema(tmp_path):
    from database.connection import DatabaseManager

    db = DatabaseManager(str(tmp_path / "compatibility.db"))
    db.initialize_database()
    with db.get_connection() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "baselines",
        "fatigue_assessments",
        "fatigue_events",
        "fatigue_session_summaries",
    }.issubset(tables)
