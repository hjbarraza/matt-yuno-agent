#!/usr/bin/env python3
"""
MCP Telegram health check — alerts you on Telegram if the plugin stops working.

Detects two failure modes:
  1. Bot process dead (pid gone) → "down"
  2. Bot process alive but stdio pipe broken (no heartbeat for >90s) → "stale"

Alert via direct Bot API (not MCP — which is exactly the thing being monitored).

Cooldown: writes ~/.claude/channels/telegram/health.state with "up" | "down" |
"stale". Only sends an alert on state transitions, not every run. Prevents spam.

Scheduled by a LaunchAgent every 300s. See the files/launchagents/ folder for
the plist template.

Configure: set CHAT_ID below to your Telegram user ID. DM @userinfobot to find it.

Requires: the server.ts patch that writes heartbeat.json every 10s (see
files/patches/server.ts.patch). Without the patch, stale-detection is skipped
and behavior falls back to pid-only monitoring.
"""
from __future__ import annotations

import json
import os
import pathlib
import time
import urllib.parse
import urllib.request


CHAT_ID = "REPLACE_WITH_YOUR_CHAT_ID"  # your Telegram user ID (DM @userinfobot)
CHANNEL_DIR = pathlib.Path.home() / ".claude" / "channels" / "telegram"
ENV_FILE = CHANNEL_DIR / ".env"
PID_FILE = CHANNEL_DIR / "bot.pid"
HEARTBEAT_FILE = CHANNEL_DIR / "heartbeat.json"
STATE_FILE = CHANNEL_DIR / "health.state"

# Heartbeat staleness threshold. server.ts writes every 10s; we allow 90s
# (9 heartbeats missed) before declaring the stdio pipe broken.
STALE_THRESHOLD_SEC = 90

MSG_DOWN = (
    "⚠️ MCP Telegram plugin down. "
    "Bot process is not running. "
    "Restart Claude Code to reconnect."
)
MSG_STALE = (
    "⚠️ MCP Telegram plugin stale. "
    "Process is alive but stdio pipe is broken (no heartbeat). "
    "Restart Claude Code to reconnect."
)
MSG_UP = "✅ MCP Telegram plugin back up."


def _load_token() -> str | None:
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _send(token: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    urllib.request.urlopen(req, timeout=5).read()


def _bot_alive() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _heartbeat_fresh() -> bool:
    """True if heartbeat.json was updated within STALE_THRESHOLD_SEC."""
    if not HEARTBEAT_FILE.exists():
        return False
    try:
        hb = json.loads(HEARTBEAT_FILE.read_text())
        updated_ms = int(hb.get("updatedMs", 0))
    except (ValueError, OSError):
        return False
    age_sec = time.time() - (updated_ms / 1000.0)
    return age_sec < STALE_THRESHOLD_SEC


def _current_status() -> str:
    """Returns 'up' | 'down' | 'stale'. 'stale' = pid alive but heartbeat stopped."""
    if not _bot_alive():
        return "down"
    # Heartbeat file may not exist yet on an older plugin build — treat as up.
    if not HEARTBEAT_FILE.exists():
        return "up"
    return "up" if _heartbeat_fresh() else "stale"


def _read_state() -> str:
    if not STATE_FILE.exists():
        return "up"
    return STATE_FILE.read_text().strip() or "up"


def _write_state(state: str) -> None:
    STATE_FILE.write_text(state)


def main() -> int:
    current = _current_status()
    previous = _read_state()

    if current == previous:
        return 0

    token = _load_token()
    if token:
        try:
            msg = {"up": MSG_UP, "down": MSG_DOWN, "stale": MSG_STALE}[current]
            _send(token, msg)
        except Exception:
            return 1

    _write_state(current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
