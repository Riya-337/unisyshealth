import unittest
from unittest.mock import patch
import os
import sqlite3
import shutil
from datetime import datetime, timezone


_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
from _paths import APP_DB, DATA_DIR

from database import DatabaseManager
from scripts.backup_db import run_backup
from scripts.replicate_db import replicate_database
from scripts.restore_db import restore_database

class TestDatabaseBackup(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(DATA_DIR, "test_db_run")
        self.test_db = os.path.join(self.test_dir, "test_app.db")
        os.makedirs(self.test_dir, exist_ok=True)

        # Populate initial test database
        db_mgr = DatabaseManager(db_path=self.test_db)
        db_mgr.log_event("evt_001", "High", 0.95, "10.0.0.1", {"attack": "test"})

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_backup_replication_and_restore(self):
        # 1. Backup DB
        backup_dir = os.path.join(self.test_dir, "backups")
        
        # Override APP_DB temporarily for testing
        with patch('scripts.backup_db.APP_DB', self.test_db):
            backup_path = run_backup(dest_dir=backup_dir)
            self.assertTrue(os.path.exists(backup_path))

        # 2. Replicate DB
        replica_dir = os.path.join(self.test_dir, "replicas")
        with patch('scripts.replicate_db.APP_DB', self.test_db):
            replica_path = replicate_database(target_dir=replica_dir)
            self.assertTrue(os.path.exists(replica_path))


        # 3. Simulate Database Corruption/Loss
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE system_events;")
        conn.commit()
        conn.close()

        # Verify corruption
        conn2 = sqlite3.connect(self.test_db)
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_events';")
        self.assertIsNone(cursor2.fetchone())
        conn2.close()

        # 4. Restore from backup
        restore_success = restore_database(backup_path, target_db=self.test_db)
        self.assertTrue(restore_success)

        # 5. Verify restored data
        conn3 = sqlite3.connect(self.test_db)
        cursor3 = conn3.cursor()
        cursor3.execute("SELECT event_id, tier, raw_score FROM system_events WHERE event_id='evt_001';")
        row = cursor3.fetchone()
        conn3.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "evt_001")
        self.assertEqual(row[1], "High")
        self.assertEqual(row[2], 0.95)


if __name__ == '__main__':
    unittest.main()
