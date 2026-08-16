# App Flow Document
## SentiHealth — End-to-End User and System Flows

**Version:** 1.0  
**Last Updated:** 2026-08-15

---

## 1. System Startup Flow

```
Terminal 1                    Terminal 2                   Terminal 3
─────────                    ──────────                   ──────────
source setup.sh              source .venv/bin/activate    source .venv/bin/activate
cd webapp && node app.js  →  python3 live_sentinel.py  →  python3 dashboard.py
       │                             │                            │
       ↓                             ↓                            ↓
Starts EHR server         Loads & verifies models         Starts Flask API
on port 3000              SHA-256 manifest check          on port 5001
       │                  Bootstraps audit chain           Serves frontend
       │                  Opens events.jsonl tail         
       ↓                  Starts event loop               Open browser:
Appends events to    ──→  Ready for events         ──→  localhost:5001
logs/events.jsonl
```

---

## 2. Normal Event Processing Flow (Low-Tier)

```
EHR Server (app.js)
        │
        │  Append JSON event to logs/events.jsonl
        ↓
live_sentinel.py (tail loop)
        │
        │  Read new line from events.jsonl
        ↓
Feature Extraction
        │  failed_logins, cpu_usage, memory_spike,
        │  ehr_access_per_hour, lateral_movement_events,
        │  data_export_volume_kb, access_time_deviation,
        │  source_ip_reputation
        ↓
scoring_matrix.score_event()
        │  Load 5 calibrated models (cached after first load)
        │  Compute P_attack for each model
        │  Weighted ensemble: Σ(weight × P_attack)
        │  Apply asset criticality + damage multipliers
        ↓
Tier = LOW (score < 0.3)
        │
        ↓
self_healing_responder.respond()
        │  Action: log_and_monitor()
        │  Write block to audit_chain.json (atomic write)
        │  Block includes: prev_hash, entry_hash, block_hmac
        ↓
SSE Push to Dashboard
        │  Event: { tier: "Low", score: 0.15, ip: "hmac:...", timestamp }
        ↓
Dashboard Updates
        │  Threat counter increments
        │  Tier distribution chart refreshes
```

---

## 3. Medium-Tier Threat Response Flow

```
[Score: 0.3 – 0.7] → Tier = MEDIUM
        │
        ↓
self_healing_responder.respond()
        │
        ├── ip_throttle(source_ip)
        │     └── Append IP to logs/blocked_ips.json
        │
        ├── account_lockout(user_id)
        │     └── Write lockout entry to logs/locked_accounts.json
        │
        ├── Write MEDIUM block to audit_chain.json
        │
        └── SSE Push: { tier: "Medium", actions: ["ip_throttle", "account_lockout"] }
                │
                ↓
        Dashboard: Alert banner appears
        Admin sees blocked IP + reason in dashboard
```

---

## 4. High-Tier Threat Response Flow (Human-in-the-Loop)

```
[Score > 0.7] → Tier = HIGH
        │
        ↓
SHAP Chart Generation
        │  Generate waterfall chart for all 8 features
        │  Save: logs/shap_explanation_<timestamp>.png
        │
        ↓
live_sentinel.handle_high_tier_threat()
        │
        ├── SSE Push: CRITICAL alert to dashboard
        │
        └── get_notifier().request_authorization(alert_message)
                │
                ├── [Telegram Mode]
                │     Send Telegram message to admin chat
                │     Attach SHAP chart image
                │     Wait for admin reply: YES / NO
                │
                └── [Dashboard Mode]
                      Write challenge to data/challenges.json
                      SSE Push: { type: "authorization_required", id: challenge_id }
                      Admin sees approval panel in dashboard

Admin Response:
        │
        ├── APPROVED
        │       │
        │       ├── db_snapshot()
        │       │     └── Copy app.db → data/snapshots/snapshot_<timestamp>.db
        │       │
        │       ├── full_lockdown()
        │       │     └── Write LOCKDOWN entry to network_actions.json
        │       │
        │       ├── generate_forensic_report()
        │       │     └── Save: logs/forensic_report_<timestamp>.json
        │       │
        │       ├── Append to retraining/retraining_queue.json
        │       │
        │       └── Write APPROVED block to audit_chain.json
        │
        └── REJECTED / TIMEOUT
                │
                ├── send_summary() → notify admin of auto-escalation
                └── Write REJECTED / TIMEOUT block to audit_chain.json
```

---

## 5. Admin Dashboard Login Flow

```
User opens localhost:5001
        │
        ↓
Login Page
        │  Enter username + password
        │  POST /api/login
        │
        ↓
dashboard.py: _check_password()
        │  Fetch stored hash from data/users.json
        │  Verify PBKDF2-HMAC-SHA256 (260,000 iterations)
        │
        ├── FAIL → 401 Unauthorized
        │          Login page shows error
        │
        └── SUCCESS
                │  Generate session token (secrets.token_hex)
                │  Store server-side in active_sessions dict
                │  Return { token, role } in response
                │
                ↓
        Frontend stores token in memory
        All subsequent requests include: Authorization: Bearer <token>
        │
        ↓
Dashboard renders:
        ├── Real-time threat feed (SSE /api/stream)
        ├── Tier distribution chart (/api/metrics)
        ├── Blocked IPs table (/api/blocked_ips)
        ├── Audit chain explorer (/api/audit_chain)
        └── [Admin only] Pending alerts (/api/alerts)
```

