# Disaster Recovery & Emergency Manual Override Runbook
## SentiHealth — Zero-Cloud Healthcare Cybersecurity Platform

**Version:** 1.0  
**Status:** Active Operational Runbook  
**Last Updated:** 2026-08-15

---

## 1. Executive Emergency Principle

> **Constitution Article V.1 & V.2:** *"When in doubt between security (blocking a potentially malicious user) and clinical availability (allowing a clinician to access EHR during an emergency), the system MUST escalate to a human admin rather than making an autonomous lockout decision. Hospital IT staff must always have a documented, tested manual override procedure to restore access even if SentiHealth is fully locked down or offline."*

---

## 2. Host Machine Failure & Emergency Manual Override

### 2.1 Scenario: Sentinel Host Hardware Failure
If the SentiHealth Sentinel server host fails (hardware crash, kernel panic, power loss), the target EHR web application continues running independently on its dedicated host.
- **Impact:** Live monitoring and automated throttling stop; EHR server remains accessible to clinical staff.
- **Action:**
  1. Hospital IT staff log in to the EHR web app host directly.
  2. Verify that network routing and firewall tables have not been left in a throttled/blocked state by running:
     ```bash
     # Unblock all IPs in local IP blocklist table with audit logging
     python3 scripts/emergency_unblock_ip.py --operator "admin" --reason "Sentinel host hardware failure recovery"
     ```
  3. **Outage Post-Incident Logging:** If the Sentinel server was offline when the override was executed, run the post-incident audit logging command immediately after Sentinel system restoration to maintain compliance with Constitution Article IV.2 ("no off-the-record actions"):
     ```bash
     python3 scripts/emergency_unblock_ip.py --operator "admin" --reason "Actions taken during hardware failure outage: cleared all IP blocks" --outage-log
     ```
  4. Restart SentiHealth Sentinel process on backup standby hardware or secondary node:
     ```bash
     source .venv/bin/activate
     python3 live_sentinel.py
     ```

### 2.2 Scenario: False-Positive Emergency Lockout (Clinical Override)
If a clinician or critical workstation is accidentally locked out during an emergency:
1. **Immediate Release via Dashboard (UI):**
   - Admin logs in to `http://localhost:5001`.
   - Navigates to **Stasis Queue / Blocked IPs**.
   - Clicks **Release IP / Unlock Account** and submits TOTP step-up authorization code (automatically logs action to audit chain).
2. **CLI Emergency Break-Glass Override:**
   - If dashboard is inaccessible, run the emergency unblock script on the sentinel host:
     ```bash
     # Unblock specific clinician IP with logged justification
     python3 scripts/emergency_unblock_ip.py --ip "192.168.1.100" --operator "dr_smith" --reason "Emergency ER patient record access"
     ```
   *Note: `scripts/emergency_unblock_ip.py` updates `logs/blocked_ips.json` and appends an HMAC-signed audit block (`EMERGENCY_UNBLOCK_IP_<IP>`) to `data/audit_chain.json` and `data/audit_chain_replica.json`.*

### 2.3 Emergency Admin MFA Break-Glass Recovery Protocol
If an administrative account is locked out due to a lost TOTP authentication device or depleted emergency backup recovery codes:

1. **Inspect User MFA Status:**
   ```bash
   python3 scripts/admin_mfa_recovery.py --user admin --status
   ```
2. **Redeem One-Time Backup Recovery Code:**
   ```bash
   python3 scripts/admin_mfa_recovery.py --user admin --redeem 12345678
   ```
3. **Reset TOTP Secret & Regenerate Fresh Backup Codes:**
   ```bash
   python3 scripts/admin_mfa_recovery.py --user admin --reset-totp
   ```
*Security & Compliance Guardrail:* Every invocation of `scripts/admin_mfa_recovery.py` automatically writes an HMAC-signed, hash-linked block (`BACKUP_CODE_REDEEMED_USER_<user>` or `ADMIN_TOTP_RESET_USER_<user>`) to both primary and replica audit ledgers.

---

## 3. Facility-Wide Power & Network Outage Recovery

