# Testing Guide
## SentiHealth — Comprehensive Testing Strategy

**Version:** 1.0  
**Last Updated:** 2026-08-15

---

## 1. Testing Philosophy

SentiHealth applies a **defense-in-depth testing strategy** mirroring its security architecture:
- Every layer of the pipeline has dedicated tests
- Security-critical paths (audit chain, model integrity) are verified automatically
- Attack simulations serve as **end-to-end integration tests**
- All tests must pass before any PR is merged

---

## 2. Test Suite Overview

| Test File | Type | Coverage Area | Run Command |
|-----------|------|---------------|-------------|
| `test_sentinel.py` | Unit | Core pipeline (feature extraction, scoring, chain, Telegram) | `python -m pytest test_sentinel.py -v` |
| `test_tiers.py` | Unit | Tier boundary classification | `python -m pytest test_tiers.py -v` |
| `attack_scripts/tamper_chain.py` | Security | Audit chain tamper detection | `python3 attack_scripts/tamper_chain.py` |
| `evaluate_models.py` | ML Evaluation | Model accuracy, precision, recall, F1, AUC-ROC | `python3 evaluate_models.py` |
| `evaluate_models_v2.py` | ML Evaluation | Boundary stress test | `python3 evaluate_models_v2.py` |
| `demo_scenario.py` | E2E Integration | Full pipeline smoke test | `python3 demo_scenario.py` |
| `interactive_demo.py` | E2E Integration | Interactive attack → response cycle | `python3 interactive_demo.py` |

---

## 3. Unit Tests (`test_sentinel.py`)

### 3.1 Test: Feature Extraction
```python
def test_feature_extraction(self):
    stats = {'login': 50, 'patient': 0, 'total': 50}
    features = extract_features(stats)
    
    # Assertions:
    assert 'failed_logins' in features       # All 8 features present
    assert 'ehr_access_per_hour' in features
    assert 'cpu_usage' in features
    assert features['failed_logins'] == 50   # Value correctly extracted
    assert features['attack_type'] == 'brute_force'  # Rule-based classification
```
**Covers:** `live_sentinel.extract_features()`  
**Expected result:** All 8 ML features extracted; brute_force classification triggered at ≥5 failed_logins

---

### 3.2 Test: Threat Tier Classification
```python
def test_threat_tier_classification(self):
    features = {
        'failed_logins': 50, 'cpu_usage': 0.95, 
        'ehr_access_per_hour': 0, 'attack_type': 'brute_force', 
        'asset_type': 'workstation'
    }
    res = score_event(features)
    
    assert res['tier'] == 'High'
    assert res['raw_score'] > 0.7
```
**Covers:** `scoring_matrix.score_event()`  
**Expected result:** High-severity brute force → tier=High, score>0.7

---

### 3.3 Test: Blockchain Integrity Detection
```python
def test_blockchain_integrity(self):
    # Write 2 legitimate blocks
    respond(score_event(normal_features))  # Block 1
    respond(score_event(normal_features))  # Block 2
    
    # Corrupt Block 2
    chain[-1]['tier'] = 'High'
    with open('data/audit_chain.json', 'w') as f:
        json.dump(chain, f)
    
    # Block 3 should detect corruption
    resp = respond(score_event(normal_features))
    assert resp.get("status") == "HALTED_CORRUPTION"
```
**Covers:** `self_healing_responder.verify_chain_integrity()`  
**Expected result:** Tampered block detected; processing halted

---

### 3.4 Test: Telegram Timeout Fallback
```python
@patch('live_sentinel.get_notifier')
def test_telegram_timeout_fallback(self, mock_get_notifier):
    mock_notifier.request_authorization.return_value = "TIMEOUT"
    
    handle_high_tier_threat("1.2.3.4", features, res, "Test Alert")
    
    mock_notifier.send_summary.assert_called()
    assert any("AUTO-ESCALATION" in str(call) for call in ...)
```
**Covers:** `live_sentinel.handle_high_tier_threat()` with timeout scenario  
**Expected result:** When Telegram times out, auto-escalation summary is sent

---

## 4. Tier Boundary Tests (`test_tiers.py`)

Tests verify that tier classification boundaries work correctly:

| Test Case | Input Score | Expected Tier |
|-----------|-------------|---------------|
| Well below Low/Medium boundary | 0.10 | Low |
| At Low/Medium boundary - ε | 0.299 | Low |
| At Low/Medium boundary + ε | 0.301 | Medium |
| Mid-medium | 0.50 | Medium |
| At Medium/High boundary - ε | 0.699 | Medium |
| At Medium/High boundary + ε | 0.701 | High |
| Maximum score | 1.0 | High |

---

## 5. ML Model Evaluation

### 5.1 Running Evaluation
```bash
source .venv/bin/activate
python3 evaluate_models.py         # Standard test split evaluation
python3 evaluate_models_v2.py      # Boundary stress test evaluation
```

### 5.2 Minimum Acceptable Metrics

| Model | Min F1 | Min AUC-ROC |
|-------|--------|-------------|
| Random Forest | 0.55 | 0.52 |
| Gradient Boosting | 0.55 | 0.52 |
| SVM (RBF) | 0.50 | 0.50 |
| Logistic Regression | 0.55 | 0.52 |
| XGBoost | 0.55 | 0.52 |
| **Ensemble (weighted)** | **0.90** | **0.95** |

> **Note:** Individual model performance is intentionally moderate on the operational distribution (70/20/10 Low/Medium/High). The ensemble significantly outperforms any single model.

### 5.3 Regenerating Metrics
```bash
python3 generate_metrics.py    # Outputs evaluation_metrics.json
```

---

