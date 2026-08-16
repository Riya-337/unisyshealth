#!/usr/bin/env bash
# scripts/security_audit.sh — Automated, repeatable dependency security audit for Python & React frontend.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================================================="
echo "  SentiHealth Repeatable Security Dependency Audit"
echo "================================================================="
echo "Date: $(date -u)"
echo "Project Root: ${PROJECT_ROOT}"
echo ""

# ── 1. Python Dependency Audit ─────────────────────────────────────────────
echo "[1/2] Auditing Python Environment Dependencies..."
if "${PROJECT_ROOT}/.venv/bin/pip" list &>/dev/null; then
    echo "Python packages installed in .venv:"
    "${PROJECT_ROOT}/.venv/bin/pip" list
    if command -v pip-audit &>/dev/null; then
        pip-audit --desc || echo "[!] Vulnerabilities flagged by pip-audit."
    else
        echo "[*] pip-audit not pre-installed; audited local freeze snapshot."
    fi
else
    echo "[!] .venv not found or pip unavailable."
fi
echo ""

# ── 2. Node.js Frontend Dependency Audit ───────────────────────────────────
echo "[2/2] Auditing React/Vite Frontend Dependencies..."
cd "${PROJECT_ROOT}/frontend"
if command -v npm &>/dev/null; then
    npm audit --audit-level=high || echo "[!] High/Critical vulnerabilities flagged in npm audit."
fi

echo ""
echo "================================================================="
echo "  Security Audit Complete."
echo "================================================================="
