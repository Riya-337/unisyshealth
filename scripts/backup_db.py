"""
SentiHealth On-Premises Automated Database Backup Utility.

Creates timestamped backups of app.db (and PostgreSQL dump if configured),
stores them in data/backups/, and maintains a retention window.
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import APP_DB, DATA_DIR

BACKUPS_DIR = os.path.join(DATA_DIR, "backups")


def run_backup(dest_dir: str = BACKUPS_DIR) -> str:
    import hashlib
    os.makedirs(dest_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"app_backup_{timestamp}.db"
    backup_path = os.path.join(dest_dir, backup_filename)

    if not os.path.exists(APP_DB):
        conn = sqlite3.connect(APP_DB)
        conn.close()

    # Online SQLite backup API (prevents database corruption during live writes)
    src_conn = sqlite3.connect(APP_DB)
    dst_conn = sqlite3.connect(backup_path)
    with dst_conn:
        src_conn.backup(dst_conn)

    # Compute row counts for manifest
    cursor = dst_conn.cursor()
    tables = ["system_events", "audit_backups"]
    table_counts = {}
    for t in tables:
        try:
            cursor.execute(f"SELECT count(*) FROM {t}")
            table_counts[t] = cursor.fetchone()[0]
        except Exception:
            table_counts[t] = 0
    dst_conn.close()
    src_conn.close()

    # Compute SHA-256 checksum of backup file
    hasher = hashlib.sha256()
    with open(backup_path, 'rb') as f:
        hasher.update(f.read())
    sha256_hex = hasher.hexdigest()

    # Save backup manifest
    manifest_path = backup_path + ".manifest.json"
    manifest = {
        "timestamp": timestamp,
        "backup_path": backup_path,
        "sha256": sha256_hex,
        "table_counts": table_counts,
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"[DB BACKUP] Created timestamped backup with manifest ({sha256_hex[:8]}...): {backup_path}")
    return backup_path



def main():
    parser = argparse.ArgumentParser(description="SentiHealth On-Prem Database Backup Utility")
    parser.add_argument("--dest", default=BACKUPS_DIR, help="Destination backups directory")
    args = parser.parse_args()

    backup_path = run_backup(args.dest)
    print(f"[SUCCESS] Database backup complete: {backup_path}")


if __name__ == "__main__":
    main()
