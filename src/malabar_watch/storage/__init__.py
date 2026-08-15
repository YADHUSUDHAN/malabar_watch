"""SQLite database storage module with WAL journal mode support."""

import sqlite3


class DatabaseManager:
    """Manages SQLite database connections and table initialization."""

    def __init__(self, db_path: str = "malabar_watch.sqlite") -> None:
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """Returns a SQLite connection configured with WAL journal mode (for file DBs)."""
        conn = sqlite3.connect(self.db_path)
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def initialize_schema(self, conn: sqlite3.Connection | None = None) -> None:
        """Initializes tables for rainfall observations and issued alerts."""
        should_close = False
        if conn is None:
            conn = self.get_connection()
            should_close = True

        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rainfall_observations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        district TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        precipitation_mm REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        district TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        message_english TEXT NOT NULL,
                        message_malayalam TEXT NOT NULL,
                        dispatched_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """)
        finally:
            if should_close:
                conn.close()
