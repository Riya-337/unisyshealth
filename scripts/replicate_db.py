"""
SentiHealth Logical Volume Database Replication Utility.

Replicates database state to a secondary independent target volume/directory
(e.g., data/replicas/ or a secondary on-prem mount).
"""

import argparse
import os
import sqlite3
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import APP_DB, DATA_DIR

REPLICAS_DIR = os.path.join(DATA_DIR, "replicas")


def replicate_database(target_dir: str = REPLICAS_DIR) -> str:
    os.makedirs(target_dir, exist_ok=True)
    replica_path = os.path.join(target_dir, "app_replica.db")

    if not os.path.exists(APP_DB):
        conn = sqlite3.connect(APP_DB)
        conn.close()

    # Online backup to secondary volume
    src_conn = sqlite3.connect(APP_DB)
    dst_conn = sqlite3.connect(replica_path)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    print(f"[DB REPLICATION] Synchronized replica DB to: {replica_path}")
    return replica_path


def main():
    parser = argparse.ArgumentParser(description="SentiHealth Database Replication Utility")
    parser.add_argument("--target", default=REPLICAS_DIR, help="Target replica directory")
    args = parser.parse_args()

    replica_path = replicate_database(args.target)
    print(f"[SUCCESS] Database replication complete: {replica_path}")


if __name__ == "__main__":
    main()
