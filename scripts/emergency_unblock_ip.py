"""
SentiHealth Emergency IP Unblock Utility.

Clears blocked IPs from logs/blocked_ips.json while maintaining compliance
with Constitution Article IV.2 by writing an HMAC-signed audit block to audit_chain.json.
Supports --outage-log mode for logging actions taken during host outages after system recovery.
"""

import argparse
import hashlib
import hmac as _hmac
import json
import os
import sys
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import BLOCKED_IPS, AUDIT_CHAIN, AUDIT_CHAIN_REPLICA, DATA_DIR


def unblock_ips(ip_address: str = None, operator: str = "admin", reason: str = "Emergency manual override", outage_log: bool = False) -> bool:
    # 1. Update blocked_ips.json
    os.makedirs(os.path.dirname(BLOCKED_IPS), exist_ok=True)
    if os.path.exists(BLOCKED_IPS):
        try:
            with open(BLOCKED_IPS, 'r') as f:
                blocked = json.load(f)
        except Exception:
            blocked = []
    else:
        blocked = []

    if ip_address:
        blocked = [entry for entry in blocked if (isinstance(entry, dict) and entry.get('ip') != ip_address) or (isinstance(entry, str) and entry != ip_address)]
        action_name = f"EMERGENCY_UNBLOCK_IP_{ip_address}"
    else:
        blocked = []
        action_name = "EMERGENCY_UNBLOCK_ALL_IPS"

    with open(BLOCKED_IPS, 'w') as f:
        json.dump(blocked, f, indent=2)

    print(f"[EMERGENCY OVERRIDE] Blocked IP list updated. Target: {ip_address if ip_address else 'ALL'}")

    # 2. Write HMAC-signed audit block if audit chain is accessible
    try:
        from self_healing_responder import _write_chain_atomic, _block_hmac
        from scoring_matrix import SESSION_SECRET

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
                "event_id": f"emergency_override_{block_idx}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tier": "High",
                "action": action_name,
                "operator": operator,
                "auth_level": "unauthenticated_emergency_override",
                "reason": reason,
                "actions_taken_during_outage": reason if outage_log else None,
                "outage_post_incident": outage_log,
                "prev_hash": prev_hash,
            }

            block_data["block_hmac"] = _block_hmac(block_data, SESSION_SECRET)
            entry_for_hash = {k: v for k, v in block_data.items() if k not in ('entry_hash', 'block_hmac')}
            block_data["entry_hash"] = hashlib.sha256((prev_hash + json.dumps(entry_for_hash, sort_keys=True)).encode()).hexdigest()
            chain.append(block_data)
            _write_chain_atomic(chain, path=p)

        print(f"[AUDIT LOG SUCCESS] Written {action_name} block to audit ledgers.")
        return True
    except Exception as e:
        print(f"[AUDIT LOG WARNING] Could not write audit chain block immediately ({e}). Operator MUST log post-recovery with --outage-log!")
        return False


def main():
    parser = argparse.ArgumentParser(description="SentiHealth Emergency Manual IP Unblock & Audit Logger")
    parser.add_argument("--ip", help="Specific IP address to unblock (omit to unblock ALL IPs)")
    parser.add_argument("--operator", default="admin", help="Operator name or ID performing override")
    parser.add_argument("--reason", default="Emergency clinical override", help="Clinical justification or ticket reference")
    parser.add_argument("--outage-log", action="store_true", help="Flag as post-incident audit logging for actions taken during host outage")
    args = parser.parse_args()

    unblock_ips(ip_address=args.ip, operator=args.operator, reason=args.reason, outage_log=args.outage_log)


if __name__ == "__main__":
    main()
