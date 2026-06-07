"""
DualNotifier — runs BOTH TelegramNotifier and SentinelNotifier simultaneously.

  • send_alert()            → Telegram (phone push) + SSHA log (dashboard/file)
  • request_authorization() → SSHA file-based challenge (dashboard UI) +
                              Telegram push so admin knows to open the dashboard
  • send_summary()          → SSHA log only (no Telegram spam)

This lets the admin get instant phone pings (new account requests, approvals,
ngrok URL) while the dashboard challenge/auth system keeps working exactly as
before through the SSHA file-IPC mechanism.
"""

from __future__ import annotations

import logging

from .base import Notifier

logger = logging.getLogger(__name__)


class DualNotifier(Notifier):
    """
    Wraps a TelegramNotifier (push to phone) and a SentinelNotifier (SSHA
    dashboard/file-based IPC).  Both are used for alerts; only SSHA is used
    for authorization challenges (the dashboard handles approve/deny).
    """

    def __init__(self, telegram: Notifier, sentinel: Notifier) -> None:
        self._telegram = telegram
        self._sentinel = sentinel

    # ------------------------------------------------------------------
    # send_alert  — goes to both Telegram AND SSHA log
    # ------------------------------------------------------------------

    def send_alert(self, message: str, photo_path: str = None) -> bool:
        # Send to Telegram (phone notification)
        try:
            self._telegram.send_alert(message, photo_path)
        except Exception as e:
            logger.warning(f"[DualNotifier] Telegram send_alert failed: {e}")

        # Also log via SSHA (dashboard alert queue + console)
        try:
            self._sentinel.send_alert(message, photo_path)
        except Exception as e:
            logger.warning(f"[DualNotifier] Sentinel send_alert failed: {e}")

        return True

    # ------------------------------------------------------------------
    # request_authorization — SSHA handles the file-based challenge
    #   (the dashboard UI shows approve/deny buttons).
    #   Telegram sends a push so the admin knows to open the dashboard.
    # ------------------------------------------------------------------

    def request_authorization(
        self,
        prompt: str | None,
        timeout_sec: int = 90,
        accept_ignore: bool = False,
        metadata: dict | None = None,
    ) -> str:
        # Telegram push — tell admin to open the dashboard
        try:
            self._telegram.send_alert(
                f"🔔 ADMIN ACTION REQUIRED\n"
                f"{prompt or 'High-tier threat — open the dashboard to respond.'}\n"
                f"⏱ You have {timeout_sec}s to respond via the dashboard."
            )
        except Exception as e:
            logger.warning(f"[DualNotifier] Telegram auth-push failed: {e}")

        # SSHA handles the actual file-based challenge / polling
        try:
            result = self._sentinel.request_authorization(
                prompt,
                timeout_sec=timeout_sec,
                accept_ignore=accept_ignore,
                metadata=metadata,
            )
            return result
        except Exception as e:
            logger.error(f"[DualNotifier] Sentinel request_authorization failed: {e}")
            return "TIMEOUT"

    # ------------------------------------------------------------------
    # send_summary — SSHA log only (no Telegram to avoid spam)
    # ------------------------------------------------------------------

    def send_summary(self, message: str) -> bool:
        try:
            self._sentinel.send_summary(message)
        except Exception as e:
            logger.warning(f"[DualNotifier] Sentinel send_summary failed: {e}")
        return True