### 3.1 Facility Outage Checklist & Startup Order
- [ ] Restore electrical power to EHR web server and Sentinel monitoring node.
- [ ] Verify local hospital LAN switch/router status (WAN internet connectivity is NOT required; SentiHealth operates 100% zero-cloud).
- [ ] Export `DATABASE_URL` if using PostgreSQL high-availability database cluster.
- [ ] Initialize database schema: `python3 database.py`.
- [ ] Start target EHR server (`cd webapp && node app.js`).
- [ ] Start SentiHealth dashboard backend (`python3 dashboard.py`).
- [ ] Complete first-time admin TOTP enrollment and **change default initial bootstrap password immediately** (`http://localhost:5001` or break-glass CLI `scripts/admin_mfa_recovery.py`).

- [ ] Launch `local_notifier_client.py` on admin workstations across the LAN.
- [ ] Start SentiHealth live sentinel AI engine (`python3 live_sentinel.py`).
- [ ] Verify audit chain integrity: `verify_chain_integrity()` runs automatically on startup.


---

## 4. Audit Ledger Corruption & Operator Restoration (`HALTED_CORRUPTION`)

### 4.1 Trigger Condition
If `verify_chain_integrity()` detects primary chain corruption, SHA-256 hash mismatch, HMAC signature failure, or a discrepancy between `audit_chain.json` and `audit_chain_replica.json`:
1. Processing immediately halts with `HALTED_CORRUPTION`.
2. A critical security alert is logged to `logs/tamper_alerts.log`.
3. **No automatic unattended overwrite occurs.**

### 4.2 Operator Restoration Runbook
To manually inspect discrepancy and authorize restoration from the replica:

1. **Inspect Chain Status:**
   ```bash
   python3 scripts/restore_audit_chain.py --status
   ```
   *Outputs block counts, integrity checks, and file existence for both primary and replica files.*

2. **Execute Operator-Authorized Restoration:**
   - Restore primary from validated replica:
     ```bash
     python3 scripts/restore_audit_chain.py --restore-from-replica --confirm-restore
     ```
   - Or sync replica from primary:
     ```bash
     python3 scripts/restore_audit_chain.py --restore-from-primary --confirm-restore
     ```

3. **Verify Integrity & Resume Processing:**
   ```bash
   python3 -c "from self_healing_responder import verify_chain_integrity; print('Chain OK' if verify_chain_integrity() else 'STILL CORRUPTED')"
   ```

---

## 5. Database Backup, Restoration & PostgreSQL Replication Runbook

### 5.1 Manual & Scheduled Database Backups
To create an instant online snapshot of `data/app.db`:
```bash
python3 scripts/backup_db.py
# Snapshot saved to data/backups/app_backup_YYYYMMDD_HHMMSS.db
```

To trigger volume replication:
```bash
python3 scripts/replicate_db.py
# Replicated DB saved to data/replicas/app_replica.db
```

### 5.2 Database Restoration Behavior
To restore database state following corruption or drive failure:
```bash
python3 scripts/restore_db.py --backup data/backups/app_backup_YYYYMMDD_HHMMSS.db
```
*Validation & Safety Guarantee:* The restore script validates the SHA-256 checksum and asserts **exact row-count equality** (`actual == expected`) against `<backup_path>.manifest.json` for both PostgreSQL and SQLite **prior** to modifying live tables. Any validation failure causes the script to abort immediately before committing changes, leaving live production data untouched (abort-before-commit / abort-before-write).

### 5.3 User Store HMAC Tamper Check Threat Model
- **Purpose:** Detects out-of-band text editor modifications, unauthenticated side-channel process edits, and partial disk writes to `data/users.json`.
- **Security Boundary:** It is an **accidental edit & process drift detection mechanism**, not an anti-tamper security boundary against a root/privileged local attacker. A privileged user with filesystem read access to `SESSION_SECRET` can generate a valid HMAC for a modified `users.json`. High-risk privilege changes remain bound to the audit ledger (`audit_chain.json`).

### 5.4 Production PostgreSQL Streaming Replication Setup
For production deployments requiring multi-node database high availability:

1. **Primary Node Configuration (`postgresql.conf`):**
   ```ini
   wal_level = replica
   max_wal_senders = 5
   wal_keep_size = 64MB
   ```
2. **Standby Node Initialization (`pg_basebackup`):**
   ```bash
   pg_basebackup -h primary-db-host -D /var/lib/postgresql/data -U replicator -P -v -R
   ```
