# Test-Driven Development (TDD) Guide
## SentiHealth — TDD Patterns and Test Blueprints

**Version:** 1.0  
**Last Updated:** 2026-08-15

---

## 1. TDD Philosophy for SentiHealth

SentiHealth follows a **security-first TDD approach**:
1. **Write the threat/attack test first** — define what a successful attack looks like
2. **Write the detection test** — define what correct detection looks like
3. **Write the response test** — define what correct remediation looks like
4. **Then implement** the feature that satisfies all three

> **Rule:** Any new security capability MUST have a failing test written BEFORE implementation begins.

---

## 2. Red-Green-Refactor Cycle for SentiHealth

```
RED   → Write a test for the new detection/response capability (it fails — feature not built yet)
GREEN → Implement the minimum code to make the test pass
REFACTOR → Clean up, ensuring the test still passes
SECURE → Add adversarial test (tamper attempt) to prove the feature is hardened
```

---

## 3. Existing Test Coverage (Green)

### 3.1 `test_sentinel.py`

| Test ID | Test Name | Status | What It Proves |
|---------|-----------|--------|----------------|
| TS-01 | `test_feature_extraction` | ✅ Green | Feature pipeline produces all 8 required fields |
| TS-02 | `test_threat_tier_classification` | ✅ Green | High-severity events score > 0.7 and receive tier=High |
| TS-03 | `test_blockchain_integrity` | ✅ Green | Tampered chain blocks trigger HALTED_CORRUPTION |
| TS-04 | `test_telegram_timeout_fallback` | ✅ Green | Admin timeout triggers auto-escalation |

### 3.2 `test_tiers.py`

| Test ID | Test Name | Status | What It Proves |
|---------|-----------|--------|----------------|
| TT-01 | Boundary low-medium | ✅ Green | Score just below 0.3 → Low |
| TT-02 | Boundary medium-high | ✅ Green | Score just above 0.7 → High |
| TT-03 | Mid-range medium | ✅ Green | Score 0.5 → Medium |

---

## 4. TDD Blueprints for Planned Features

Each blueprint follows the Red-Green-Refactor pattern.

---

### Blueprint 4.1: IPv6 Event Normalization

**Feature Goal:** `live_sentinel.py` should correctly parse IPv6 addresses and normalize them before feature extraction.

