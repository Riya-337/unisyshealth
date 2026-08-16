# Product Requirements Document (PRD)
## SentiHealth — Autonomous Healthcare Cybersecurity Platform

**Version:** 1.0  
**Status:** Active Prototype  
**Last Updated:** 2026-08-15  
**Repository:** [UnisysUIP / SentiHealth](https://github.com/UnisysUIP/2026-ML-Driven-Threat-Detection-and-Self-Healing-Architecture-for-Healthcare-Web-Applications)

---

## 1. Executive Summary

SentiHealth is an **autonomous, zero-cloud healthcare cybersecurity system** that monitors live hospital Electronic Health Record (EHR) web servers in real time, detects cyber threats using a 5-model ML ensemble, and automatically executes tiered self-healing responses — all without requiring cloud infrastructure, making it HIPAA air-gap compliant.

### Problem Statement

Hospitals are the number-one target for ransomware and data exfiltration attacks. Existing ML-based security tools either:
- Depend on cloud infrastructure, violating HIPAA air-gap requirements, or
- Require constant manual human review, making them too slow for millisecond-scale intrusions.

### Solution

A fully on-premises, real-time threat detection and autonomous response pipeline with human-in-the-loop authorization for high-risk actions.

---

## 2. Goals and Non-Goals

### Goals
| # | Goal | Priority |
|---|------|----------|
| G1 | Detect threats in real time from live network event logs with no cloud dependency | P0 |
| G2 | Automate tiered responses (throttle, lockout, snapshot) proportional to threat severity | P0 |
| G3 | Keep humans in the loop — High-tier threats require admin approval before action | P0 |
| G4 | Leave a tamper-proof, cryptographically verifiable audit trail | P0 |
| G5 | Continuously improve via human-confirmed retraining queue | P1 |
| G6 | Provide SHAP-based explainability for every High-tier alert | P1 |
| G7 | Protect PHI through pseudonymization and crypto-shredding | P1 |
| G8 | Deceive active attackers via the Mirage honeypot layer | P2 |

### Non-Goals
- Real-time protection of non-healthcare verticals
- Cloud-based SaaS deployment
- Integration with real HL7 FHIR EHR systems (prototype only; planned for v2)
- Mobile application or native desktop client

---

## 3. Users and Personas

### 3.1 Primary Users

| Persona | Role | Core Need |
|---------|------|-----------|
| **Hospital Security Admin** | Approves/rejects High-tier threat responses via dashboard/Telegram | Informed, fast decisions with SHAP explainability |
| **Security Analyst** | Monitors the real-time threat dashboard | Visibility into live threat landscape |
| **ML Engineer** | Retrains models via the review queue | Quality-controlled feedback loop |

### 3.2 Adversarial Actors (Out-of-scope users the system defends against)
- External ransomware operators
- Insider threats (rogue clinicians / IT staff)
- Nation-state APT actors

---

## 4. Functional Requirements

### 4.1 Event Ingestion
- **FR-01:** The system SHALL tail `logs/events.jsonl` in real time using `live_sentinel.py`
- **FR-02:** The system SHALL parse each JSON-lines event and extract exactly 8 ML features per event
- **FR-03:** The system SHALL support all event types: login attempt, EHR access, data export, lateral movement, CPU/memory spikes

### 4.2 Threat Scoring
- **FR-04:** The system SHALL score every event using a weighted ensemble of 5 ML models (RF, XGB, GBM, SVM, LR)
- **FR-05:** All models SHALL be loaded with SHA-256 manifest verification on startup; tampered models SHALL cause immediate shutdown
- **FR-06:** The composite threat score SHALL be a weighted sum: `RF=0.25, XGB=0.20, GBM=0.20, SVM=0.20, LR=0.15`
- **FR-07:** The scoring engine SHALL apply configurable thresholds from `config/thresholds.json`

### 4.3 Tier Classification
- **FR-08:** Events SHALL be classified into three tiers based on composite risk score:
  - **Low** (score < 0.3): Log and monitor
  - **Medium** (0.3–0.7): IP throttle + account lockout
  - **High** (> 0.7): Telegram admin approval → DB snapshot + full lockdown
- **FR-09:** Asset criticality multipliers SHALL be applied: `workstation=1.0x`, `clinical_app=1.2x`, `ehr=1.5x`

### 4.4 Self-Healing Response
- **FR-10:** Low-tier events SHALL be logged to the audit chain automatically with no blocking action
- **FR-11:** Medium-tier events SHALL trigger: IP throttling, account lockout, and SSE alert push to dashboard
- **FR-12:** High-tier events SHALL pause execution and request admin authorization via Telegram bot and/or dashboard
- **FR-13:** Upon admin approval, High-tier response SHALL: create DB snapshot, execute full lockdown, write forensic report
- **FR-14:** If admin does not respond within the timeout window, the system SHALL auto-escalate with a summary notification

### 4.5 Audit Ledger
- **FR-15:** Every action SHALL be appended to `data/audit_chain.json` as an HMAC-SHA-256 hash-chained block
- **FR-16:** The system SHALL verify chain integrity on every new block write; detected corruption SHALL halt processing with `HALTED_CORRUPTION` status
- **FR-17:** The genesis block SHALL be bootstrapped automatically on first run

### 4.6 Explainability (SHAP)
- **FR-18:** Every High-tier detection SHALL generate a SHAP waterfall chart showing all 8 feature contributions
- **FR-19:** SHAP charts SHALL be saved to `logs/shap_explanation_<timestamp>.png`

### 4.7 Admin Dashboard
- **FR-20:** A Flask dashboard SHALL be served at `http://localhost:5001`
- **FR-21:** Dashboard SHALL expose: live threat feed, tier distribution, blocked IPs, audit chain, SHAP charts
- **FR-22:** Admin endpoints SHALL require PBKDF2-HMAC-SHA256 session token authentication (260,000 iterations)
- **FR-23:** A Server-Sent Events (SSE) stream SHALL push real-time alerts to authenticated admin clients
- **FR-24:** Admin SHALL be able to approve/reject pending High-tier challenges from the dashboard

### 4.8 Privacy Layer
- **FR-25:** Source IPs SHALL be pseudonymized via HMAC tokenization before being written to the exportable audit chain
- **FR-26:** The system SHALL support crypto-shredding: deleting the encryption key renders all associated PII irrecoverable
- **FR-27:** The threat dashboard (authenticated) SHALL display real IPs; audit chain exports SHALL use HMAC tokens only

### 4.9 Deception Layer (Mirage)
- **FR-28:** The system SHALL optionally route suspected attacker sessions to honeypot data via the Mirage module
- **FR-29:** Mirage engagement SHALL be logged and fed back to the model retraining pipeline as confirmed attack data

### 4.10 Model Retraining
- **FR-30:** Confirmed High-tier events SHALL be appended to `retraining/retraining_queue.json`
- **FR-31:** The retraining pipeline SHALL include a poison-quarantine gate: if the candidate High-tier fraction drops >25% below baseline, suspicious rows SHALL be quarantined and logged
- **FR-32:** Each retrained model SHALL produce a new SHA-256 manifest entry

---

## 5. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Latency** | Feature extraction + scoring < 500ms per event under normal load |
| **Availability** | Sentinel process must restart automatically on crash (process supervisor) |
| **Security** | Zero external network calls except for Telegram notifications; all data stays on-premises |
| **Compliance** | HIPAA-aligned: no real PHI, pseudonymized audit exports, crypto-shredding support |
| **Scalability** | Must handle sustained 100 events/sec without queue buildup |
| **Auditability** | Every system action must appear in the hash-chained ledger within 1 second of occurrence |
| **Portability** | Runs on Python 3.10+; no GPU required |

---

- **No cloud dependency** — all ML inference, storage, and alerting (`local_notifier_client.py`) is 100% on-premises over local LAN.
- **No real EHR data** — all training data is synthetically generated.
- **Zero-Cloud Enforcement** — Telegram calls are blocked at runtime by the zero-cloud guard.
- **Dual Audit Ledger Replication** — write-ahead replication (`AUDIT_CHAIN_REPLICA`) with operator-authorized manual recovery (`scripts/restore_audit_chain.py`).

---

## 6.1 Deployment & Scaling Model

SentiHealth scales by **independent deployment**, not by network interconnectivity.

- Each hospital site runs a complete, self-contained instance — its own LAN, dashboard backend, local SSE desktop notifier client, and audit ledger — with zero dependency on any third-party cloud service or external network.
- Live cross-hospital network connections are **strictly prohibited** in this architecture.
- Future cross-site capabilities (Phase 8.4) will strictly rely on offline/federated model weight updates over private channels, never live event streams or PHI.


---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Ensemble threat detection accuracy | ≥ 95% on balanced test set |
| False positive rate (Low misclassified as High) | < 2% |
| Mean time to detection (event → tier assignment) | < 500ms |
| Mean time to admin notification (High event → Telegram) | < 5s |
| Audit chain integrity (verified blocks) | 100% |
| SHAP chart generation success rate | 100% of High-tier events |

---

## 8. Release Milestones

| Milestone | Scope | Status |
|-----------|-------|--------|
| M1 — Core Pipeline | Feature engineering, ensemble scoring, tier classification, audit chain | ✅ Complete |
| M2 — Self-Healing Responder | Tiered response, Telegram approval, DB snapshot | ✅ Complete |
| M3 — Dashboard | Flask dashboard, SSE stream, PBKDF2 auth | ✅ Complete |
| M4 — Privacy & Deception | Pseudonymization, crypto-shredding, Mirage honeypot | ✅ Complete |
| M5 — FHIR Integration | Connect to Epic/Cerner via HL7 FHIR | 🔲 Planned |
| M6 — Federated Learning | Cross-hospital weight sharing without PHI sharing | 🔲 Planned |
| M7 — Distributed Ledger | Migrate audit chain to Hyperledger Fabric | 🔲 Planned |
