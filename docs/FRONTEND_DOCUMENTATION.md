# SentiHealth — Frontend Architecture & Functionality Documentation

> **Version:** 2.4.1  
> **Framework:** React 19 + TypeScript + Vite + TanStack Router + TailwindCSS  
> **Repository Path:** `frontend/`

---

## 1. Overview & Architecture

The **SentiHealth Frontend** is an air-gapped, zero-cloud operations dashboard and security portal designed for real-time cyberthreat monitoring in healthcare environments. It interfaces directly with the Flask backend API (`dashboard.py`) and live monitoring engine (`live_sentinel.py`) over local LAN via REST endpoints and Server-Sent Events (SSE).

### Technology Stack
- **UI Library:** React 19 (Functional TypeScript components with strict mode enabled)
- **Routing:** TanStack Router (`frontend/src/routes/`)
- **Build System:** Vite 7.3+
- **Styling:** Vanilla TailwindCSS + HSL color design system
- **Micro-Animations:** Framer Motion (`motion/react`)
- **Charts & Data Visualization:** Recharts (Donut, Bar, Risk Series charts)
- **Toast Notifications:** Sonner (Custom inline step-up authorization toasts)

---

## 2. Page Routes & User Flows

```text
[ Access Portal ] http://localhost:8080/
      ├── Login Form (PBKDF2 Password Check)
      ├── Account Registration Request Form
      └── Step-Up MFA / Backup Code Redemption Modal
            │
            ▼ (Session Token Granted: sessionStorage + localStorage)
[ Operations Dashboard ] http://localhost:8080/dashboard
      ├── 1. System Status Indicator (NORMAL / THREAT / LOCKDOWN)
      ├── 2. Blockchain Audit Ledger Status & Block Count
      ├── 3. MTTR (Mean-Time-To-Respond) Timer
      ├── 4. Recent Threat Detections Table (All / High / Medium / Low)
      ├── 5. Tier Distribution & Risk Score Gauge
      ├── 6. ML Ensemble Performance Metrics (RF, GB, SVM, LR, XGBoost)
      ├── 7. Real-Time High-Tier SSE Step-Up Authorization Toasts (90s Countdown)
      ├── 8. Expandable Detailed Analysis (Live Feed & Blocked IPs Table)
      └── 9. Admin SSHA Panels (Alerts Queue, Stasis Queue, Pending User Approvals)
```

---

## 3. Core Frontend Functionalities

### 3.1 Authentication & Custodian Security Gate (`frontend/src/routes/index.tsx`)
- **Dual-Factor Login:** Accepts administrator credentials (`admin` / `adminpass123`) or registered user emails.
- **Dynamic Risk-Adaptive MFA:** Displays a 2FA TOTP verification modal. Supports 6-digit TOTP codes from Google Authenticator / Authy or 64-character emergency backup recovery codes.
- **Dual Token Storage:** Saves `auth_token` to both `sessionStorage` and `localStorage` to preserve session state across browser refreshes and multi-tab workflows.
- **User Account Registration:** Allows new healthcare operators to submit access requests (`/api/auth/register`), which are queued for administrator sign-off.

---

### 3.2 Live System Status & Threat Telemetry (`frontend/src/components/dashboard/Dashboard.tsx`)
- **System Status Card:**
  - `NORMAL`: All network traffic nominal (Green badge).
  - `THREAT`: Elevated threat detected (Red pulsing badge).
  - `LOCKDOWN`: Multiple pending High-tier threats awaiting human decision (Orange pulsing badge).
- **Dual Audit Ledger Card:** Displays cryptographic chain status (`INTACT` or `COMPROMISED`) verified via SHA-256 and HMAC checks, along with total blocked IP counts.
- **MTTR Clock:** Real-time counter tracking response latency since the last detected threat.

---

### 3.3 Threat Detection Table & Tier Filtering
- **Multi-Tier View:** Displays the 10 most recent threat events.
- **Tier Filter:** Interactively filters threats by `All Tiers`, `High`, `Medium`, or `Low`.
- **SHAP Feature Importance Modal:** Clicking **SHAP** opens a modal fetching the model explanation PNG chart (`/api/shap/<filename>`) behind the authenticated custodian gate.
- **Threat Detail Drawer:** Clicking any row slides out a detailed drawer showing geolocation (City, Country), ML Risk Score gauge, attack nature, and UTC timestamp.

---

### 3.4 ML Ensemble Performance Panel
- **5-Model Comparison Table:** Renders accuracy, precision, recall, F1 score, and AUC-ROC metrics for all 5 calibrated machine learning models:
  1. `RF` (Random Forest — weight: 0.25)
  2. `GB` (Gradient Boosting — weight: 0.20)
  3. `SVM` (Support Vector Machine — weight: 0.20)
  4. `LR` (Logistic Regression — weight: 0.15)
  5. `XGB` (XGBoost — weight: 0.20)
- **Interactive Bar Chart:** Visualizes model AUC-ROC metrics side-by-side.

---

### 3.5 Real-Time Zero-Cloud SSE Step-Up Authorization (`useHighTierSSE`)
- **Zero-Cloud Stream:** Connects to `/api/stream?token=<token>` over EventSource.
- **Instant Toast Alert:** When a High-tier intrusion occurs, an inline red toast notification pops up with:
  - 90-second countdown timer before automated lockdown.
  - **`✓ YES — Approve`** button (Triggers forensic report generation).
  - **`✗ DENY — Defend`** button (Holds defensive posture).

---

### 3.6 Blocked IPs & Detailed Analysis Table
- **Complete Tier Coverage:** Displays all contained/blocked threats across **High**, **Medium**, and **Low** tiers.
- **Live Search:** Enables instantaneous IP filtering.
- **Action Badges:** Shows status tags (`AUTO-LOCKED`, `RESOLVED`, `FORENSICS GENERATED`, `DENIED`, `ADMIN RELEASED`).

---

### 3.7 Admin SSHA Control Panels (Admin Only)
- **Pending Challenges:** Shows unresolved High-tier authorization challenges.
- **Stasis Review Queue:** Displays expired/auto-locked threats allowing retro-active `Release Block` or `Confirm Block` decisions.
- **User Management Panel:** Lists pending registration requests with one-click **Approve** or **Reject** controls.

---

## 4. Key Security & Privacy Controls

1. **Air-Gapped Telemetry:** No external network or cloud services are invoked by the frontend.
2. **Custodian Access Gate:** Real IP addresses, SHAP charts, and audit logs are only rendered after session token validation.
3. **Browser Notifications:** Requests desktop notification permission for background tab alerting.
