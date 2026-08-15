"""Shared Pytest fixtures for Malabar Watch test suite."""

import sqlite3
from collections.abc import Generator

import pytest

from malabar_watch.storage import DatabaseManager


@pytest.fixture
def in_memory_db() -> Generator[sqlite3.Connection, None, None]:
    """Provides a fresh in-memory SQLite database connection for testing."""
    manager = DatabaseManager(db_path=":memory:")
    conn = manager.get_connection()
    manager.initialize_schema(conn)
    yield conn
    conn.close()
