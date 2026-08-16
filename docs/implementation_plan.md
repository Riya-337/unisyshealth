# Implementation Plan
## SentiHealth — ML-Driven Threat Detection and Self-Healing Architecture

**Version:** 1.0  
**Status:** Current Architecture + Roadmap  
**Last Updated:** 2026-08-15

---

## Current State Summary

SentiHealth is a complete working prototype with all four core layers implemented and verified. This document captures the **current implementation state** and the **planned enhancements roadmap**.

---

## Phase 0 — Foundation (✅ Complete)

### 0.1 Project Bootstrap
- [x] Python virtual environment + `requirements.txt`
- [x] `_paths.py` — single source of truth for all filesystem paths
- [x] `setup.sh` / `reset_and_run.sh` — single-command environment setup
- [x] `.env` support via `python-dotenv`

### 0.2 Synthetic Data Generation
- [x] `data_generator.py` — generates `data/sentinelhealth_dataset.csv`
- [x] 5 attack types: `normal`, `brute_force`, `exfiltration`, `ddos`, `ransomware`
- [x] 8 ML features per event with realistic per-type distributions
- [x] MITRE ATT&CK and HHS Breach Portal-inspired feature ranges

---

## Phase 1 — ML Core (✅ Complete)

### 1.1 Model Training Pipeline (`model_trainer.py`)
- [x] 5 classifiers: Random Forest, XGBoost, Gradient Boosting, SVM, Logistic Regression
- [x] `CalibratedClassifierCV` with isotonic regression (5-fold CV)
- [x] SMOTE resampling for class imbalance correction
- [x] Gaussian noise injection (2.0% scale) for sensor jitter simulation
- [x] Boundary case injection (1.0%) via hyperparameter grid search
- [x] **Poison quarantine gate:** Label distribution drift detection (25% threshold)
- [x] SHA-256 model manifest generation post-training

### 1.2 Threat Scoring Engine (`scoring_matrix.py`)
- [x] Weighted ensemble: `RF=0.25, XGB=0.20, GBM=0.20, SVM=0.20, LR=0.15`
- [x] Asset criticality multipliers: `workstation=1.0x`, `clinical_app=1.2x`, `ehr=1.5x`
- [x] Attack damage weights: `normal=0.1`, `brute_force=0.4`, `exfiltration=0.7`, `ddos=0.5`, `ransomware=1.0`
- [x] **SHA-256 manifest verification** at model load time
- [x] Configurable thresholds from `config/thresholds.json`
- [x] Heuristic fallback if models unavailable

### 1.3 Threshold Optimization (`threshold_optimizer.py`)
- [x] Grid search over Low/Medium and Medium/High boundary values
- [x] Outputs optimal thresholds to `config/thresholds.json`

---

## Phase 2 — Event Pipeline (✅ Complete)

### 2.1 Live Sentinel (`live_sentinel.py`)
- [x] Real-time `events.jsonl` tail (non-blocking I/O with threading)
- [x] 8-feature extraction per event with backward-compat `extract_features()` helper
- [x] SHAP waterfall chart generation for all High-tier events (all 8 features)
- [x] SHAP chart saved to `logs/shap_explanation_<timestamp>.png`
- [x] Alert deduplication via `_alert_claim_lock` (thread-safe)
- [x] Integration with Mirage deception engine
- [x] IP pseudonymization via `privacy.pseudonymize.tokenize()`
- [x] `SENTIHEALTH_TEST_MODE` env var bypasses Telegram for testing

### 2.2 EHR Target Server (`webapp/app.js`)
- [x] Node.js/Express server simulating hospital web traffic
- [x] Append-only event logging to `logs/events.jsonl`

---

## Phase 3 — Response Engine (✅ Complete)

### 3.1 Self-Healing Responder (`self_healing_responder.py`)
- [x] Tiered response dispatcher:
  - Low → `log_and_monitor()`
  - Medium → `ip_throttle()` + `account_lockout()` + SSE alert
  - High → `request_admin_authorization()` → `db_snapshot()` + `full_lockdown()`
- [x] Auto-escalation on admin timeout (`send_summary()` fallback)
- [x] **Genesis block bootstrap** on first run
- [x] `_write_chain_atomic()` — temp file + rename for corruption-safe writes
- [x] `verify_chain_integrity()` — full HMAC + hash chain validation
- [x] `HALTED_CORRUPTION` status on chain breach detection
- [x] Forensic report generation for confirmed High-tier threats
- [x] Retraining queue append (`retraining/retraining_queue.json`)

---

## Phase 4 — Admin Interface (✅ Complete)

### 4.1 Flask Dashboard (`dashboard.py`)
- [x] PBKDF2-HMAC-SHA256 password hashing (260,000 iterations, OWASP 2023)
- [x] Legacy plaintext → hashed password transparent upgrade on login
- [x] Session token management (server-side)
- [x] Admin vs. standard user role separation
- [x] REST API endpoints for all threat/audit data
- [x] SSE stream endpoint (`/api/stream`) for real-time push
- [x] High-tier challenge approval flow (`/api/alerts/<id>/respond`)
- [x] User registration/approval workflow (`/api/admin/users`)
- [x] Mirage deception status endpoint (`/api/deception/status`)

