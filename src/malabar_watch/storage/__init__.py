from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from malabar_watch.ingestion.models import PrecipitationMetrics
    from malabar_watch.risk_engine.models import RiskAssessment


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
        """Initializes tables for rainfall observations, alerts, and risk assessments."""
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
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS risk_assessments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        district TEXT NOT NULL,
                        assessed_at DATETIME NOT NULL,
                        risk_level TEXT NOT NULL,
                        escalation_state TEXT NOT NULL,
                        rainfall_1h REAL NOT NULL,
                        rainfall_24h REAL NOT NULL,
                        rainfall_48h REAL NOT NULL,
                        rainfall_72h REAL NOT NULL,
                        antecedent_index REAL NOT NULL,
                        triggered_rules TEXT NOT NULL,
                        historical_event_id TEXT,
                        requires_alert INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

    def save_assessment(
        self, assessment: RiskAssessment, conn: sqlite3.Connection | None = None
    ) -> int:
        """Saves an immutable deterministic RiskAssessment record into SQLite.

        Args:
            assessment: RiskAssessment instance to persist.
            conn: Optional existing connection.

        Returns:
            The row id of the inserted record.
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
                    INSERT INTO risk_assessments (
                        district,
                        assessed_at,
                        risk_level,
                        escalation_state,
                        rainfall_1h,
                        rainfall_24h,
                        rainfall_48h,
                        rainfall_72h,
                        antecedent_index,
                        triggered_rules,
                        historical_event_id,
                        requires_alert
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        assessment.district,
                        assessment.assessed_at.isoformat(),
                        assessment.risk_level.value,
                        assessment.escalation_state.value,
                        assessment.rainfall_1h,
                        assessment.rainfall_24h,
                        assessment.rainfall_48h,
                        assessment.rainfall_72h,
                        assessment.antecedent_index,
                        json.dumps(assessment.triggered_rules),
                        (
                            assessment.historical_event.event_id
                            if assessment.historical_event
                            else None
                        ),
                        1 if assessment.requires_alert else 0,
                    ),
                )
                return cursor.lastrowid or 0
        finally:
            if should_close:
                conn.close()

    def get_latest_assessment(
        self, district: str, conn: sqlite3.Connection | None = None
    ) -> dict[str, Any] | None:
        """Retrieves the most recent RiskAssessment record for a given district.

        Args:
            district: District or micro-zone identifier.
            conn: Optional existing connection.

        Returns:
            Dictionary with assessment values and deserialized triggered_rules, or None.
        """
        should_close = False
        if conn is None:
            conn = self.get_connection()
            if self._shared_conn is None:
                should_close = True

        try:
            cursor = conn.execute(
                """
                SELECT * FROM risk_assessments
                WHERE district = ?
                ORDER BY assessed_at DESC, id DESC
                LIMIT 1;
                """,
                (district,),
            )
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if "triggered_rules" in d and isinstance(d["triggered_rules"], str):
                    try:
                        d["triggered_rules"] = json.loads(d["triggered_rules"])
                    except Exception:
                        pass
                return d
            return None
        finally:
            if should_close:
                conn.close()

    def get_recent_assessments(
        self, district: str, limit: int = 5, conn: sqlite3.Connection | None = None
    ) -> list[dict[str, Any]]:
        """Retrieves recent assessments for a district to evaluate hysteresis and state trends.

        Args:
            district: District identifier.
            limit: Maximum count of trailing assessments to return.
            conn: Optional existing connection.

        Returns:
            List of assessment record dictionaries ordered newest first.
        """
        should_close = False
        if conn is None:
            conn = self.get_connection()
            if self._shared_conn is None:
                should_close = True

        try:
            cursor = conn.execute(
                """
                SELECT * FROM risk_assessments
                WHERE district = ?
                ORDER BY assessed_at DESC, id DESC
                LIMIT ?;
                """,
                (district, limit),
            )
            rows = cursor.fetchall()
            results: list[dict[str, Any]] = []
            for r in rows:
                d = dict(r)
                if "triggered_rules" in d and isinstance(d["triggered_rules"], str):
                    try:
                        d["triggered_rules"] = json.loads(d["triggered_rules"])
                    except Exception:
                        pass
                results.append(d)
            return results
        finally:
            if should_close:
                conn.close()

    def get_latest_alert_time(
        self, district: str, conn: sqlite3.Connection | None = None
    ) -> datetime | None:
        """Finds the timestamp when an alert was last required/dispatched for a district.

        Args:
            district: District identifier.
            conn: Optional existing connection.

        Returns:
            Datetime of last alert, or None if no prior alert occurred.
        """
        should_close = False
        if conn is None:
            conn = self.get_connection()
            if self._shared_conn is None:
                should_close = True

        try:
            cursor = conn.execute(
                """
                SELECT assessed_at FROM risk_assessments
                WHERE district = ? AND requires_alert = 1
                ORDER BY assessed_at DESC, id DESC
                LIMIT 1;
                """,
                (district,),
            )
            row = cursor.fetchone()
            if row:
                val = row["assessed_at"]
                if isinstance(val, str):
                    return datetime.fromisoformat(val)
                if isinstance(val, datetime):
                    return val
            return None
        finally:
            if should_close:
                conn.close()
