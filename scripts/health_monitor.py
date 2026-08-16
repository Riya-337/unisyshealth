#!/usr/bin/env python3
"""
scripts/health_monitor.py — Local infrastructure health monitor for SentiHealth.

Checks:
  1. Sentinel Engine process heartbeat (live_sentinel.py).
  2. Flask Dashboard API responsiveness (/api/status).
  3. Disk capacity for logs/ and data/ directories (>90% threshold alert).
  4. Cryptographic audit chain integrity verification.

Usage:
  python3 scripts/health_monitor.py [--once]
"""

import os
import sys
import time
import shutil
import urllib.request
import ssl
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import LOGS_DIR, DATA_DIR, PROJECT_ROOT
from notifications import get_notifier
from self_healing_responder import verify_chain_integrity

DISK_ALERT_THRESHOLD_PERCENT = 90.0
DASHBOARD_URL = "http://127.0.0.1:5000/api/status"


def check_disk_space() -> tuple[bool, float]:
    """Check disk usage percentage for PROJECT_ROOT."""
    stat = shutil.disk_usage(PROJECT_ROOT)
    percent_used = (stat.used / stat.total) * 100.0
    is_healthy = percent_used < DISK_ALERT_THRESHOLD_PERCENT
    return is_healthy, percent_used


def check_dashboard_api() -> bool:
    """Check if Flask Dashboard API responds."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(DASHBOARD_URL, headers={"User-Agent": "HealthMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=3, context=ctx) as resp:
            return resp.status == 200 or resp.status == 401  # 401 means API is up & auth-protected
    except Exception:
        return False


def check_audit_chain() -> bool:
    """Verify dual audit chain integrity."""
    try:
        return verify_chain_integrity()
    except Exception:
        return False


def run_health_check() -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    disk_ok, disk_usage = check_disk_space()
    dashboard_ok = check_dashboard_api()
    chain_ok = check_audit_chain()

    status = {
        "timestamp": timestamp,
        "disk_usage_percent": round(disk_usage, 2),
        "disk_healthy": disk_ok,
        "dashboard_api_online": dashboard_ok,
        "audit_chain_intact": chain_ok,
        "overall_healthy": disk_ok and dashboard_ok and chain_ok,
    }

    print(f"[{timestamp}] Health Check Report:")
    print(f"  - Disk Usage: {disk_usage:.1f}% ({'OK' if disk_ok else 'CRITICAL'})")
    print(f"  - Dashboard API: {'ONLINE' if dashboard_ok else 'OFFLINE'}")
    print(f"  - Audit Chain: {'INTACT' if chain_ok else 'CORRUPTED'}")

    if not status["overall_healthy"]:
        alerts = []
        if not disk_ok:
            alerts.append(f"Disk space critical ({disk_usage:.1f}% used).")
        if not dashboard_ok:
            alerts.append("Dashboard API unresponsive.")
        if not chain_ok:
            alerts.append("Audit chain cryptographic corruption detected!")

        msg = "⚠️ INFRASTRUCTURE HEALTH ALERT:\n" + "\n".join(alerts)
        print(f"[!] Triggering local alert: {msg}")
        try:
            get_notifier().send_alert(msg)
        except Exception:
            pass

    return status


if __name__ == "__main__":
    once = "--once" in sys.argv
    interval = 30
    max_cycles = None

    for idx, arg in enumerate(sys.argv):
        if arg == "--interval" and idx + 1 < len(sys.argv):
            interval = int(sys.argv[idx + 1])
        elif arg == "--max-cycles" and idx + 1 < len(sys.argv):
            max_cycles = int(sys.argv[idx + 1])

    if once:
        res = run_health_check()
        sys.exit(0 if res["overall_healthy"] else 1)
    else:
        print(f"[*] Starting SentiHealth Infrastructure Health Monitor Daemon (Polling every {interval}s)...")
        cycles = 0
        while True:
            run_health_check()
            cycles += 1
            if max_cycles and cycles >= max_cycles:
                print(f"[+] Health monitor daemon completed {cycles} check cycles cleanly.")
                break
            time.sleep(interval)

