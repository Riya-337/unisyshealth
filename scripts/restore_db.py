"""
SentiHealth Database Restoration Utility.

Restores app.db from a specified backup or replica file with integrity checks.
"""

import argparse
import os
import shutil
import sqlite3
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import APP_DB, DATA_DIR


def restore_database(backup_path: str, target_db: str = APP_DB) -> bool:
    import hashlib
    import json

    if not os.path.exists(backup_path):
        print(f"[RESTORE ERROR] Backup file not found: {backup_path}")
        return False

    manifest_path = backup_path + ".manifest.json"
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"[RESTORE WARNING] Could not read manifest {manifest_path}: {e}")

    # 1. SHA-256 checksum validation
    if manifest.get("sha256"):
        hasher = hashlib.sha256()
        with open(backup_path, 'rb') as f:
            hasher.update(f.read())
        actual_sha256 = hasher.hexdigest()
        if actual_sha256 != manifest["sha256"]:
            print(f"[RESTORE ERROR] Checksum mismatch! Expected {manifest['sha256']}, got {actual_sha256}. Aborting restore.")
            return False

    database_url = os.environ.get("DATABASE_URL", "").strip()
    is_postgres = database_url.startswith("postgres://") or database_url.startswith("postgresql://")

    if is_postgres:
        print(f"[DB RESTORE] Validating PostgreSQL restore from {backup_path}...")
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
            table_count = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM system_events;")
            event_count = cursor.fetchone()[0]
            conn.close()

            expected_counts = manifest.get("table_counts", {})
            if "system_events" in expected_counts and event_count != expected_counts["system_events"]:
                print(f"[RESTORE ERROR] Row count mismatch! Expected exactly {expected_counts['system_events']} system_events, got {event_count}. Aborting restore.")
                return False


            print(f"[DB RESTORE SUCCESS] PostgreSQL verified ({table_count} tables, {event_count} system events).")
            return True
        except Exception as e:
            print(f"[RESTORE ERROR] PostgreSQL restore integrity validation failed: {e}. Aborting restore.")
            return False

    # SQLite fallback validation
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        
        # Verify manifest table counts on backup DB
        if manifest.get("table_counts"):
            for tbl, expected_c in manifest["table_counts"].items():
                try:
                    cursor.execute(f"SELECT count(*) FROM {tbl}")
                    actual_c = cursor.fetchone()[0]
                    if actual_c != expected_c:
                        print(f"[RESTORE ERROR] Table '{tbl}' count mismatch: expected {expected_c}, got {actual_c}. Aborting restore.")
                        conn.close()
                        return False
                except Exception:
                    pass

        conn.close()
        if not res or res[0] != "ok":
            print(f"[RESTORE ERROR] Backup file failed SQLite integrity check: {res}. Aborting restore.")
            return False
    except Exception as e:
        print(f"[RESTORE ERROR] SQLite check exception: {e}. Aborting restore.")
        return False

    # Perform atomic restore
    tmp_path = target_db + ".restore_tmp"
    try:
        shutil.copyfile(backup_path, tmp_path)
        os.replace(tmp_path, target_db)
        print(f"[DB RESTORE SUCCESS] Successfully restored database from {backup_path} -> {target_db}")
        return True
    except Exception as exc:
        print(f"[RESTORE ERROR] Failed during atomic copy/replace: {exc}. Rolling back.")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False




def main():
    parser = argparse.ArgumentParser(description="SentiHealth Database Restoration Utility")
    parser.add_argument("--backup", required=True, help="Path to backup .db file")
    parser.add_argument("--target", default=APP_DB, help="Target database path")
    args = parser.parse_args()

    success = restore_database(args.backup, args.target)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
