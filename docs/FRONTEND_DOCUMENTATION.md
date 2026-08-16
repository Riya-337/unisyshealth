# SentiHealth — Frontend Architecture & Security Documentation

> **Version:** 2.4.2  
> **Framework:** React 19 + TypeScript + Vite 7.3+ + TanStack Router + TailwindCSS  
> **Repository Path:** `frontend/`

---

## 1. Structure Verification & Routing Architecture

Every route and component listed below has been verified against the actual codebase (`frontend/src/routes/` and `frontend/src/components/dashboard/`):

### 1.1 Verified File Structure
```text
frontend/src/
├── routes/
│   ├── __root.tsx             # Root layout & global HTML head metadata
│   ├── index.tsx              # Login & Access Request Portal
│   └── dashboard.tsx          # Operations Dashboard Route wrapper
├── components/
│   └── dashboard/
│         ├── Dashboard.tsx    # Main Operations Dashboard & Admin Control Panels
│         └── GeoMap.tsx       # Offline Geolocation Visualization Widget
├── lib/
│   ├── sentinel-data.ts       # API data mapper, SSE hook, and fallback definitions
│   └── audit-log.ts           # Emergency local audit helper
└── styles.css                 # Global HSL CSS design system
```

---

## 2. Authentication, Session Security & Data Isolation

### 2.1 Session Token Persistence (`sessionStorage` Only)
- **Security Design Rationale:** Session authentication tokens (`auth_token`) are strictly saved in **`sessionStorage` ONLY**.
- **Removal of `localStorage`:** `localStorage` persistence was deliberately **removed** to prevent XSS script token theft across tabs. For a security operations panel with lockdown authority, storing session tokens in `localStorage` would allow any injected script to read the session token and bypass administrative authentication controls.
- **Session Lifespan:** `sessionStorage` ensures the token is automatically wiped from browser memory when the tab or window is closed.

### 2.2 User Registration & Admin Approval Workflow
1. **User Sign-up:** Users submit credentials via `POST /api/auth/register` on the `/` access portal (`index.tsx`).
2. **Pending Queue:** Account status is stored as `"pending"` in `data/users.json`.
3. **Admin Sign-Off:** Authenticated administrators review and approve accounts via the **Pending Registration Approvals** panel on the `/dashboard` route using `POST /api/admin/users/<username>/approve`.

---

## 3. 90-Second Step-Up Authorization & Timeout Protocol

### 3.1 Unambiguous Timeout Behavior
When a **High-tier threat** is detected by `live_sentinel.py`, an authorization challenge is broadcast to authenticated administrator sessions via Server-Sent Events (`/api/stream`).

```text
[ High-Tier Threat Detected ]
           │
           ▼
[ SSE Broadcast: /api/stream ] ──► Admin Browser Toast (90s Countdown)
           │
     ┌─────┴─────────────────────────────┐
     ▼                                   ▼
Admin Responds in <90s             90s Countdown Expires
┌──────────────────────────┐       ┌─────────────────────────────────────┐
│ • YES: Forensics generated│       │ • NO DESTRUCTIVE ACTION EXECUTED    │
│ • DENY: Aborted          │       │ • Incident queued in Stasis Panel   │
└──────────────────────────┘       │ • Auto-escalation summary sent      │
                                   │ • Awaits human review (Stasis Panel)│
                                   └─────────────────────────────────────┘
```

### 3.2 Constitution Article III.4 Compliance
- **No Automatic Destructive Actions:** Per **Constitution Article III.4**, High-tier threats **MUST NOT** trigger automated destructive actions or permanent IP bans without explicit human sign-off via TOTP step-up authentication.
- **Stasis Review Queue Behavior:** When the 90-second countdown expires without admin intervention, `live_sentinel.py` **does not execute an automated IP ban**. Instead, it:
  1. Marks the incident status as `"auto-locked"` (stasis) in `logs/threat_log.json`.
  2. Sends an auto-escalation notification summary (`send_summary()`) to operators.
  3. Queues the event in the **Stasis Review Queue** (`/api/alerts/stasis`).
  4. Requires an authenticated admin to log in to the dashboard and retroactively select **Release Block** or **Confirm Block**.

---

## 4. Terminology Audit & SSE Admin Panels

### 4.1 Terminology Reconciliation
- The acronym **SSHA** in backend logs and container element IDs stands for **Sentinel Self-Healing Architecture**.
- In all user-facing documentation and frontend interfaces, these controls are formally designated as **SSE-Based Admin Control Panels**.

### 4.2 Admin Control Panel Capabilities
When an authenticated administrator (`is_admin === true`) logs into `/dashboard`, the following specialized control panels are rendered:
1. **Admin Alerts Queue:** Real-time High-tier authorization challenges with step-up TOTP verification.
2. **Stasis Review Queue:** Post-timeout review queue for retroactively approving or dismissing auto-locked threats.
3. **Pending Users Panel:** Account approval interface for new operator registration requests.

---

## 5. Geolocation Drawer & Data Minimization Audit

### 5.1 Origin of the Feature
- **Origin:** The **Geolocation Drawer (City, Country)** was introduced as a visual UI representation widget (`GeoMap.tsx` / `sentinel-data.ts`) to provide security operators with dynamic location context during threat triage.
- **PRD/TRD Status:** It is **not** a mandated requirement in the core PRD, TRD, or Constitution.

### 5.2 IP Handling & Offline Implementation
- **Offline Deterministic Lookup:** Geolocation lookup is performed strictly **offline in-browser** (`geoForIP()`) using static IP subnet prefix matching and mathematical seed modulo mapping.
- **Zero External API Calls:** No external cloud geolocation services or APIs (e.g. MaxMind, ipinfo.io) are called, preserving the 100% zero-cloud air-gap guarantee.

### 5.3 Data Minimization Governance Flag
> [!NOTE]  
> **Data Minimization Audit Note:** In accordance with HIPAA privacy standards and Constitution Article IV (IP Pseudonymization via `_tokenize_ip()`), exact IP geographic plotting is classified as an **optional presentation-layer feature**. Real IP addresses remain strictly gated behind administrator authentication (`_require_auth`).

---

## 6. Real-Time SSE Event Specifications

| Event Name | Source Endpoint | Description | Frontend Handler |
|------------|-----------------|-------------|------------------|
| `connected` | `/api/stream` | Initial SSE connection handshake | `useHighTierSSE()` |
| `threat_update` | `/api/stream` | Pushed when a new scored threat is logged | `useSentinel()` |
| `high_alert` | `/api/stream` | Triggers 90s step-up authorization toast | `useHighTierSSE()` |
| `stasis_resolved` | `/api/stream` | Pushed when an admin acts on a stasis challenge | `StasisPanel()` |
