"""
SentiHealth Operator-Authorized Audit Chain Restoration CLI.

Used by hospital IT administrators to manually inspect audit chain discrepancies
and authorize restoration of audit_chain.json from audit_chain_replica.json (or vice versa).
Requires explicit human operator confirmation (--confirm-restore).
"""

import argparse
import json
import os
import shutil
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import AUDIT_CHAIN, AUDIT_CHAIN_REPLICA, LOGS_DIR, TAMPER_ALERTS


def inspect_chains():
    print("\n" + "=" * 60)
    print(" SentiHealth Audit Chain Replication Status")
    print("=" * 60)

    p_exists = os.path.exists(AUDIT_CHAIN)
    r_exists = os.path.exists(AUDIT_CHAIN_REPLICA)

    print(f" Primary Chain Path   : {AUDIT_CHAIN} (Exists: {p_exists})")
    print(f" Replica Chain Path   : {AUDIT_CHAIN_REPLICA} (Exists: {r_exists})")

    p_len = 0
    r_len = 0

    if p_exists:
        try:
            with open(AUDIT_CHAIN, 'r') as f:
                p_data = json.load(f)
                p_len = len(p_data)
                print(f" Primary Block Count  : {p_len}")
        except Exception as e:
            print(f" Primary Read Error   : {e}")

    if r_exists:
        try:
            with open(AUDIT_CHAIN_REPLICA, 'r') as f:
                r_data = json.load(f)
                r_len = len(r_data)
                print(f" Replica Block Count  : {r_len}")
        except Exception as e:
            print(f" Replica Read Error   : {e}")

    if p_exists and r_exists:
        if p_len == r_len:
            print(" Consistency Status   : Block count match")
        else:
            print(f" Consistency Status   : DISCREPANCY DETECTED (Primary: {p_len}, Replica: {r_len})")
    else:
        print(" Consistency Status   : ONE OR BOTH FILES MISSING")

    print("=" * 60 + "\n")


def restore_chain(from_replica: bool, confirm: bool):
    src = AUDIT_CHAIN_REPLICA if from_replica else AUDIT_CHAIN
    dst = AUDIT_CHAIN if from_replica else AUDIT_CHAIN_REPLICA

    if not os.path.exists(src):
        print(f"[ERROR] Source audit file does not exist: {src}")
        sys.exit(1)

    if not confirm:
        print("[ABORTED] Restoration requires explicit confirmation flag '--confirm-restore'.")
        print(f"To execute: python3 scripts/restore_audit_chain.py --{'restore-from-replica' if from_replica else 'restore-from-primary'} --confirm-restore")
        sys.exit(1)

    # Validate source file JSON integrity before restoring
    try:
        with open(src, 'r') as f:
            data = json.load(f)
            if not isinstance(data, list) or not data:
                raise ValueError("Source chain file is empty or not a valid JSON array")
    except Exception as e:
        print(f"[ERROR] Cannot restore from invalid JSON file {src}: {e}")
        sys.exit(1)

    # Atomic copy
    tmp = dst + '.tmp'
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)

    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(TAMPER_ALERTS, 'a') as f:
        f.write(f"[OPERATOR RESTORE] Manual restoration executed from {src} -> {dst}\n")

    print(f"[OPERATOR RESTORE SUCCESS] Restored audit ledger: {src} -> {dst}")


def main():
    parser = argparse.ArgumentParser(description="Operator-Authorized Audit Chain Restoration Tool")
    parser.add_argument("--status", action="store_true", help="Inspect primary vs replica status")
    parser.add_argument("--restore-from-replica", action="store_true", help="Authorize restoring primary from replica")
    parser.add_argument("--restore-from-primary", action="store_true", help="Authorize restoring replica from primary")
    parser.add_argument("--confirm-restore", action="store_true", help="Explicit human sign-off for restoration")
    args = parser.parse_args()

    if args.restore_from_replica:
        restore_chain(from_replica=True, confirm=args.confirm_restore)
    elif args.restore_from_primary:
        restore_chain(from_replica=False, confirm=args.confirm_restore)
    else:
        inspect_chains()



if __name__ == "__main__":
    main()