#### Step 1 — RED (Write Failing Test First)
```python
# test_sentinel.py — add this test BEFORE implementing IPv6 support
def test_ipv6_normalization(self):
    """IPv6 addresses should be normalized to compressed form."""
    from live_sentinel import normalize_source_ip
    
    # Full form → compressed
    assert normalize_source_ip("2001:0db8:0000:0000:0000:0000:0000:0001") == "2001:db8::1"
    
    # Loopback
    assert normalize_source_ip("::1") == "::1"
    
    # IPv4-mapped IPv6
    assert normalize_source_ip("::ffff:192.168.1.1") == "::ffff:192.168.1.1"
    
    # Regular IPv4 unchanged
    assert normalize_source_ip("10.0.0.1") == "10.0.0.1"
```
**Run:** `python -m pytest test_sentinel.py::TestSentinel::test_ipv6_normalization -v`  
**Expected:** `FAILED` (function doesn't exist yet)

#### Step 2 — GREEN (Implement Minimum)
```python
# live_sentinel.py
import ipaddress

def normalize_source_ip(raw_ip: str) -> str:
    """Normalize IPv4 and IPv6 addresses to compressed canonical form."""
    try:
        return str(ipaddress.ip_address(raw_ip))
    except ValueError:
        return raw_ip  # Preserve malformed IPs as-is; scoring handles them
```
**Run:** `python -m pytest test_sentinel.py::TestSentinel::test_ipv6_normalization -v`  
**Expected:** `PASSED`

#### Step 3 — REFACTOR + SECURE
```python
def test_ipv6_normalization_adversarial(self):
    """Malformed IPs should not crash the system."""
    from live_sentinel import normalize_source_ip
    assert normalize_source_ip("not_an_ip") == "not_an_ip"   # Graceful fallback
    assert normalize_source_ip("") == ""                       # Empty string safe
    assert normalize_source_ip("256.0.0.1") == "256.0.0.1"   # Out-of-range preserved
```

---

### Blueprint 4.2: Federated Learning Weight Aggregation

**Feature Goal:** A `federated_aggregator.py` module should merge model weight updates from multiple hospitals using FedAvg.

#### Step 1 — RED
```python
# test_federated.py (new file)
import pytest
from federated_aggregator import fedavg_weights

def test_fedavg_equal_weights():
    """FedAvg with equal sample sizes should average weights exactly."""
    weights_a = {'rf': [1.0, 2.0, 3.0], 'lr': [0.5, 1.5]}
    weights_b = {'rf': [3.0, 4.0, 5.0], 'lr': [1.5, 2.5]}
    
    result = fedavg_weights(
        [weights_a, weights_b], 
        sample_counts=[100, 100]
    )
    
    assert result['rf'] == pytest.approx([2.0, 3.0, 4.0])
    assert result['lr'] == pytest.approx([1.0, 2.0])

def test_fedavg_rejects_mismatched_shapes():
    """Weight vectors of different shapes should raise ValueError."""
    with pytest.raises(ValueError, match="shape mismatch"):
        fedavg_weights(
            [{'rf': [1.0, 2.0]}, {'rf': [1.0, 2.0, 3.0]}],
            sample_counts=[50, 50]
        )
```
**Run:** `python -m pytest test_federated.py -v`  
**Expected:** `FAILED` (module doesn't exist)

#### Step 2 — GREEN (Skeleton)
```python
# federated_aggregator.py
import numpy as np

def fedavg_weights(weight_lists: list[dict], sample_counts: list[int]) -> dict:
    total = sum(sample_counts)
    result = {}
    for key in weight_lists[0]:
        arrays = [np.array(w[key]) for w in weight_lists]
        # Shape check
        if len({a.shape for a in arrays}) > 1:
            raise ValueError(f"shape mismatch for key '{key}'")
        result[key] = sum(
            (n / total) * a for n, a in zip(sample_counts, arrays)
        ).tolist()
    return result
```

---

### Blueprint 4.3: Hyperledger Fabric Audit Chain Client

**Feature Goal:** Replace `_write_chain_atomic()` with a Fabric SDK client call.

#### Step 1 — RED
```python
# test_fabric_chain.py (new file)
from unittest.mock import MagicMock, patch

def test_fabric_block_append():
    """Block append should call the Fabric chaincode with correct payload."""
    with patch('fabric_chain_client.fabric_gateway') as mock_gw:
        mock_contract = MagicMock()
        mock_gw.get_network.return_value.get_contract.return_value = mock_contract
        
        from fabric_chain_client import append_block
        append_block({'tier': 'High', 'entry_hash': 'abc123'})
        
        mock_contract.submit_transaction.assert_called_once_with(
            'AppendBlock',
            '{"tier": "High", "entry_hash": "abc123"}'
        )

def test_fabric_integrity_on_tamper():
    """Chain query should detect a tampered block via Fabric."""
    with patch('fabric_chain_client.fabric_gateway') as mock_gw:
        mock_contract = MagicMock()
        mock_contract.evaluate_transaction.return_value = b'{"valid": false, "block": 3}'
        mock_gw.get_network.return_value.get_contract.return_value = mock_contract
        
        from fabric_chain_client import verify_chain
        result = verify_chain()
        assert result['valid'] == False
        assert result['tampered_block'] == 3
```

---

### Blueprint 4.4: STRIP Backdoor Defense

**Feature Goal:** Detect backdoor-injected training samples before model retraining.

#### Step 1 — RED
```python
# test_adversarial_robustness.py
import pandas as pd
import numpy as np

def test_strip_detects_backdoor():
    """STRIP defense should flag backdoored samples with high entropy."""
    from model_trainer import strip_defense
    
    # Clean sample — low entropy (consistent predictions)
    clean_sample = pd.DataFrame([{
        'failed_logins': 1, 'cpu_usage': 0.2, 'memory_spike': 0,
        'ehr_access_per_hour': 5, 'lateral_movement_events': 0,
        'data_export_volume_kb': 10, 'access_time_deviation': 0.1,
        'source_ip_reputation': 0.9
    }])
    
    # Backdoored sample — high entropy (inconsistent predictions when perturbed)
    backdoor_sample = pd.DataFrame([{
        'failed_logins': 1, 'cpu_usage': 0.2, 'memory_spike': 0,
        'ehr_access_per_hour': 5, 'lateral_movement_events': 0,
        'data_export_volume_kb': 10, 'access_time_deviation': 0.1,
        'source_ip_reputation': 0.9,
        '_backdoor_trigger': True  # Simulated trigger
    }])
    
    clean_entropy = strip_defense(clean_sample)
    backdoor_entropy = strip_defense(backdoor_sample)
    
    assert clean_entropy < 0.5, "Clean samples should have low prediction entropy"
    assert backdoor_entropy > 0.8, "Backdoored samples should have high entropy"
```

---

## 5. TDD Rules for SentiHealth Contributors

### 5.1 Feature Development Rules
| Rule | Enforcement |
|------|-------------|
| No new feature without a failing test first | PR review will reject code without prior test commit |
| Security-critical code needs adversarial test | Tamper/bypass tests required for audit chain, model loading, auth |
| Mock external services in unit tests | Telegram, filesystem writes must be mocked in unit tests |
| `SENTIHEALTH_TEST_MODE=1` for all CI runs | Prevents Telegram spam; enforced in `conftest.py` |
| Test must specify expected tier AND score range | `assert res['tier'] == 'High' and res['raw_score'] > 0.7` |

### 5.2 Test Naming Convention
```
test_<component>_<scenario>_<expected_outcome>

Examples:
  test_feature_extraction_brute_force_labels_correctly
  test_scoring_high_cpu_produces_high_tier
  test_chain_tampered_entry_halts_processing
  test_auth_wrong_password_returns_401
  test_shap_high_tier_generates_png
```

### 5.3 Test Isolation Requirements
```python
def setUp(self):
    # Each test starts with clean state
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('retraining', exist_ok=True)
    
    # Remove audit chain so each test gets fresh genesis block
    if os.path.exists('data/audit_chain.json'):
        os.remove('data/audit_chain.json')
```

---

## 6. Continuous Testing Workflow

### 6.1 Pre-Commit Hook (Recommended)
```bash
# .git/hooks/pre-commit
#!/bin/bash
export SENTIHEALTH_TEST_MODE=1
python -m pytest test_sentinel.py test_tiers.py -v --tb=short -q
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit blocked."
    exit 1
fi
```

### 6.2 CI Pipeline Steps
```yaml
# Recommended GitHub Actions workflow
steps:
  - name: Setup Python
    uses: actions/setup-python@v4
    with:
      python-version: '3.12'

  - name: Install dependencies
    run: pip install -r requirements.txt

  - name: Create required directories
    run: mkdir -p data logs retraining config models

  - name: Run unit tests
    env:
      SENTIHEALTH_TEST_MODE: "1"
    run: python -m pytest test_sentinel.py test_tiers.py -v --tb=short

  - name: Verify model manifest
    run: python3 -c "from scoring_matrix import load_models; load_models()"

  - name: Check audit chain integrity
    run: python3 -c "
    from self_healing_responder import _bootstrap_chain, verify_chain_integrity
    _bootstrap_chain()
    verify_chain_integrity()
    print('Chain integrity OK')
    "
```

---

## 7. Test Coverage Targets

| Module | Current Coverage | Target Coverage |
|--------|-----------------|-----------------|
| `scoring_matrix.py` | ~60% | 90% |
| `self_healing_responder.py` | ~45% | 85% |
| `live_sentinel.py` | ~40% | 80% |
| `model_trainer.py` | ~30% | 75% |
| `privacy/` | ~25% | 85% |
| `deception/` | ~20% | 70% |
| `dashboard.py` | ~20% | 70% |

### Measuring Coverage
```bash
pip install pytest-cov
export SENTIHEALTH_TEST_MODE=1
python -m pytest test_sentinel.py test_tiers.py \
  --cov=scoring_matrix \
  --cov=self_healing_responder \
  --cov=live_sentinel \
  --cov-report=term-missing
```
