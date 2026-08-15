"""Integration tests for database storage manager."""

import sqlite3

import pytest


@pytest.mark.integration
def test_schema_initialization(in_memory_db: sqlite3.Connection) -> None:
    """Verify that required tables are created in the database."""
    cursor = in_memory_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    assert "rainfall_observations" in tables
    assert "alerts_history" in tables