---

## 6. Model Retraining Flow

```
Review Queue (review_queue.py)
        │
        │  Admin reviews flagged events in retraining_queue.json
        │  Marks each as: confirmed_attack | false_positive
        │
        ↓
Poison Quarantine Gate (model_trainer.quarantine_check())
        │  Compute candidate High-tier fraction
        │  Compare against baseline from sentinelhealth_dataset.csv
        │
        ├── DRIFT DETECTED (>25% drop)
        │     └── Quarantine Low-tier rows → logs/poison_quarantine.json
        │           Stop retraining; alert admin
        │
        └── CLEAN
                │
                ↓
        Merge confirmed attacks with original training CSV
        Re-run full training pipeline:
                │  SMOTE resampling
                │  Noise injection
                │  Train 5 models + calibration
                │  Evaluate on test set
                │
                ↓
        Update models/ with new .pkl files
        Regenerate SHA-256 model manifest
        Restart live_sentinel.py to load new models
```

---

## 7. Attack Simulation Flow (Demo / Testing)

```
Terminal 4
        │
        python3 attack_scripts/exfiltration.py
        │
        ↓
Phase 1: RECONNAISSANCE (10 events)
        │  Subtle probing: low failed_logins, mild lateral_movement
        │  source_ip_reputation: 0.6–0.9 (looks legitimate)
        │  Expected tier: Low → Low
        │
        ↓
Phase 2: ESCALATION (10 events)
        │  Privilege escalation: moderate failed_logins, ehr_access rising
        │  source_ip_reputation: 0.25–0.5 (suspicious)
        │  Expected tier: Medium → Medium
        │
        ↓
Phase 3: EXFILTRATION (10 events)
        │  Full attack: high data_export_volume_kb, lateral_movement_events
        │  source_ip_reputation: 0.02–0.15 (malicious)
        │  Expected tier: High → High
        │
        ↓
live_sentinel detects Phase 3
        │  Generates SHAP chart
        │  Sends Telegram alert (or dashboard challenge)
        │  Waits for admin approval
        │
        ↓
Admin approves via dashboard
        │  DB snapshot taken
        │  Full lockdown executed
        │  Forensic report generated
        │  Audit chain updated
        │
        ↓
Dashboard shows full attack timeline
```

---

## 8. Mirage Deception Flow

```
live_sentinel detects repeated suspicious activity from IP X
        │
        │  _mirage_decide(source_ip, features, score)
        │
        ↓
deception/mirage.py
        │
        ├── Decision: DECEIVE
        │       │
        │       ├── Route requests to honey_data.py
        │       │     └── Serve fake EHR records (realistic but fabricated)
        │       │
        │       ├── Inject statistical noise via noise.py
        │       │     └── Make fake data look authentic
        │       │
        │       └── Log engagement to deception feedback
        │             └── deception/feedback.flush_mirage_labels()
        │                   └── Append to retraining_queue.json
        │                         (source='mirage_oracle' — exempted from quarantine)
        │
        └── Decision: PASS
                └── Normal event processing continues
```

---

## 9. Audit Chain Integrity Check Flow

```
Every new block write triggers verify_chain_integrity()
        │
        ↓
Load audit_chain.json
        │
        For each block[i] from index 1 to N:
        │
        ├── Recompute entry_hash(block[i]) = SHA-256(block_content + block[i-1].entry_hash)
        │
        ├── Compare recomputed hash vs stored entry_hash
        │     └── MISMATCH → integrity_alert() → HALTED_CORRUPTION
        │
        └── Recompute block_hmac = HMAC-SHA256(payload, SESSION_SECRET)
              └── MISMATCH → integrity_alert() → HALTED_CORRUPTION
        │
        ↓
All blocks pass → chain is VALID → proceed with new block write
```

---

## 10. Data Flow Diagram

```
                    ┌─────────────────┐
                    │  EHR Server     │
                    │  (Node.js)      │
                    └────────┬────────┘
                             │ events.jsonl
                             ▼
                    ┌─────────────────┐      ┌──────────────────┐
                    │ Live Sentinel   │─────▶│ Scoring Matrix   │
                    │ (feature eng.)  │      │ (5-model ensemble)│
                    └────────┬────────┘      └────────┬─────────┘
                             │                        │ Threat Score + Tier
                             │                        ▼
                    ┌─────────────────┐      ┌──────────────────┐
                    │ SHAP Engine     │      │ Self-Healing     │
                    │ (explainability)│      │ Responder        │
                    └────────┬────────┘      └────────┬─────────┘
                             │ shap_*.png             │
                             │                ┌───────┼────────┐
                             │                ▼       ▼        ▼
                             │          IP Block  DB Snap  Telegram
                             │                        │
                             │                        ▼
                    ┌─────────────────────────────────────────┐
                    │         Audit Chain (audit_chain.json)   │
                    │         SHA-256 Hash + HMAC-SHA256       │
                    └─────────────────────────────────────────┘
                             │                        │
                    ┌────────▼────────┐      ┌────────▼────────┐
                    │ Flask Dashboard │      │ Retraining Queue │
                    │ (localhost:5001)│      │ (retraining/)    │
                    └─────────────────┘      └─────────────────┘
```
