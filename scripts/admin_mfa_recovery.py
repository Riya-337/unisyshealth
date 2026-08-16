"""
SentiHealth Admin MFA Break-Glass Recovery Tool.

Allows system administrators on the local server console to redeem an emergency backup code,
reset TOTP MFA secrets, or view MFA status for registered users when locked out.

Usage:
    python3 scripts/admin_mfa_recovery.py --user admin --status
    python3 scripts/admin_mfa_recovery.py --user admin --redeem 12345678
    python3 scripts/admin_mfa_recovery.py --user admin --reset-totp
"""

import argparse
import hashlib
import json
import os
import secrets
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import USERS_FILE, DATA_DIR

try:
    import pyotp
    _HAS_PYOTP = True
except ImportError:
    _HAS_PYOTP = False


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def generate_backup_codes(count: int = 8) -> tuple[list[str], list[str]]:
    """Generate (raw_codes, hashed_codes)."""
    raw_codes = [f"{secrets.randbelow(100000000):08d}" for _ in range(count)]
    hashed_codes = [_hash_code(c) for c in raw_codes]
    return raw_codes, hashed_codes


def load_users_data() -> dict:
    from dashboard import load_users
    return load_users()


def save_users_data(users: dict):
    from dashboard import save_users
    save_users(users)



def _audit_log_recovery_action(action_name: str):
    """Write an HMAC-signed, hash-linked block to primary and replica audit ledgers."""
    from _paths import AUDIT_CHAIN, AUDIT_CHAIN_REPLICA, DATA_DIR
    from self_healing_responder import _write_chain_atomic, _block_hmac
    from scoring_matrix import SESSION_SECRET
    from datetime import datetime, timezone
    import json
    import hashlib
    import hmac as _hmac


    os.makedirs(DATA_DIR, exist_ok=True)
    for p in (AUDIT_CHAIN, AUDIT_CHAIN_REPLICA):
        if not os.path.exists(p):
            genesis_data = {"block_index": 0}
            genesis_str = json.dumps(genesis_data, sort_keys=True)
            genesis = {
                "block_index": 0,
                "entry_hash": hashlib.sha256(b"genesis").hexdigest(),
                "block_hmac": _hmac.new(SESSION_SECRET, genesis_str.encode(), hashlib.sha256).hexdigest(),
            }
            chain = [genesis]
        else:
            with open(p, 'r') as f:
                chain = json.load(f)

        prev_hash = chain[-1]['entry_hash']
        block_idx = len(chain)
        block_data = {
            "block_index": block_idx,
            "event_id": f"mfa_recovery_{block_idx}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tier": "High",
            "action": action_name,
            "prev_hash": prev_hash,
        }
        block_data["block_hmac"] = _block_hmac(block_data, SESSION_SECRET)
        entry_for_hash = {k: v for k, v in block_data.items() if k not in ('entry_hash', 'block_hmac')}
        block_data["entry_hash"] = hashlib.sha256((prev_hash + json.dumps(entry_for_hash, sort_keys=True)).encode()).hexdigest()
        chain.append(block_data)
        _write_chain_atomic(chain, path=p)


def main():
    parser = argparse.ArgumentParser(description="SentiHealth Admin MFA Recovery Tool")
    parser.add_argument("--user", default="admin", help="Username to inspect/recover")
    parser.add_argument("--status", action="store_true", help="Display user MFA status")
    parser.add_argument("--redeem", help="Redeem an 8-digit emergency backup code")
    parser.add_argument("--reset-totp", action="store_true", help="Reset TOTP secret and generate new backup codes")
    args = parser.parse_args()

    users = load_users_data()
    if args.user not in users:
        print(f"[ERROR] User '{args.user}' not found in {USERS_FILE}")
        sys.exit(1)

    user = users[args.user]

    if args.status or (not args.redeem and not args.reset_totp):
        print("\n" + "=" * 50)
        print(f" MFA Status for '{args.user}'")
        print("=" * 50)
        print(f" Role               : {user.get('role')}")
        print(f" Status             : {user.get('status')}")
        print(f" TOTP Secret Set    : {'YES' if user.get('totp_secret') else 'NO'}")
        if user.get('totp_secret'):
            print(f" TOTP Secret        : {user.get('totp_secret')}")
        backup_count = len(user.get('mfa_backup_codes', []))
        print(f" Backup Codes Left  : {backup_count}")
        print("=" * 50 + "\n")
        return

    if args.redeem:
        raw_code = args.redeem.strip()
        code_hash = _hash_code(raw_code)
        codes = user.get('mfa_backup_codes', [])
        if code_hash in codes:
            codes.remove(code_hash)
            user['mfa_backup_codes'] = codes
            save_users_data(users)
            
            # Log privileged recovery action to audit chain
            _audit_log_recovery_action(f"BACKUP_CODE_REDEEMED_USER_{args.user}")

            print(f"[SUCCESS] Backup code redeemed for user '{args.user}'. {len(codes)} remaining codes left.")
        else:
            print(f"[REJECTED] Invalid or already used backup code for '{args.user}'.")
            sys.exit(1)

    if args.reset_totp:
        if not _HAS_PYOTP:
            print("[ERROR] pyotp package required to generate TOTP secret.")
            sys.exit(1)

        new_secret = pyotp.random_base32()
        raw_codes, hashed_codes = generate_backup_codes(8)
        user['totp_secret'] = new_secret
        user['mfa_backup_codes'] = hashed_codes
        save_users_data(users)

        # Log privileged recovery action to audit chain
        _audit_log_recovery_action(f"ADMIN_TOTP_RESET_USER_{args.user}")

        print("\n" + "=" * 60)


        print(f" [MFA RESET SUCCESSFUL] New credentials for '{args.user}'")
        print("=" * 60)
        print(f" TOTP Secret Key : {new_secret}")
        print(" Emergency Backup Recovery Codes (Save these in a secure offline location):")
        for i, c in enumerate(raw_codes, 1):
            print(f"   {i}. {c}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
