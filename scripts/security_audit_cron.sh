#!/usr/bin/env bash
# scripts/security_audit_cron.sh — Recurring cron/systemd wrapper for security_audit.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${PROJECT_ROOT}/logs/security_audit.log"

mkdir -p "${PROJECT_ROOT}/logs"

{
    echo "================================================================="
    echo "  SentiHealth Scheduled Security Audit"
    echo "  Execution Time: $(date -u)"
    echo "================================================================="
    bash "${SCRIPT_DIR}/security_audit.sh"
    echo "  Audit execution complete at $(date -u)"
    echo "================================================================="
    echo ""
} >> "${LOG_FILE}" 2>&1

echo "[+] Scheduled security audit executed cleanly. Output logged to ${LOG_FILE}"
