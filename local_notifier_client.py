"""
SentiHealth Local Desktop Notifier Client — Zero-Cloud Alerting.

Consumes the Flask dashboard's Server-Sent Events (SSE) stream over LAN (/api/stream),
displays real-time desktop notifications (via plyer) with sound/visual alert text for
High-tier threats and authorization challenges, and functions independently on admin workstations.

Usage:
    python3 local_notifier_client.py [--url http://localhost:5001] [--token <session_token>]
"""

import argparse
import json
import logging
import os
import sys
import time
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("local_notifier_client")

try:
    from plyer import notification
    _HAS_PLYER = True
except ImportError:
    _HAS_PLYER = False
    logger.warning("[Notifier Client] plyer package not found. Desktop notifications will fall back to terminal alerts.")


def trigger_desktop_notification(title: str, message: str, is_high: bool = True):
    """Raise native OS desktop notification."""
    logger.info(f"ALERT: {title} — {message}")
    print("\a", end="", flush=True)  # System bell audio chime
    if _HAS_PLYER:
        try:
            notification.notify(
                title=title[:64],
                message=message[:256],
                app_name="SentiHealth Sentinel",
                timeout=10,
            )
        except Exception as e:
            logger.debug(f"plyer notification exception: {e}")


def _auto_authenticate(server_url: str, username: str = "admin", password: str = "", totp_code: str = "") -> str:
    """Obtain session token from dashboard API via user login."""
    url = f"{server_url.rstrip('/')}/api/auth/login"
    try:
        if not password and not sys.stdin.isatty():
            # In non-interactive batch test environment, attempt standard admin auth
            password = os.environ.get("SENTIHEALTH_ADMIN_PASSWORD", "adminpass123")

        if not password:
            import getpass
            print(f"\n[Notifier Client] Authentication required for SSE stream access on {server_url}")
            username = input(f" Username [{username}]: ").strip() or username
            password = getpass.getpass(" Password: ")

        res1 = requests.post(url, json={"username": username, "password": password}, timeout=10)
        if res1.status_code != 200:
            logger.error(f"[Notifier Client] Login failed: {res1.json().get('message', 'Invalid credentials')}")
            return ""

        stage = res1.json().get("stage")
        if stage == "otp":
            if not totp_code and not sys.stdin.isatty():
                totp_code = os.environ.get("SENTIHEALTH_TOTP_CODE", "")
            if not totp_code:
                totp_code = input(" 6-Digit TOTP / Recovery Code: ").strip()
            v_res = requests.post(f"{server_url.rstrip('/')}/api/auth/verify-otp", json={"username": username, "code": totp_code}, timeout=10)
            if v_res.status_code == 200 and v_res.json().get("success"):
                token = v_res.json().get("token", "")
                logger.info(f"[Notifier Client] Authentication successful for user '{username}'.")
                return token
            else:
                logger.error(f"[Notifier Client] TOTP verification failed: {v_res.json().get('message', 'Invalid code')}")
                return ""
        elif "token" in res1.json():
            return res1.json()["token"]
    except Exception as e:
        logger.error(f"[Notifier Client] Auto-auth exception: {e}")
    return ""


def listen_sse_stream(server_url: str, token: str = ""):
    """Consume SSE stream from dashboard server."""
    if not token:
        token = os.environ.get("SENTIHEALTH_SESSION_TOKEN", "")

    headers = {"Accept": "text/event-stream"}

    while True:
        endpoint = f"{server_url.rstrip('/')}/api/stream"
        if token:
            endpoint += f"?token={token}"

        logger.info(f"[Notifier Client] Connecting to zero-cloud SSE alert stream: {endpoint}")
        try:
            with requests.get(endpoint, headers=headers, stream=True, timeout=60) as response:
                if response.status_code == 401:
                    logger.warning("[Notifier Client] Authentication required (401). Attempting authentication...")
                    token = _auto_authenticate(server_url)
                    if not token:
                        logger.error("[Notifier Client] Could not obtain valid session token. Retrying in 10s...")
                        time.sleep(10)
                    continue
                if response.status_code != 200:
                    logger.warning(f"[Notifier Client] SSE endpoint returned status {response.status_code}. Retrying in 5s...")
                    time.sleep(5)
                    continue

                logger.info("[Notifier Client] Connected to SentiHealth SSE stream — listening for High-tier alerts...")
                current_event = None
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data_str = line.split(":", 1)[1].strip()
                        try:
                            data = json.loads(data_str)
                            process_sse_event(current_event, data)
                        except Exception as parse_err:
                            logger.debug(f"Error parsing SSE data: {parse_err}")
                        current_event = None

        except requests.exceptions.RequestException as req_err:
            logger.warning(f"[Notifier Client] SSE connection disconnected ({req_err}). Reconnecting in 3s...")
            time.sleep(3)
        except KeyboardInterrupt:
            logger.info("[Notifier Client] Shutting down notifier client.")
            sys.exit(0)


def process_sse_event(event_type: str, data: dict):
    """Parse SSE event payload and trigger alert if actionable."""
    if event_type in ("authorization_required", "high_tier_alert") or data.get("tier") == "High":
        incident_id = data.get("incident_id") or data.get("event_id") or "N/A"
        ip = data.get("ip") or data.get("source_ip") or "Unknown IP"
        score = data.get("score") or data.get("raw_score") or "0.00"
        reason = data.get("reason") or data.get("attack_type") or "High Threat Action Required"

        title = f"🚨 HIGH THREAT ALERT [{tier_str(data)}]"
        message = f"IP: {ip} | Score: {score}\nReason: {reason}\nChallenge ID: {incident_id[:8]}"

        trigger_desktop_notification(title, message, is_high=True)

        print("\n" + "=" * 60)
        print(f"\033[91m[SENTINEL DESKTOP ALERT] {title}\033[0m")
        print(f"  Incident ID : {incident_id}")
        print(f"  Source IP   : {ip}")
        print(f"  Risk Score  : {score}")
        print(f"  Reason      : {reason}")
        if "shap_values" in data or "top_features" in data:
            print(f"  SHAP Drivers: {data.get('top_features') or data.get('shap_values')}")
        print(f"  Action      : Open Dashboard or submit TOTP step-up authorization")
        print("=" * 60 + "\n", flush=True)

    elif event_type == "medium_tier_alert" or data.get("tier") == "Medium":
        title = "⚠️ MEDIUM THREAT DETECTED"
        message = f"IP: {data.get('ip', 'Unknown')} — Automated containment applied."
        trigger_desktop_notification(title, message, is_high=False)


def tier_str(data: dict) -> str:
    return str(data.get("tier") or "HIGH").upper()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentiHealth Local Desktop Notifier Client")
    parser.add_argument("--url", default=os.environ.get("SENTIHEALTH_DASHBOARD_URL", "http://localhost:5001"), help="Dashboard base URL")
    parser.add_argument("--token", default=os.environ.get("SENTIHEALTH_SESSION_TOKEN", ""), help="Session token if auth required")
    parser.add_argument("--username", default="admin", help="Admin username for auto-authentication")
    parser.add_argument("--password", default="", help="Admin password for auto-authentication")
    parser.add_argument("--totp", default="", help="TOTP code for auto-authentication")
    args = parser.parse_args()

    token = args.token
    if not token and (args.password or args.totp):
        token = _auto_authenticate(args.url, args.username, args.password, args.totp)

    listen_sse_stream(args.url, token)

