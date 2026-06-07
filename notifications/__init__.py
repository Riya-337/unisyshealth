"""
Notification package — lazy singleton factory.

Available backends (set "backend" in config/notifier.json):
  "sentinel"    — SentinelNotifier (SSHA): self-hosted, zero-cloud, default.
                  Alerts go to server console + logs/alert_queue.jsonl.
                  Authorization challenges resolved via the admin dashboard.
  "telegram"    — TelegramNotifier: legacy; requires TELEGRAM_BOT_TOKEN env var.
  "dual"        — DualNotifier: Telegram push to phone + SSHA dashboard/file IPC.
                  Best of both: instant phone alerts AND in-dashboard challenge flow.
                  Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
  "console"     — ConsoleNotifier: stdout only; useful for unit tests.

Usage (anywhere in the project):
    from notifications import get_notifier
    get_notifier().send_alert("Critical threat")
    result = get_notifier().request_authorization(None, timeout_sec=90)
"""

import json
import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Notifier

logger = logging.getLogger(__name__)

_notifier = None
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "notifier.json")


def get_notifier() -> "Notifier":
    """Return the process-wide Notifier singleton, building it on first call."""
    global _notifier
    if _notifier is None:
        _notifier = _build()
    return _notifier


def _build() -> "Notifier":
    config = _load_config()
    backend = config.get("backend", "sentinel").lower()

    if backend == "telegram":
        return _build_telegram(config.get("telegram", {}))

    if backend == "sentinel":
        return _build_sentinel(config.get("sentinel", {}))

    if backend == "dual":
        return _build_dual(config.get("telegram", {}))

    # Any unknown value (including old "aegis" or "local_smtp") → SSHA
    if backend not in ("console",):
        logger.warning(
            f"[Notifier] Unknown backend '{backend}' — defaulting to SentinelNotifier (SSHA)"
        )
        return _build_sentinel({})

    # Explicit console (unit tests / CI)
    logger.info("[Notifier] ConsoleNotifier active (explicit)")
    from .console import ConsoleNotifier
    return ConsoleNotifier()


def _load_config() -> dict:
    path = os.path.normpath(_CONFIG_PATH)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[Notifier] Could not read {path}: {e}")
        return {}


def _build_sentinel(cfg: dict) -> "Notifier":
    from .sentinel_notifier import SentinelNotifier
    logger.info("[Notifier] SentinelNotifier (SSHA) active — zero-cloud, self-hosted")
    return SentinelNotifier(cfg)


def _build_telegram(cfg: dict) -> "Notifier":
    token = os.environ.get(cfg.get("bot_token_env", "TELEGRAM_BOT_TOKEN"), "").strip()
    chat_id = os.environ.get(cfg.get("chat_id_env", "TELEGRAM_CHAT_ID"), "").strip()

    if not token or not chat_id:
        logger.warning(
            "[Notifier] Telegram credentials missing — falling back to SentinelNotifier (SSHA)"
        )
        return _build_sentinel({})

    from .telegram import TelegramNotifier
    logger.info("[Notifier] TelegramNotifier active")
    return TelegramNotifier(token, chat_id)


def _build_dual(cfg: dict) -> "Notifier":
    """Build DualNotifier: Telegram for push alerts + SentinelNotifier for dashboard IPC."""
    token = os.environ.get(cfg.get("bot_token_env", "TELEGRAM_BOT_TOKEN"), "").strip()
    chat_id = os.environ.get(cfg.get("chat_id_env", "TELEGRAM_CHAT_ID"), "").strip()

    sentinel = _build_sentinel({})

    if not token or not chat_id:
        logger.warning(
            "[Notifier] Dual mode: Telegram credentials missing — running Sentinel-only"
        )
        return sentinel

    from .telegram import TelegramNotifier
    from .dual_notifier import DualNotifier
    telegram = TelegramNotifier(token, chat_id)
    logger.info("[Notifier] DualNotifier active (Telegram + SSHA)")
    return DualNotifier(telegram, sentinel)
