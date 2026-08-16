import unittest
import json
import os
import pyotp
from unittest.mock import patch

import sys
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Setup paths
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)


from dashboard import app, init_db, load_users, save_users, _hash_password, _generate_backup_codes

class TestMFA(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Initialize clean test user database
        self.totp_secret = pyotp.random_base32()
        self.raw_codes, self.hashed_codes = _generate_backup_codes(8)
        
        users = {
            "testadmin": {
                "password": _hash_password("adminpass123"),
                "role": "admin",
                "status": "approved",
                "totp_secret": self.totp_secret,
                "mfa_backup_codes": list(self.hashed_codes),
            }
        }
        save_users(users)

    def test_mfa_totp_login_success(self):
        # 1. Login with password
        res1 = self.app.post('/api/auth/login', json={
            "username": "testadmin",
            "password": "adminpass123"
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json.get("stage"), "otp")

        # 2. Verify TOTP code
        totp = pyotp.TOTP(self.totp_secret)
        code = totp.now()
        res2 = self.app.post('/api/auth/verify-otp', json={
            "username": "testadmin",
            "code": code
        })
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json.get("success"))
        self.assertIn("token", res2.json)

    def test_mfa_invalid_totp_rejection(self):
        # Login with valid password but invalid TOTP code
        res1 = self.app.post('/api/auth/login', json={
            "username": "testadmin",
            "password": "adminpass123"
        })
        self.assertEqual(res1.status_code, 200)

        res2 = self.app.post('/api/auth/verify-otp', json={
            "username": "testadmin",
            "code": "000000"
        })
        self.assertEqual(res2.status_code, 401)
        self.assertFalse(res2.json.get("success"))

    def test_mfa_backup_code_redemption(self):
        # Use first raw backup code
        backup_code = self.raw_codes[0]
        res = self.app.post('/api/auth/verify-otp', json={
            "username": "testadmin",
            "code": backup_code
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json.get("success"))

        # Verify backup code is single-use and rejected on second attempt
        res_repeat = self.app.post('/api/auth/verify-otp', json={
            "username": "testadmin",
            "code": backup_code
        })
        self.assertEqual(res_repeat.status_code, 401)

    @patch('notifications.sentinel_notifier.resolve_challenge')
    def test_step_up_mfa_on_challenge_response(self, mock_resolve):
        mock_resolve.return_value = True

        # Login to get valid session token
        totp = pyotp.TOTP(self.totp_secret)
        code = totp.now()
        login_res = self.app.post('/api/auth/verify-otp', json={
            "username": "testadmin",
            "code": code
        })
        token = login_res.json["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Attempt response WITHOUT step-up TOTP code -> 401
        res_no_mfa = self.app.post('/api/alerts/inc_123/respond', headers=headers, json={
            "decision": "YES"
        })
        self.assertEqual(res_no_mfa.status_code, 401)
        self.assertIn("Step-up MFA authorization failed", res_no_mfa.json["message"])

        # 2. Attempt response WITH valid step-up TOTP code -> 200
        valid_totp = totp.now()
        res_with_mfa = self.app.post('/api/alerts/inc_123/respond', headers=headers, json={
            "decision": "YES",
            "totp_code": valid_totp
        })
        self.assertEqual(res_with_mfa.status_code, 200)
        self.assertTrue(res_with_mfa.json["success"])

    def test_users_json_tamper_detected(self):
        from _paths import USERS_FILE, TAMPER_ALERTS
        
        # 1. Ensure clean save_users creates valid HMAC
        save_users({"testadmin": {"role": "admin"}})

        # Clear tamper alert log for clean test
        if os.path.exists(TAMPER_ALERTS):
            os.remove(TAMPER_ALERTS)

        # 2. Perform out-of-band edit directly on disk without updating HMAC
        with open(USERS_FILE, "w") as f:
            json.dump({"testadmin": {"role": "admin", "tampered": True}}, f)

        # 3. Call load_users() and verify tamper alert logged
        load_users()
        self.assertTrue(os.path.exists(TAMPER_ALERTS))
        with open(TAMPER_ALERTS, "r") as f:
            log_content = f.read()
        self.assertIn("[USERS.JSON TAMPERING DETECTED]", log_content)

    def test_mfa_recovery_writes_audit_chain(self):
        import tempfile
        import self_healing_responder
        import scripts.admin_mfa_recovery
        import _paths

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_chain = os.path.join(tmpdir, "audit_chain.json")
            tmp_replica = os.path.join(tmpdir, "audit_chain_replica.json")

            with patch.object(_paths, 'AUDIT_CHAIN', tmp_chain), \
                 patch.object(_paths, 'AUDIT_CHAIN_REPLICA', tmp_replica), \
                 patch.object(self_healing_responder, 'AUDIT_CHAIN', tmp_chain), \
                 patch.object(self_healing_responder, 'AUDIT_CHAIN_REPLICA', tmp_replica):


                from scripts.admin_mfa_recovery import generate_backup_codes, _audit_log_recovery_action

                raw_codes, hashed_codes = generate_backup_codes(4)
                save_users({"recoveryuser": {"role": "admin", "totp_secret": pyotp.random_base32(), "mfa_backup_codes": list(hashed_codes)}})

                # Log recovery action
                _audit_log_recovery_action("BACKUP_CODE_REDEEMED_USER_recoveryuser")

                # Verify audit chain block written
                self.assertTrue(os.path.exists(tmp_chain))
                self.assertTrue(os.path.exists(tmp_replica))
                with open(tmp_chain, "r") as f:
                    chain = json.load(f)

                actions = [b.get("action", "") for b in chain if isinstance(b, dict)]
                self.assertTrue(any("BACKUP_CODE_REDEEMED_USER_recoveryuser" in act for act in actions))


    def test_emergency_ip_unblock_writes_audit_chain(self):
        import tempfile
        import self_healing_responder
        import scripts.emergency_unblock_ip
        import _paths

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_chain = os.path.join(tmpdir, "audit_chain.json")
            tmp_replica = os.path.join(tmpdir, "audit_chain_replica.json")
            tmp_blocked = os.path.join(tmpdir, "blocked_ips.json")

            with patch.object(_paths, 'AUDIT_CHAIN', tmp_chain), \
                 patch.object(_paths, 'AUDIT_CHAIN_REPLICA', tmp_replica), \
                 patch.object(_paths, 'BLOCKED_IPS', tmp_blocked), \
                 patch.object(self_healing_responder, 'AUDIT_CHAIN', tmp_chain), \
                 patch.object(self_healing_responder, 'AUDIT_CHAIN_REPLICA', tmp_replica), \
                 patch.object(scripts.emergency_unblock_ip, 'AUDIT_CHAIN', tmp_chain), \
                 patch.object(scripts.emergency_unblock_ip, 'AUDIT_CHAIN_REPLICA', tmp_replica), \
                 patch.object(scripts.emergency_unblock_ip, 'BLOCKED_IPS', tmp_blocked):

                from scripts.emergency_unblock_ip import unblock_ips

                # Seed blocked IP list
                with open(tmp_blocked, "w") as f:
                    json.dump([{"ip": "192.168.1.100", "reason": "test"}], f)

                # Run emergency unblock
                success = unblock_ips(ip_address="192.168.1.100", operator="op_dr", reason="Emergency ER access", outage_log=True)
                self.assertTrue(success)

                # Assert IP unblocked
                with open(tmp_blocked, "r") as f:
                    blocked = json.load(f)
                self.assertEqual(len(blocked), 0)

                # Assert audit chain block appended with operator, reason, and outage fields
                with open(tmp_chain, "r") as f:
                    chain = json.load(f)

                unblock_blocks = [b for b in chain if isinstance(b, dict) and "EMERGENCY_UNBLOCK_IP_192.168.1.100" in b.get("action", "")]
                self.assertGreater(len(unblock_blocks), 0)
                last_b = unblock_blocks[-1]
                self.assertEqual(last_b.get("operator"), "op_dr")
                self.assertEqual(last_b.get("actions_taken_during_outage"), "Emergency ER access")
                self.assertTrue(last_b.get("outage_post_incident"))



if __name__ == '__main__':
    unittest.main()