### 4.2 React Frontend (`frontend/`)
- [x] Vite + TypeScript + shadcn/ui
- [x] Real-time threat feed via SSE consumption
- [x] Tier distribution charts (Plotly/Recharts)
- [x] SHAP chart viewer
- [x] Audit chain explorer
- [x] Admin approval UI for pending High-tier challenges

---

## Phase 5 — Privacy and Deception (✅ Complete)

### 5.1 Privacy Layer (`privacy/`)
- [x] `pseudonymize.py` — HMAC-SHA256 IP tokenization (persistent key in `config/.chain_key`)
- [x] `crypto_shred.py` — AES-256 encryption of PHI-adjacent fields; key deletion = irrecoverable data
- [x] Demo scripts: `demo_pseudonymize.py`, `demo_crypto_shred.py`

### 5.2 Mirage Deception Layer (`deception/`)
- [x] `mirage.py` — Routing decision engine: redirect suspected attackers to honeypot data
- [x] `honey_data.py` — Realistic fake EHR data generation for the honeypot
- [x] `noise.py` — Statistical noise injection to make honeypot data convincingly realistic
- [x] `feedback.py` — Flush confirmed Mirage interactions to retraining queue

---

## Phase 6 — Attack Simulation (✅ Complete)

### 6.1 Attack Scripts (`attack_scripts/`)
- [x] `exfiltration.py` — 3-phase exfiltration: Recon → Escalation → Exfiltration
  - [x] Fixed: all 8 features now vary per phase (commit `73e7b35`)
- [x] `brute_force.py` — Credential stuffing simulation
- [x] `ddos.py` — DDoS with CPU/memory spikes
- [x] `port_scan.py` — Stealth network reconnaissance
- [x] `tamper_chain.py` — Audit chain integrity attack (for testing detection)

---

## Phase 7 — Quality and Observability (✅ Complete)

### 7.1 Testing
- [x] `test_sentinel.py` — 4 unit tests: feature extraction, tier classification, blockchain integrity, Telegram timeout fallback
- [x] `test_tiers.py` — Boundary condition tests for tier thresholds
- [x] `evaluate_models.py` / `evaluate_models_v2.py` — Offline model evaluation

### 7.2 Reporting
- [x] `generate_metrics.py` — Produces `evaluation_metrics.json`
- [x] `generate_report.py` — Human-readable threat summary report
- [x] `MODEL_METRICS.md` — Ensemble performance table

---

## Phase 8 — Planned Enhancements (🔲 Roadmap)

### 8.1 Distributed Audit Ledger
**Timeline:** Q4 2026  
**Approach:** Migrate `audit_chain.json` to Hyperledger Fabric  
- Deploy 3-node Fabric network across hospital subnets
- Implement Fabric chaincode for block append and integrity verification
- Migrate `_write_chain_atomic()` to Fabric SDK client calls

### 8.2 Air-Gap Admin Notification
**Timeline:** Q4 2026  
**Approach:** Replace Telegram with on-premises SMS gateway  
- Integrate with Spok hospital pager system API
- Add local SMTP fallback (partially implemented in `notifications/local_smtp.py`)
- Remove `pyngrok` dependency

### 8.3 FHIR Integration
**Timeline:** Q1 2027  
**Approach:** Connect to real EHR via HL7 FHIR R4  
- Implement FHIR event adapter in `live_sentinel.py`
- Map FHIR audit events to the 8-feature vector
- Test against Epic sandbox environment

### 8.4 Federated Learning
**Timeline:** Q2 2027  
**Approach:** Cross-hospital model weight sharing  
- Implement FedAvg aggregation server
- Add differential privacy (ε-DP) to weight updates
- Each hospital node trains locally; only gradients shared

### 8.5 IPv6 + Session Fingerprinting
**Timeline:** Q3 2026  
**Approach:** Counter IP spoofing  
- Add IPv6 normalization to `live_sentinel.py`
- Implement session token fingerprinting via HTTP headers
- Cross-reference MAC addresses at switch level (requires SNMP integration)

### 8.6 Adversarial ML Robustness
**Timeline:** Q3 2026  
**Approach:** Harden retraining pipeline  
- Add STRIP defense against backdoor attacks
- Implement adversarial example detection in `quarantine_check()`
- Add Jensen-Shannon divergence check for feature distribution drift

---

## Open Questions / Decision Points

> [!IMPORTANT]
> The following items require stakeholder decisions before implementation:

1. **Ledger Migration:** Which consensus algorithm for Hyperledger Fabric? (PBFT vs. Raft) — affects network topology requirements
2. **Federated Learning:** Will hospitals consent to sharing gradient updates? Legal review needed.
3. **FHIR Auth:** OAuth2 (SMART on FHIR) vs. mutual TLS for EHR connection?
4. **Dashboard Auth:** Upgrade from session tokens to JWT + refresh token pattern?
5. **Multi-tenancy:** Should a single SentiHealth instance monitor multiple departments/hospitals?
