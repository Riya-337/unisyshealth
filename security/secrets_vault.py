"""
secrets_vault.py — Permission-restricted local secrets storage and rotation manager.

Stores application secrets (SESSION_SECRET, chain_key, db_credentials) in:
  config/.secrets_vault.json (Permissions: 0600, Owner-Read-Only)

Note on deployment scale:
  This local vault is an intentional, permission-restricted scope reduction
  designed for single-host, lightweight on-premises hospital deployments
  without dedicated HashiCorp Vault infrastructure.
"""

import json
import os
import sys
import secrets
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from _paths import CONFIG_DIR, CHAIN_KEY_FILE

VAULT_FILE = os.path.join(CONFIG_DIR, ".secrets_vault.json")
_DEFAULT_FALLBACK_SECRET = b"sentihealth-sentinel-v2-master-key-change-in-prod"


def _ensure_vault_exists() -> dict:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(VAULT_FILE):
        try:
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            pass

    # If legacy .chain_key file exists, incorporate its raw bytes as hex
    session_secret_hex = secrets.token_hex(32)
    if os.path.exists(CHAIN_KEY_FILE):
        try:
            with open(CHAIN_KEY_FILE, "rb") as f:
                k_bytes = f.read()
                if k_bytes:
                    session_secret_hex = k_bytes.hex()
        except Exception:
            pass

    initial_vault = {
        "_version": "1.0",
        "_scope_note": "Intentional local 0600 permission-restricted vault for single-host on-prem deployment.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_rotated_at": datetime.now(timezone.utc).isoformat(),
        "SESSION_SECRET": session_secret_hex,
        "CHAIN_KEY": session_secret_hex,
    }


    tmp = VAULT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(initial_vault, f, indent=2)
    os.replace(tmp, VAULT_FILE)
    os.chmod(VAULT_FILE, 0o600)
    return initial_vault


def get_secret(key_name: str, fallback_bytes: bytes = None) -> bytes:
    """Retrieve a secret by key name, returning bytes for HMAC/cryptography."""
    vault = _ensure_vault_exists()
    val = vault.get(key_name)
    if val:
        try:
            return bytes.fromhex(val)
        except ValueError:
            return val.encode("utf-8")
    if fallback_bytes is not None:
        return fallback_bytes
    return _DEFAULT_FALLBACK_SECRET


def get_secret_str(key_name: str, fallback: str = "") -> str:
    """Retrieve a secret as a string."""
    vault = _ensure_vault_exists()
    return vault.get(key_name, fallback)


def set_secret(key_name: str, value: str) -> None:
    """Write or update a secret in the vault."""
    vault = _ensure_vault_exists()
    vault[key_name] = value
    vault["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = VAULT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(vault, f, indent=2)
    os.replace(tmp, VAULT_FILE)
    os.chmod(VAULT_FILE, 0o600)


def rotate_secret(key_name: str) -> tuple[str, str]:
    """
    Rotate a secret by generating a new 32-byte hex value.
    Returns (old_value, new_value).
    """
    vault = _ensure_vault_exists()
    old_val = vault.get(key_name, "")
    new_val = secrets.token_hex(32)
    vault[key_name] = new_val
    vault["last_rotated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = VAULT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(vault, f, indent=2)
    os.replace(tmp, VAULT_FILE)
    os.chmod(VAULT_FILE, 0o600)
    return old_val, new_val
