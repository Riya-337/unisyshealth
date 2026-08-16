# SentiHealth — Secrets Management & Rotation Runbook

> **Scope Note:** `config/.secrets_vault.json` (Permissions: `0600`, Owner-Read-Only) is an **intentional, permission-restricted scope reduction** designed for single-host, lightweight on-premises hospital deployments without dedicated HashiCorp Vault infrastructure. For enterprise multi-node deployments requiring process separation, access auditing, and secret leasing, a self-hosted HashiCorp Vault cluster can be integrated.

---

## 1. Managed Secrets Overview

| Secret Identifier | Storage Location | Default Permission | Purpose & Impact if Rotated |
|-------------------|------------------|--------------------|-----------------------------|
| `SESSION_SECRET` | `config/.secrets_vault.json` | `0600` | Used for audit chain HMAC signatures (`_block_hmac`) and `users.json` HMAC verification. Rotating invalidates existing HMAC signatures until re-signed. |
| `CHAIN_KEY` | `config/.secrets_vault.json` | `0600` | Backup cryptographic seed for audit chain verification. |
| `TLS_KEY` | `config/certs/server.key` | `0600` | Private key for local HTTPS/TLS connections. |

---

## 2. Secret Rotation Frequency

- **`SESSION_SECRET` & `CHAIN_KEY`:** Rotate every 180 days or immediately following a suspected administrative credential compromise.
- **`TLS_KEY` & `TLS_CRT`:** Regenerate annually (365 days) via `python3 scripts/generate_tls_certs.py`.

---

## 3. Step-by-Step Secret Rotation Procedures

### 3.1 Rotating `SESSION_SECRET` (HMAC Master Key)

> [!WARNING]
> Rotating `SESSION_SECRET` invalidates the HMAC signature on `data/users.json`. You **MUST** run the user re-signing sequence immediately after rotation to avoid `users.json` tamper detection errors on startup.

```bash
# 1. Stop active SentiHealth services
killall python3 2>/dev/null || true

# 2. Execute secret rotation in Python
python3 -c "import secrets_vault; old, new = secrets_vault.rotate_secret('SESSION_SECRET'); print('Rotated SESSION_SECRET successfully')"

# 3. Re-sign data/users.json with the new SESSION_SECRET
python3 -c "from dashboard import load_users, save_users; save_users(load_users()); print('users.json re-signed successfully')"

# 4. Verify system startup and audit chain integrity
python3 -c "from self_healing_responder import verify_chain_integrity; assert verify_chain_integrity(), 'Chain verification failed'"
```

---

### 3.2 Regenerating TLS Certificates (`server.key` / `server.crt`)

```bash
# Force certificate regeneration
rm -f config/certs/server.key config/certs/server.crt
python3 scripts/generate_tls_certs.py
```

---

## 4. Emergency Secret Rollback Procedure

If a secret rotation causes unexpected service disruption:
1. Open `config/.secrets_vault.json`.
2. Restore the previous hex value for `SESSION_SECRET` from system backup or administrative vault archive.
3. Re-sign `users.json` via `python3 -c "from dashboard import load_users, save_users; save_users(load_users())"`.
4. Restart services.
