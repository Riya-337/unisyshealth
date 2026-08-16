# Technical Requirements Document (TRD)
## SentiHealth — ML-Driven Threat Detection and Self-Healing Architecture

**Version:** 1.0  
**Status:** Active Prototype  
**Last Updated:** 2026-08-15

---

## 1. System Overview

SentiHealth is a multi-layer cybersecurity platform consisting of four primary subsystems:

1. **EHR Target Server** — Node.js/Express mock hospital web server (event source)
2. **Live Sentinel** — Python event consumer, feature engineer, and ML orchestrator
3. **Self-Healing Responder** — Tiered automated response and cryptographic audit engine
4. **Admin Dashboard** — Flask REST API + SSE streaming + React/Vite frontend

---

## 2. Runtime Environment

### 2.1 Backend (Python)
| Requirement | Specification |
|-------------|---------------|
| Python version | 3.10+ (3.12 recommended) |
| Package manager | pip with virtualenv |
| Entry points | `live_sentinel.py`, `dashboard.py`, `model_trainer.py` |
| Environment config | `.env` file via `python-dotenv` |

### 2.2 EHR Server (Node.js)
| Requirement | Specification |
|-------------|---------------|
| Node.js version | 18+ LTS |
| Framework | Express.js |
| Event output | Append-only JSONL (`logs/events.jsonl`) |
| Default port | 3000 |

### 2.3 Frontend (React/Vite)
| Requirement | Specification |
|-------------|---------------|
| Framework | React 18 + TypeScript |
| Build tool | Vite |
| UI components | shadcn/ui |
| Package manager | bun / npm |
| Dev server port | 8080 (Vite default) |

---

## 3. Python Dependencies

```
colorama==0.4.6          # Terminal colorized output
Faker==40.15.0           # Synthetic data generation
Flask==3.1.3             # Dashboard REST API
flask-cors               # Cross-origin resource sharing
joblib==1.5.3            # Model serialization utility
matplotlib==3.10.8       # SHAP chart rendering
numpy==2.4.4             # Numerical operations
pandas==3.0.2            # Tabular data manipulation
scikit-learn==1.8.0      # ML models + calibration
scipy==1.17.1            # Statistical utilities
shap==0.51.0             # Model explainability
xgboost==3.2.0           # Gradient boosting model
lightgbm                 # LightGBM (optional model)
imbalanced-learn         # SMOTE class balancing
requests                 # HTTP client (Telegram API)
python-dotenv            # .env config loading
cryptography             # Crypto-shredding primitives
pyngrok                  # Optional ngrok tunnel for Telegram
```

---

## 4. File System Layout (Technical)

```
uipfinal/
├── _paths.py                    # Canonical path constants — ALL paths defined here
├── live_sentinel.py             # Core event loop, feature engineering, SHAP
├── scoring_matrix.py            # Ensemble scoring, model loading, HMAC chain logic
├── self_healing_responder.py    # Tiered response, audit chain writes, Telegram flow
├── model_trainer.py             # Training pipeline with SMOTE + poison quarantine
├── dashboard.py                 # Flask app: REST API + SSE + PBKDF2 auth
├── review_queue.py              # Human-in-the-loop retraining queue manager
├── data_generator.py            # Synthetic training data generator
├── threshold_optimizer.py       # Grid search for optimal tier thresholds
├── evaluate_models.py           # Post-training metric evaluation
├── context.py                   # Session/context state management
├── cost_matrix.py               # Asymmetric cost matrix for tier weighting
│
├── attack_scripts/
│   ├── brute_force.py           # Credential stuffing attack simulator
│   ├── ddos.py                  # DDoS attack simulator
│   ├── exfiltration.py          # 3-phase data exfiltration simulator
│   ├── port_scan.py             # Network port scanning simulator
│   └── tamper_chain.py          # Audit chain tampering test script
│
├── notifications/
│   ├── __init__.py              # Notifier factory (get_notifier())
│   ├── base.py                  # Abstract notifier base class
│   ├── telegram.py              # Telegram Bot API notifier
│   ├── local_smtp.py            # On-premises SMTP notifier
│   ├── sentinel_notifier.py     # SentiHealth-specific alert formatter
│   ├── dual_notifier.py         # Telegram + SMTP dual-channel notifier
│   └── console.py               # Console-only notifier (test mode)
│
├── privacy/
│   ├── __init__.py
│   ├── pseudonymize.py          # HMAC IP tokenization
│   └── crypto_shred.py          # AES-256 encryption + key deletion
│
├── deception/
│   ├── __init__.py
│   ├── mirage.py                # Honeypot routing decision engine
│   ├── honey_data.py            # Fake EHR data generator for honeypot
│   ├── noise.py                 # Statistical noise injection for deception
│   └── feedback.py              # Mirage label flush to retraining queue
│
├── models/                      # Serialized calibrated .pkl model files
│   └── model_manifest.json      # SHA-256 checksums for tamper detection
│
├── data/
│   ├── audit_chain.json         # HMAC hash-chained audit ledger
│   ├── app.db                   # SQLite: users, sessions, metrics
│   └── sentinelhealth_dataset.csv # Synthetic training dataset
│
├── logs/
│   ├── events.jsonl             # Live event stream (tailed by sentinel)
│   ├── threat_log.json          # Detected threats registry
│   ├── blocked_ips.json         # Active IP blocklist
│   ├── shap_explanation_*.png   # Per-High-event SHAP charts
│   └── forensic_report_*.json   # Detailed forensic reports
│
├── config/
│   ├── thresholds.json          # Tier boundary thresholds
│   └── .chain_key               # Persistent HMAC key (binary, 32 bytes)
│
├── retraining/
│   └── retraining_queue.json    # Verified attacks for model retraining
│
├── webapp/                      # Node.js EHR server
│   └── app.js
│
└── frontend/                    # React/Vite dashboard UI
    ├── src/
    └── package.json
```

