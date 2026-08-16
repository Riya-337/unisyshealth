"""
SentiHealth Database Manager.

Provides a unified storage interface supporting on-premises PostgreSQL (when DATABASE_URL is set)
with automatic SQLite fallback (data/app.db) for single-node hospital deployments.
"""

import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import APP_DB, DATA_DIR

logger = logging.getLogger("database")


class DatabaseManager:
    def __init__(self, db_path: str = APP_DB):
        self.db_path = db_path
        self.database_url = os.environ.get("DATABASE_URL", "").strip()
        self.is_postgres = self.database_url.startswith("postgres://") or self.database_url.startswith("postgresql://")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_schema()

    def get_connection(self):
        if self.is_postgres:
            try:
                import psycopg2
                return psycopg2.connect(self.database_url)
            except Exception as e:
                logger.warning(f"[DB] Could not connect to PostgreSQL ({e}). Falling back to local SQLite.")
        return sqlite3.connect(self.db_path)

    def init_schema(self):
        """Initialize database schema tables if not present."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE,
                    timestamp TEXT,
                    tier TEXT,
                    raw_score REAL,
                    source_ip TEXT,
                    payload TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_file TEXT,
                    created_at TEXT,
                    status TEXT
                )
            """)
            conn.commit()
        except Exception as e:
            logger.error(f"[DB] Schema initialization error: {e}")
        finally:
            conn.close()

    def log_event(self, event_id: str, tier: str, raw_score: float, source_ip: str, payload: dict) -> bool:
        """Insert a system event record."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            ts = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO system_events (event_id, timestamp, tier, raw_score, source_ip, payload) VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, ts, tier, raw_score, source_ip, json.dumps(payload))
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"[DB] Error logging event {event_id}: {e}")
            return False
        finally:
            conn.close()


# Singleton instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
