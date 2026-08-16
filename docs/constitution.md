# Constitution
## SentiHealth — Principles, Ethics, and Inviolable Commitments

**Version:** 1.0  
**Status:** Foundational Document — All Contributors Must Acknowledge  
**Last Updated:** 2026-08-15

---

> *"In the domain of healthcare, cybersecurity is not a product feature — it is a patient safety obligation. Every design decision in SentiHealth must be evaluated first through the lens of patient outcomes, then through the lens of operational efficiency."*

---

## Article I — Mission and Purpose

**Section 1.1 — Core Mission**  
SentiHealth exists to protect patient data, clinical availability, and human life from cyber threats targeting healthcare systems — without compromising the privacy, dignity, or safety of patients.

**Section 1.2 — Who We Serve**  
In order of priority:
1. **Patients** — their data, privacy, and continuity of care are sacrosanct
2. **Clinical Staff** — their ability to access EHR systems during emergencies must never be compromised by false positives
3. **Hospital Administrators** — their authority to approve or reject automated actions is respected and enforced
4. **Security Analysts** — they receive transparent, explainable, and auditable information

**Section 1.3 — What SentiHealth Is Not**  
- Not a surveillance tool for monitoring employee behavior
- Not a tool for identifying or tracking patients
- Not a cloud service (HIPAA air-gap requirement)
- Not a replacement for human judgment in High-tier decisions

---

## Article II — Privacy as a First Principle

**Section 2.1 — No Real PHI**  
SentiHealth MUST NEVER process, store, or transmit real Protected Health Information (PHI). All training data is synthetic. This is an inviolable constraint.

**Section 2.2 — Pseudonymization by Default**  
All identifiers (IP addresses, user IDs) written to exportable audit artifacts MUST be HMAC-tokenized via `privacy.pseudonymize.tokenize()`. The authenticated dashboard may display real identifiers to authorized admins. External exports may not.

**Section 2.3 — Data Minimization**  
SentiHealth collects only the 8 ML features required for threat scoring. No additional user profiling, behavioral tracking, or data aggregation beyond threat detection is permitted.

**Section 2.4 — Crypto-Shredding**  
When data associated with a patient or user must be deleted, SentiHealth MUST use cryptographic erasure (`privacy/crypto_shred.py`): encrypting the data, then deleting the key — making recovery impossible even with physical access to storage.

**Section 2.5 — Right to Audit**  
Every admin action, every automated response, and every model inference that led to a patient-impacting decision MUST be preserved in the cryptographic audit ledger and available for forensic review.

---

## Article III — Human-in-the-Loop as a Non-Negotiable

**Section 3.1 — High-Tier Events Require Human Authorization**  
No High-tier automated response (database snapshot, full lockdown, account deletion) shall execute without explicit human approval. This is not a configurable option — it is a constitutional requirement.

**Section 3.2 — Admin Authority is Sovereign**  
An admin's rejection of a High-tier response MUST be honored. The system MAY escalate via summary notification, but it shall not override a human rejection.

**Section 3.3 — Informed Decisions Only**  
Admins MUST be provided with:
- The composite threat score
- The individual model scores
- A SHAP waterfall chart explaining which features drove the decision
- The proposed response actions and their reversibility

Blind approval flows (where the admin cannot see the underlying evidence) are prohibited.

**Section 3.4 — Auto-Escalation Is an Emergency Failsafe, Not a Bypass**  
When an admin does not respond within the timeout window, the system MAY send a summary notification. It shall NOT automatically execute High-tier actions. Auto-escalation means "notify more loudly," not "act autonomously."

---

## Article IV — Transparency and Explainability

**Section 4.1 — Every High-Tier Detection Must Be Explainable**  
A black-box "threat detected" message is unacceptable for High-tier events. Every such event MUST produce a SHAP explanation chart showing which of the 8 features drove the ensemble's decision.

**Section 4.2 — The Audit Chain Is the System's Memory**  
Every action taken by SentiHealth — detection, response, approval, rejection, escalation — MUST be recorded in `data/audit_chain.json` within 1 second of occurrence. There are no off-the-record actions.

**Section 4.3 — Chain Integrity Is Sacred**  
The SHA-256 hash chain and HMAC validation exist to make the audit record tamper-evident. Any code change that weakens this cryptographic guarantee is a constitutional violation. If integrity is broken, the system MUST halt (`HALTED_CORRUPTION`) rather than continue logging to a compromised record.

**Section 4.4 — Model Decisions Must Be Reproducible**  
Model files are checksummed via SHA-256 manifest. If a model file changes without a corresponding manifest update, the system refuses to start. This ensures the model making decisions today is the model that was tested and approved.

---

## Article V — Safety First in Healthcare Contexts

**Section 5.1 — Clinical Availability Trumps Security Lockouts**  
When in doubt between security (blocking a potentially malicious user) and clinical availability (allowing a clinician to access EHR during an emergency), the system MUST escalate to a human admin rather than making an autonomous lockout decision.

