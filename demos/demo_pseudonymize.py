import os
import sys
import json

# Ensure project root is on sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from privacy.pseudonymize import pseudonymize_event

# 1. Define raw telemetry event with sensitive identifiers
raw_event = {
  "event_id": "a532edcc-cfce-4e9b-963b-f28d59658d50",
  "source_ip": "211.166.26.12",
  "ip_address": "211.166.26.12",
  "endpoint": "/patients",
  "features": {
    "failed_logins": 2,
    "user_id": "U_SIM",
    "role": "it_staff"
  }
}

print("="*60)
print("🛡️  SENTINELHEALTH PSEUDONYMIZATION DEMO")
print("="*60)
print("Raw Event (contains sensitive IP and User ID):")
print(json.dumps(raw_event, indent=2))
print("")

# 2. Run pseudonymization
print("[*] Processing event through pseudonymize_event()...")
processed_event = pseudonymize_event(raw_event)
print("")

print("Pseudonymized Event (safe to log publicly or share):")
print(json.dumps(processed_event, indent=2))
print("="*60)

# Explain how the stability is maintained
salt_path = os.path.join("config", "pseudonym_salt.bin")
print(f"✅ Secure Salt File used: {salt_path}")
print("   - This file contains 32 random bytes generated once and stored locally.")
print("   - As long as the salt remains unchanged, the same IP and User ID will")
print("     always resolve to the exact same 16-character token.")
print("   - This allows security models to track behaviors over time without")
print("     ever exposing the actual underlying identity.")
print("="*60)