3. **Failover:** If primary PostgreSQL host fails, trigger standby promotion:
   ```bash
   pg_ctlpromote -D /var/lib/postgresql/data
   ```


---

## 6. Restated Known Limitations Matrix

| # | Limitation | Original Status | Current Status (This Pass) | Technical Details / Path Forward |
|---|-----------|-----------------|----------------------------|----------------------------------|
| 1 | Outbound Telegram API internet dependency | Violates zero-cloud | **Fixed this pass** | Replaced with standalone `local_notifier_client.py` consuming SSE over LAN. Telegram calls blocked at runtime. |
| 2 | Audit ledger on single file | Deletable by root attacker | **Mitigated (interim)** | Dual-volume write-ahead replication (`AUDIT_CHAIN_REPLICA`) + `HALTED_CORRUPTION` alert + `scripts/restore_audit_chain.py` operator restoration tool. |
| 3 | SQLite single point of failure | Documented SPOF | **Mitigated (interim)** | Added `database.py` PostgreSQL support, online backup tool (`backup_db.py`), replication (`replicate_db.py`), and restore validation (`restore_db.py`). |
| 4 | Audit ledger migration to Hyperledger Fabric | Single node | **Roadmap (not yet built)** | Multi-node PBFT/Raft Fabric chaincode planned for Phase 8.1. |
| 5 | Cross-hospital Federated Learning | Single hospital | **Roadmap (not yet built)** | Differential privacy (ε-DP) weight aggregation planned for Phase 8.4. |
| 6 | IP spoofing velocity metrics dilution | IP-based grouping | **Roadmap (not yet built)** | IPv6 + MAC switch cross-referencing planned for Phase 8.5. |
| 7 | Outage manual override audit reliance | Human process dependency | **Operational Trust Gap** | Actions taken during total host/sentinel outages rely on manual operator post-incident logging (`--outage-log`). Full automated Article IV.2 compliance is not guaranteed until post-incident entry after system recovery. |
| 8 | WebAuthn / FIDO2 Hardware Key Authentication | Stretch Goal | **Deferred Roadmap** | Deferring in favor of TOTP + 8 hashed emergency backup recovery codes with step-up authorization, which provides zero-cloud air-gapped MFA without client hardware token driver dependencies. WebAuthn support planned for Phase 8.2. |
| 9 | GSM / Cellular Hardware Modem for Offline SMS | Stretch Goal | **Deferred Roadmap** | Deferring in favor of LAN-based SSE local desktop notifier (`local_notifier_client.py`), which delivers zero-cloud instant desktop popups without cellular modem hardware configuration. Serial AT-command modem integration planned for Phase 8.3. |



---


---

## 8. Host OS Audit Logging & On-Premises TLS CA Setup

### 8.1 OS-Level Authentication & Host Audit Logging Requirements
Any host running SentiHealth components MUST have OS-level authentication logging enabled and retained:
1. **SSH & Local Authentication Logging:** Ensure `/var/log/auth.log` (Debian/Ubuntu) or `/var/log/secure` (RHEL/CentOS) is enabled with log retention $\ge 90$ days.
2. **Systemd Journal Storage:** Set `Storage=persistent` in `/etc/systemd/journald.conf` to guarantee daemon log persistence across host reboots.
3. **Log Rotation Policy:** Configure `/etc/logrotate.d/sentihealth` to preserve historical host logs with compression.

### 8.2 On-Premises TLS Certificate Authority (CA) Setup & Distribution
To enforce encrypted HTTPS connections across the local hospital LAN:
1. **Generate Local TLS Certificates:**
   ```bash
   python3 scripts/generate_tls_certs.py
   ```
2. **Trust CA Certificate on Admin Workstations:**
   - **macOS:** Import `config/certs/server.crt` into Keychain Access $\rightarrow$ System Keychain $\rightarrow$ Set to "Always Trust".
   - **Windows:** Import `config/certs/server.crt` into `certmgr.msc` $\rightarrow$ Trusted Root Certification Authorities.
   - **Linux:** Copy `config/certs/server.crt` to `/usr/local/share/ca-certificates/sentihealth.crt` and run `update-ca-certificates`.

