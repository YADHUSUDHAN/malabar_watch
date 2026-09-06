from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from malabar_watch.ingestion.models import PrecipitationMetrics


class DatabaseManager:
    """Manages SQLite database connections and table initialization."""

    def __init__(
        self,
        db_path: str = "malabar_watch.sqlite",
        connection: sqlite3.Connection | None = None,
    ) -> None:
        self.db_path = db_path
        self._shared_conn = connection
        if self.db_path == ":memory:" and self._shared_conn is None:
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.execute("PRAGMA foreign_keys=ON;")
            self._shared_conn.row_factory = sqlite3.Row

    def get_connection(self) -> sqlite3.Connection:
        """Returns a SQLite connection configured with WAL journal mode (for file DBs)."""
        if self._shared_conn is not None:
            return self._shared_conn

        conn = sqlite3.connect(self.db_path)
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_schema(self, conn: sqlite3.Connection | None = None) -> None:
        """Initializes tables for rainfall observations and issued alerts."""
        should_close = False
        if conn is None:
            conn = self.get_connection()
            if self._shared_conn is None:
                should_close = True

        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rainfall_observations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        district TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        precipitation_mm REAL NOT NULL,
                        rainfall_24h REAL NOT NULL DEFAULT 0.0,
                        rainfall_48h REAL NOT NULL DEFAULT 0.0,
                        rainfall_72h REAL NOT NULL DEFAULT 0.0,
                        antecedent_index REAL NOT NULL DEFAULT 0.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(district, timestamp) ON CONFLICT REPLACE
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

    def save_observation(
        self, metrics: PrecipitationMetrics, conn: sqlite3.Connection | None = None
    ) -> int:
        """Saves or updates a precipitation metrics observation into the database.

        Args:
            metrics: PrecipitationMetrics instance.
            conn: Optional existing connection. If omitted, a connection is managed.

        Returns:
            The row id of the inserted/updated record.
        """
        should_close = False
        if conn is None:
            conn = self.get_connection()
            if self._shared_conn is None:
                should_close = True

        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO rainfall_observations (
                        district,
                        timestamp,
                        precipitation_mm,
                        rainfall_24h,
                        rainfall_48h,
                        rainfall_72h,
                        antecedent_index
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(district, timestamp) DO UPDATE SET
                        precipitation_mm = excluded.precipitation_mm,
                        rainfall_24h = excluded.rainfall_24h,
                        rainfall_48h = excluded.rainfall_48h,
                        rainfall_72h = excluded.rainfall_72h,
                        antecedent_index = excluded.antecedent_index,
                        created_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        metrics.district_id,
                        metrics.timestamp.isoformat(),
                        metrics.rainfall_1h,
                        metrics.rainfall_24h,
                        metrics.rainfall_48h,
                        metrics.rainfall_72h,
                        metrics.antecedent_index,
                    ),
                )
                return cursor.lastrowid or 0
        finally:
            if should_close:
                conn.close()

    def get_latest_observation(
        self, district: str, conn: sqlite3.Connection | None = None
    ) -> dict[str, Any] | None:
        """Retrieves the latest rainfall observation recorded for a given district.

        Args:
            district: District identifier string (e.g. 'wayanad').
            conn: Optional existing connection.

        Returns:
            Dictionary with observation values, or None if no records exist.
        """
        should_close = False
        if conn is None:
            conn = self.get_connection()
            if self._shared_conn is None:
                should_close = True

        try:
            cursor = conn.execute(
                """
                SELECT * FROM rainfall_observations
                WHERE district = ?
                ORDER BY timestamp DESC
                LIMIT 1;
                """,
                (district,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            if should_close:
                conn.close()