---

## 5. Core Algorithm Specifications

### 5.1 Feature Engineering Pipeline

```
Raw Event (JSON) → Feature Extraction → [8-dimensional float vector]

Feature normalization:
  - failed_logins: raw integer count
  - cpu_usage: float [0.0, 1.0]
  - memory_spike: binary {0, 1}
  - ehr_access_per_hour: raw integer count
  - lateral_movement_events: raw integer count
  - data_export_volume_kb: raw float (kilobytes)
  - access_time_deviation: float (hours from baseline)
  - source_ip_reputation: float [0.0, 1.0] (0=malicious)
```

### 5.2 Ensemble Scoring Algorithm

```python
composite_score = Σ (weight[i] × P_attack[i]) for i in models
adjusted_score  = composite_score × CRITICALITY[asset_type] × DAMAGE[attack_type]
```

Where `P_attack[i]` is the calibrated probability output of model `i` using `CalibratedClassifierCV(method='isotonic', cv=5)`.

### 5.3 Tier Classification Logic

```
if adjusted_score < THRESHOLDS['low_medium_boundary']:  → Low
elif adjusted_score < THRESHOLDS['medium_high_boundary']: → Medium
else:                                                      → High
```

Default thresholds: Low/Medium = 0.3, Medium/High = 0.7

### 5.4 Audit Chain Block Structure

```json
{
  "block_index":  42,
  "timestamp":    "2026-08-15T07:10:00.000Z",
  "event_id":     "uuid-v4",
  "tier":         "High",
  "source_ip":    "hmac:token:abc123...",
  "actions_taken": ["ip_throttle", "db_snapshot"],
  "status":       "APPROVED",
  "prev_hash":    "sha256_of_previous_block",
  "entry_hash":   "sha256(current_content + prev_hash)",
  "block_hmac":   "hmac-sha256(payload, SESSION_SECRET)"
}
```

### 5.5 Password Hashing (Dashboard Auth)

```
Algorithm: PBKDF2-HMAC-SHA256
Iterations: 260,000 (OWASP 2023 recommendation)
Salt: 16 bytes (cryptographically random, per-password)
Key length: 32 bytes
Storage format: "pbkdf2:sha256:<iters>:<salt_hex>:<key_hex>"
```

---

## 6. API Endpoints (Dashboard — Flask)

### 6.1 Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/login` | None | Login with username/password → session token |
| POST | `/api/logout` | Session | Invalidate session |
| POST | `/api/register` | None | Submit registration request |

### 6.2 Data Endpoints (Admin-only)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/status` | Session | System health + active threat count |
| GET | `/api/metrics` | Session | Threat tier distribution + scoring metrics |
| GET | `/api/threats` | Session | Paginated threat log |
| GET | `/api/blocked_ips` | Session | Currently blocked IP list |
| GET | `/api/audit_chain` | Session | Last N blocks of audit chain |
| GET | `/api/alerts` | Admin | Pending High-tier authorization challenges |
| POST | `/api/alerts/<id>/respond` | Admin | Approve or deny a pending challenge |
| GET | `/api/admin/users` | Admin | List pending user registrations |
| POST | `/api/admin/users/<id>` | Admin | Approve/reject a user |
| GET | `/api/deception/status` | Admin | Mirage honeypot engagement stats |