## 6. Security Tests

### 6.1 Audit Chain Tamper Test
```bash
python3 attack_scripts/tamper_chain.py
```
**What it does:**
1. Writes several legitimate blocks to `data/audit_chain.json`
2. Silently modifies a mid-chain entry (simulates attacker editing logs)
3. Attempts to write a new block
4. Verifies that `verify_chain_integrity()` detects the tampering

**Expected output:**
```
[CHAIN ALERT] Entry hash mismatch at block 3
[SENTINEL] Status: HALTED_CORRUPTION
```

### 6.2 Model Manifest Tamper Test (Manual)
```bash
# Corrupt a model file
echo "corrupted" >> models/calibrated_rf.pkl

# Attempt to start the sentinel
python3 live_sentinel.py
```
**Expected output:**
```
MODEL TAMPERED: rf
```
(Immediate SystemExit — sentinel refuses to start with a tampered model)

### 6.3 Poison Quarantine Test (Manual)
```bash
# Add suspicious Low-tier entries to the retraining queue
python3 -c "
import json
queue = [{'tier_label': 'Low', 'source': 'test'} for _ in range(100)]
json.dump(queue, open('retraining/retraining_queue.json', 'w'))
"

# Attempt retraining
python3 model_trainer.py
```
**Expected output:**
```
[POISON QUARANTINE] N rows quarantined (baseline High=X%, candidate=Y%). See logs/poison_quarantine.json.
```

---

## 7. Integration Tests (Attack Simulation)

### 7.1 Full Pipeline E2E Test

**Setup:**
```bash
# Terminal 1
source setup.sh && cd webapp && node app.js

# Terminal 2
export SENTIHEALTH_TEST_MODE=1
python3 live_sentinel.py

# Terminal 3
python3 dashboard.py
```

**Execute:**
```bash
# Terminal 4
python3 attack_scripts/exfiltration.py
```

**Verification Checklist:**
- [ ] Low-tier events appear in `logs/threat_log.json` with tier=Low
- [ ] Medium-tier events appear with tier=Medium and `blocked_ips.json` updated
- [ ] High-tier events trigger SHAP chart in `logs/shap_explanation_*.png`
- [ ] All events appear as hash-chained blocks in `data/audit_chain.json`
- [ ] Dashboard at `localhost:5001` shows live threat feed updating
- [ ] Console shows `[CHAIN] Block N appended` for each event

### 7.2 DDoS Simulation Test
```bash
python3 attack_scripts/ddos.py
```
**Expected:** Multiple Medium→High events detected; IP throttled; dashboard shows CPU spike pattern

### 7.3 Brute Force Simulation Test
```bash
python3 attack_scripts/brute_force.py
```
**Expected:** Failed login count escalates; account lockout triggered; Medium→High progression

---

## 8. Dashboard API Tests (Manual with curl)

### 8.1 Login
```bash
curl -X POST http://localhost:5001/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
# Expected: { "token": "...", "role": "admin" }
```

### 8.2 Get Threats (Authenticated)
```bash
curl http://localhost:5001/api/metrics \
  -H "Authorization: Bearer <token>"
# Expected: { "low": N, "medium": N, "high": N, "total": N }
```

### 8.3 Reject Unauthenticated Access
```bash
curl http://localhost:5001/api/metrics
# Expected: 401 Unauthorized
```

### 8.4 Admin Approve High-Tier Challenge
```bash
curl -X POST http://localhost:5001/api/alerts/<challenge_id>/respond \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "approve"}'
# Expected: { "status": "approved" }
```

---

## 9. Privacy Layer Tests

### 9.1 Pseudonymization
```bash
python3 demo_pseudonymize.py
```
**Verify:**
- Same IP always produces the same HMAC token (deterministic)
- Different IPs produce different tokens
- Original IP is not recoverable from token alone

### 9.2 Crypto-Shredding
```bash
python3 demo_crypto_shred.py
```
**Verify:**
- Data encrypted successfully
- Decryption works with key present
- After key deletion, decryption fails (data irrecoverable)

---

## 10. Pre-Merge Checklist

Before any pull request is merged, verify ALL of the following:

```bash
# 1. All unit tests pass
python -m pytest test_sentinel.py test_tiers.py -v

# 2. No import errors
python3 -c "import live_sentinel; import scoring_matrix; import self_healing_responder"

# 3. Model manifest is current (if models were retrained)
python3 -c "from scoring_matrix import load_models; load_models(); print('Models OK')"

# 4. Audit chain integrity
python3 -c "
from self_healing_responder import verify_chain_integrity
result = verify_chain_integrity()
print('Chain OK' if result else 'CHAIN CORRUPTED')
"

# 5. All 8 features present in feature extraction
python3 -c "
from live_sentinel import extract_features
f = extract_features({'login': 5, 'patient': 10, 'total': 15})
required = ['failed_logins','cpu_usage','memory_spike','ehr_access_per_hour',
            'lateral_movement_events','data_export_volume_kb',
            'access_time_deviation','source_ip_reputation']
assert all(k in f for k in required), f'Missing features: {set(required) - set(f)}'
print('Feature extraction OK')
"
```

---

## 11. Test Environment Setup

```bash
# Create isolated test environment
source setup.sh

# Set test mode (disables real Telegram calls)
export SENTIHEALTH_TEST_MODE=1

# Create required directories
mkdir -p data logs retraining config models

# Run full test suite
python -m pytest test_sentinel.py test_tiers.py -v --tb=short
```

**Test mode effects when `SENTIHEALTH_TEST_MODE=1`:**
- Telegram API calls are mocked/skipped
- Real Telegram bot is not spammed
- All other functionality is identical to production
