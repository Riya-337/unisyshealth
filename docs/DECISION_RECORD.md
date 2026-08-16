# SentiHealth — Architectural Decision Record (ADR)

This document tracks all formal architectural decisions, security choices, and accepted deployment trade-offs in SentiHealth.

---

## Decision History

### ADR-001: 100% Zero-Cloud Air-Gapped LAN Architecture
- **Date:** 2026-08-14  
- **Status:** Accepted & Enforced  
- **Decision:** Eliminate all outbound third-party cloud service dependencies (Telegram, cloud SMS gateways, public APNs). Replace with on-premises Server-Sent Events (`/api/stream`), server console logging, and local desktop subscribers (`local_notifier_client.py`).  
- **Rationale:** Strict compliance with HIPAA air-gap regulations and hospital network isolation requirements.

---

### ADR-002: Dual Cryptographic Audit Ledger with Atomic Writes
- **Date:** 2026-08-15  
- **Status:** Accepted & Enforced  
- **Decision:** Implement SHA-256 hash chains (`entry_hash`) paired with HMAC signatures (`_block_hmac`) backed by `_write_chain_atomic()` and an independent replica (`audit_chain_replica.json`).  
- **Rationale:** Guarantees tamper detection (`HALTED_CORRUPTION`) and disaster recovery without single-point ledger corruption.

---

### ADR-003: Human-in-the-Loop Step-Up Authorization & 90s Stasis Timeout
- **Date:** 2026-08-15  
- **Status:** Accepted & Enforced (Constitution Article III.4 & V.3)  
- **Decision:** High-tier threat containment requires explicit TOTP step-up human authorization. If the 90-second countdown timer expires without admin response, **no automated destructive action or permanent IP ban is executed**; the incident is queued in the Stasis Review Queue (`/api/alerts/stasis`) for retro-active human review.  
- **Rationale:** Preserves clinical availability during medical emergencies and prevents automated false-positive lockouts.

---

### ADR-004: Session Storage Token Isolation & Rate Limiting
- **Date:** 2026-08-16  
- **Status:** Accepted & Enforced  
- **Decision:** Remove `localStorage` token storage in favor of **`sessionStorage` ONLY**. Enforce a 5-failed-attempts rolling rate limiter per IP/user (15-minute auto-unlock window) and 15-minute frontend session idle auto-logout.  
- **Rationale:** Protects against XSS token theft across tabs and brute-force authentication attacks.

---

### ADR-005: Permission-Restricted Local Secrets Vault Scope
- **Date:** 2026-08-16  
- **Status:** Accepted & Enforced (Scope Reduction)  
- **Decision:** Store `SESSION_SECRET` and `CHAIN_KEY` in `config/.secrets_vault.json` with strict `0600` owner-read-only file permissions.  
- **Rationale:** Provides an intentional, permission-restricted vault solution tailored for lightweight, single-host on-premises hospital deployments without dedicated HashiCorp Vault infrastructure.

---

### ADR-006: Formal Decision on WebAuthn and GSM Modems
- **Date:** 2026-08-16  
- **Status:** Formally Closed — Accepted Limitations  
- **WebAuthn / FIDO2:** Closed as an accepted limitation. Baseline TOTP (PBKDF2-HMAC-SHA256) + 8 hashed 64-character emergency recovery codes with TOTP step-up authorization fulfills 100% zero-cloud air-gapped MFA without client hardware token driver or browser extension dependencies.  
- **GSM / Cellular Modems:** Closed as an accepted limitation. LAN-based SSE desktop notifier (`local_notifier_client.py`) delivers zero-cloud instant desktop alerts without introducing hardware serial driver dependencies or cellular carrier reliability risks.