### 6.3 Streaming
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/stream` | Session | SSE stream for real-time threat push events |

### 6.4 Static / Media
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/shap/<filename>` | Session | Serve SHAP explanation PNG |

---

## 7. ML Model Training Specification

### 7.1 Training Data
- **Source:** `data/sentinelhealth_dataset.csv` (synthetic)
- **Generator:** `data_generator.py`
- **Split:** 80% train / 20% test
- **Class balancing:** SMOTE (imbalanced-learn)
- **Noise injection:** Gaussian noise, scale=2.0%, to simulate sensor jitter
- **Boundary injection:** 1.0% boundary-case samples via grid search

### 7.2 Model Configuration
| Model | Class | Key Hyperparameters |
|-------|-------|---------------------|
| Random Forest | `RandomForestClassifier` | n_estimators=100, random_state=42 |
| XGBoost | `XGBClassifier` | use_label_encoder=False, eval_metric='mlogloss' |
| Gradient Boosting | `GradientBoostingClassifier` | n_estimators=100 |
| SVM | `SVC` | kernel='rbf', probability=True |
| Logistic Regression | `LogisticRegression` | max_iter=1000 |

All models wrapped in `CalibratedClassifierCV(method='isotonic', cv=5)`.

### 7.3 Poison Quarantine Gate
```python
POISON_DRIFT_THRESHOLD = 0.25  # 25% drop in High-tier fraction triggers quarantine
```
If the retraining candidate set's High-tier fraction drops >25% below the baseline, all Low-tier rows (except `source=='mirage_oracle'`) are quarantined to `logs/poison_quarantine.json`.

---

## 8. Security Architecture

### 8.1 Cryptographic Primitives
| Primitive | Usage | Implementation |
|-----------|-------|----------------|
| SHA-256 | Block entry hash, model manifest | `hashlib.sha256()` |
| HMAC-SHA-256 | Block HMAC, IP tokenization | `hmac.new(SESSION_SECRET, ...)` |
| PBKDF2-HMAC-SHA256 | Dashboard password storage | `hashlib.pbkdf2_hmac()` |
| AES-256 (via `cryptography`) | Crypto-shredding of PHI-adjacent data | `privacy/crypto_shred.py` |

### 8.2 Attack Simulation Capabilities
| Script | Attack Type | Phases |
|--------|-------------|--------|
| `exfiltration.py` | Data exfiltration (3-phase) | Recon → Escalation → Exfiltration |
| `brute_force.py` | Credential stuffing | Ramp-up → Sustained |
| `ddos.py` | Distributed Denial of Service | Flood → Sustained flood |
| `port_scan.py` | Network reconnaissance | Stealth scan → Aggressive |
| `tamper_chain.py` | Audit chain integrity test | Corruption → Detection |

---

## 9. Configuration Reference

### 9.1 Environment Variables (`.env`)
| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | — | Telegram Bot API token |
| `TELEGRAM_CHAT_ID` | — | Admin chat ID for alerts |
| `SENTIHEALTH_TEST_MODE` | `0` | `1` = skip real Telegram calls |

### 9.2 Threshold Configuration (`config/thresholds.json`)
```json
{
  "low_medium_boundary": 0.3,
  "medium_high_boundary": 0.7
}
```

### 9.3 Model Weights (hardcoded in `scoring_matrix.py`)
```python
WEIGHTS = {'rf': 0.25, 'gb': 0.20, 'svm': 0.20, 'lr': 0.15, 'xgb': 0.20}
```

---

## 10. Known Technical Limitations

| # | Limitation | Technical Impact |
|---|-----------|-----------------|
| L1 | Single-node audit ledger | Root attacker can delete `audit_chain.json` |
| L2 | IP-based feature grouping | Spoofed IPs dilute per-IP velocity metrics |
| L3 | Telegram requires internet | Violates strict air-gap; fails if network severed |
| L4 | Synthetic training data | Distribution shift when deployed against real attacks |
| L5 | No GPU acceleration | Inference latency may increase under heavy load |
| L6 | SQLite for `app.db` | Not suitable for multi-node or high-concurrency deployment |