**Section 5.2 — Emergency Override is Always Possible**  
Hospital IT staff must always have a documented, tested manual override procedure to restore access even if SentiHealth is fully locked down or offline. SentiHealth must not be the single point of failure for clinical access.

**Section 5.3 — False Positives Are Not Acceptable for Clinical Staff**  
Blocking a nurse or physician from accessing patient records during an active emergency could be life-threatening. The system must be tuned to prefer false negatives over false positives for accounts flagged as `role: clinical`.

---

## Article VI — Security as a System Property

**Section 6.1 — Defense in Depth**  
No single component of SentiHealth is trusted absolutely. The ensemble mitigates single-model failures. The audit chain detects single-node corruption. The poison quarantine gate mitigates admin-level model poisoning.

**Section 6.2 — Adversarial Assumptions**  
SentiHealth operates under the assumption that:
- Attackers may attempt to manipulate the retraining pipeline (model poisoning)
- Attackers may attempt to tamper with the audit log (log falsification)
- Attackers may spoof IP addresses (velocity metric dilution)
- Attackers may gain admin credentials (insider threat)

Defenses must be designed against these assumptions, not against idealized threat models.

**Section 6.3 — The Mirage Principle**  
Deceiving an active attacker with honeypot data is an ethical and legally defensible defensive measure in this context. Mirage engagement data is labeled honestly in the retraining pipeline (`source='mirage_oracle'`) and is never used to falsely accuse a legitimate user.

**Section 6.4 — No Security by Obscurity**  
The cryptographic security of SentiHealth must not depend on keeping the algorithm secret. HMAC keys are kept secret; the HMAC algorithm itself is standard and public.

---

## Article VII — Responsible AI and ML Ethics

**Section 7.1 — No Biased Features**  
The 8 ML features are chosen based on network behavior signals, not on user demographics, geography, or any protected characteristic. A user's race, religion, national origin, or other personal attributes must never influence the threat score.

**Section 7.2 — Model Performance Must Be Audited Regularly**  
Model metrics must be reviewed before each production deployment. A model that performs well on training data but introduces systematic bias against specific user roles or IP ranges must be corrected before deployment.

**Section 7.3 — Synthetic Training Data Disclaimer**  
SentiHealth's models are trained on synthetic data. Contributors and operators must acknowledge that:
- Models may perform differently on real hospital traffic distributions
- Continuous retraining with real (anonymized) data is required for production deployment
- Performance claims in `MODEL_METRICS.md` apply to the synthetic benchmark only

**Section 7.4 — Model Poisoning is an Existential Threat**  
An attacker who can corrupt the training pipeline can make SentiHealth blind to specific attack signatures. The poison quarantine gate, SHA-256 manifest, and human review of the retraining queue are the primary defenses. These defenses MUST NOT be removed or weakened.

---

## Article VIII — Operational Ethics

**Section 8.1 — Zero Tolerance for Silent Failures**  
A SentiHealth component that fails must fail loudly — logged to the audit chain, surfaced to the admin dashboard, and included in the SSE alert stream. Silent failures that allow threats to pass undetected are worse than system downtime.

**Section 8.2 — Transparent Limitations**  
Known limitations (see `FUTURE_WORK.md`) must be documented, communicated to operators, and never hidden. A hospital deploying SentiHealth must understand what it cannot do.

**Section 8.3 — The Principle of Least Privilege**  
Every system component accesses only the data it needs:
- The ML ensemble never writes to the audit chain
- The dashboard exposes real IPs only to authenticated admins
- The Mirage module never modifies real EHR records

**Section 8.4 — No Vendor Lock-In by Design**  
SentiHealth uses open-source components (Python, scikit-learn, XGBoost, Flask) and open standards (SHA-256, HMAC, PBKDF2, JSONL). Any hospital should be able to audit, modify, and operate SentiHealth without dependency on proprietary vendors.

---

## Article IX — Contributor Commitments

By contributing to SentiHealth, every contributor commits to:

1. **Reading and acknowledging** this Constitution before their first commit
2. **Prioritizing patient safety** over feature velocity
3. **Never introducing** real PHI into the codebase or test fixtures
4. **Writing tests first** for all security-critical changes
5. **Documenting limitations** of every new feature in `FUTURE_WORK.md`
6. **Respecting the audit chain** — every change that affects what is logged or how it is verified requires security review
7. **Declaring conflicts of interest** — contributors who are also security researchers studying hospital attack vectors must declare this affiliation

---

## Article X — Amendments

This Constitution may be amended by:
1. A written proposal describing the change and its rationale
2. Review by at least 2 senior contributors
3. A 72-hour comment period
4. Unanimous approval by all reviewers

**No amendment may weaken the protections in Articles II (Privacy), III (Human-in-the-Loop), or IV (Transparency).**

---

*This document was established on 2026-08-15 as the foundational ethical and operational charter of the SentiHealth project.*
