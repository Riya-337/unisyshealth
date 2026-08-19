# AGENTS.md — SentiHealth Coding Agent Guidelines

> This file defines the authoritative rules, conventions, and guardrails for any AI coding agent (Antigravity, Copilot, Claude, Cursor, etc.) working in this repository.

---

## 1. Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | SentiHealth |
| **Domain** | Healthcare Cybersecurity |
| **Primary Language** | Python 3.10+ |
| **Frontend** | Node.js (EHR server), React/Vite (dashboard frontend) |
| **Framework** | Flask (dashboard API), scikit-learn + XGBoost (ML) |
| **Compliance Context** | HIPAA-adjacent (no real PHI; synthetic data only) |

---

## 2. Mandatory Reading Before Any Change

Before modifying any file, an agent MUST read:
1. `README.md` — full system overview and architecture
2. `_paths.py` — all canonical file path constants (NEVER hardcode paths)
3. The docstring of the module being edited
4. `requirements.txt` — do not introduce unlisted dependencies without approval

---

## 3. Code Style and Conventions

### 3.1 Python
- Follow **PEP 8** strictly; max line length: **100 characters**
- Use **type hints** on all function signatures
- Docstrings: **Google style** (`Args:`, `Returns:`, `Raises:`)
- Prefer `f-strings` over `.format()` or `%`
- Never use bare `except:` — always specify exception type
- All file I/O MUST go through paths defined in `_paths.py`

### 3.2 Naming Conventions
| Artifact | Convention | Example |
|----------|-----------|---------|
| Functions | `snake_case` | `score_event()` |
| Classes | `PascalCase` | `SentinelNotifier` |
| Constants | `UPPER_SNAKE_CASE` | `POISON_DRIFT_THRESHOLD` |
| Private helpers | `_leading_underscore` | `_block_hmac()` |
| Module-level singletons | `_leading_underscore` | `_tokenize_ip` |

### 3.3 JavaScript / TypeScript (frontend/)
- Use **TypeScript** with strict mode enabled
- Follow the existing ESLint config (`eslint.config.js`)
- Components: **PascalCase** functional components only
- Hooks: `use` prefix (`useThreats`, `useAuditChain`)

---

## 4. Architecture Rules — NEVER Violate

| Rule | Rationale |
|------|-----------|
| **No cloud calls** except Telegram | HIPAA air-gap requirement |
| **All paths via `_paths.py`** | Prevents path fragmentation across OS environments |
| **No real PHI** in any data file | Synthetic data only; HIPAA risk |
| **SHA-256 manifest must be updated** when any model file is modified | Prevents silent model tampering |
| **Audit chain writes MUST use `_write_chain_atomic()`** | Prevents partial-write corruption |
| **Never write real IPs to audit chain** | Use `_tokenize_ip()` from `privacy.pseudonymize` |
| **Models load via `load_models()` in `scoring_matrix.py`** | Do not load `.pkl` files directly elsewhere |
| **Feature vector MUST exclude `attack_type` and `tier_label`** | Data leakage guard — assertion enforced |

---

## 5. The 8 ML Features — Source of Truth

An agent MUST use exactly these 8 features (in this order) when constructing feature vectors:

```python
FEATURES = [
    'failed_logins',          # int: consecutive failed auth attempts
    'cpu_usage',              # float [0.0–1.0]: CPU utilization
    'memory_spike',           # int {0,1}: binary abnormal memory flag
    'ehr_access_per_hour',    # int: EHR record access frequency
    'lateral_movement_events',# int: cross-system access count
    'data_export_volume_kb',  # float: outbound data transfer in KB
    'access_time_deviation',  # float: hours deviation from baseline
    'source_ip_reputation',   # float [0.0–1.0]: 0=malicious, 1=trusted
]
```

**Adding a 9th feature requires:**
1. Updating `data_generator.py` to add the feature to training data
2. Retraining all 5 models with `model_trainer.py`
3. Updating the SHAP feature name list in `live_sentinel.py`
4. Updating `SentinelHealth_QA_Reference.md`
5. Incrementing the SHA-256 manifest

---

## 6. Threat Tier Thresholds

Thresholds are stored in `config/thresholds.json` and loaded at runtime:

```json
{
  "low_medium_boundary": 0.3,
  "medium_high_boundary": 0.7
}
```

An agent MUST NOT hardcode threshold values in Python — always read from `THRESHOLDS` dict in `scoring_matrix.py`.

---

## 7. Model Ensemble Weights

```python
WEIGHTS = {'rf': 0.25, 'gb': 0.20, 'svm': 0.20, 'lr': 0.15, 'xgb': 0.20}
```

Weights must sum to 1.0. Changing weights requires model re-evaluation against the test set in `MODEL_METRICS.md`.

---

## 8. Audit Chain Protocol

When writing a new block to `data/audit_chain.json`:
1. Compute `entry_hash = SHA-256(current_block_content + prev_entry_hash)`
2. Compute `block_hmac = HMAC-SHA256(block_payload, SESSION_SECRET)`
3. Use `_write_chain_atomic()` — never write directly to the chain file
4. If `entry_hash` of the previous block doesn't match on read → emit `HALTED_CORRUPTION`

---

## 9. Testing Requirements

Before submitting any PR:
- [ ] `python -m pytest test_sentinel.py -v` must pass (all 4 test cases)
- [ ] `python -m pytest test_tiers.py -v` must pass
- [ ] No new imports may be added to `requirements.txt` without documenting the reason in the PR description
- [ ] Any new feature that touches the audit chain MUST include a chain integrity test
- [ ] Any new ML feature MUST include a SHAP chart generation test

---

## 10. Security Guardrails for Agents

| Prohibited Action | Why |
|-------------------|-----|
| Removing or weakening `quarantine_check()` | Protects against model poisoning |
| Disabling SHA-256 model manifest verification | Protects against model swap attacks |
| Writing to `data/audit_chain.json` without using `_write_chain_atomic()` | Corruption risk |
| Exposing the Flask dashboard without auth | PII/admin panel exposure |
| Logging actual IPs to the audit chain (non-tokenized) | HIPAA privacy violation |
| Removing `SENTIHEALTH_TEST_MODE` guard for Telegram calls | Would spam the real Telegram bot during testing |

---

## 11. File Ownership Map

| Module | Owned By | Do Not Modify Without |
|--------|----------|----------------------|
| `scoring_matrix.py` | ML Team | Full model re-evaluation |
| `model_trainer.py` | ML Team | Dataset and metrics review |
| `self_healing_responder.py` | Security Team | Security review + chain test |
| `privacy/` | Privacy/Compliance | HIPAA impact assessment |
| `notifications/` | Ops Team | Telegram bot credential review |
| `deception/` | Red Team | Honeypot effectiveness review |
| `dashboard.py` | UI Team | Auth flow review |

---

## 12. Commit Message Format

```
<type>(<scope>): <short description>

Types: feat | fix | refactor | test | docs | chore | security
Scope: sentinel | scoring | responder | dashboard | privacy | deception | models | notifications

Examples:
  feat(sentinel): add IPv6 event normalization
  fix(scoring): correct feature-name mismatch in SHAP chart
  security(responder): enforce HMAC on all chain writes
```
