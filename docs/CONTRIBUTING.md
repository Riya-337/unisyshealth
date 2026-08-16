# SentiHealth — Engineering Change Management & Governance

> **Version:** 1.0  
> **Target Audience:** All AI Coding Agents, Security Engineers, and Healthcare IT Contributors.

---

## 1. Core Engineering Principles

1. **Constitutional Inviolability:** Any change modifying `HALTED_CORRUPTION`, human-in-the-loop TOTP step-up authentication, or zero-cloud air-gap guarantees is **strictly forbidden**.
2. **ML Contract Lock:** The 8-feature vector schema (`FEATURES`), model ensemble weights (`WEIGHTS`), and threat tier thresholds (`THRESHOLDS`) **MUST NOT** be modified without full model retraining and re-evaluation.
3. **No Unverified Claims:** Every pull request (PR) or commit must include empirical runtime verification logs demonstrating clean test suite execution (`pytest`) and frontend build compilation (`npm run build`).

---

## 2. Mandatory Branching & Merge Strategy

```text
[ Feature Branch: feat/topic ]
            │
            ▼
[ Automated CI / Local Pre-Merge Test Suite ]
            │
            ▼
[ Staging Environment Smoke Test ] (Mirrors hospital deployment)
            │
            ▼
[ Mandatory Peer / Security Review Sign-off ]
            │
            ▼
[ Merge to master / Production Branch ]
```

### Branch Rules:
- **`master` Branch:** Protected branch. Direct pushes prohibited in multi-developer setups. All changes enter via verified pull requests.
- **Naming Conventions:**
  - `feat/<scope>`: New features or capabilities.
  - `fix/<scope>`: Bug fixes and issue resolutions.
  - `security/<scope>`: Security hardening or cryptographic updates.
  - `docs/<scope>`: Documentation improvements.

---

## 3. Pre-Merge Checklist (Definition of Done)

Before submitting or merging any change, the following checklist **MUST** be executed cleanly:

- [ ] **Python Unit Tests:** All 15 tests pass cleanly:
      ```bash
      python3 -m pytest tests/ -v --tb=short
      ```
- [ ] **Dual Audit Ledger Integrity:** Chain verification succeeds:
      ```bash
      python3 -c "from self_healing_responder import verify_chain_integrity; assert verify_chain_integrity()"
      ```
- [ ] **Frontend Build Compilation:** Vite production build compiles with 0 errors:
      ```bash
      cd frontend && npm run build
      ```
- [ ] **Security Audit:** Repeatable dependency audit executed:
      ```bash
      bash scripts/security_audit.sh
      ```
- [ ] **Local Health Check:** Infrastructure health monitor runs clean:
      ```bash
      python3 scripts/health_monitor.py --once
      ```
- [ ] **No Hardcoded Paths:** All path references go through `_paths.py`.
- [ ] **No Unlisted Dependencies:** No new third-party packages introduced without architectural review.
