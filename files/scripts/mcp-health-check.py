#!/usr/bin/env python3
"""
MCP Telegram health check — alerts you on Telegram if the plugin stops working.

Reads ~/.claude/channels/telegram/bot.pid. If the PID is not a live process,
the MCP stdio connection is dead (the plugin's orphan watchdog kills itself
when Claude Code disconnects).

Alert via direct Bot API (not MCP — which is exactly the thing that's down).

Cooldown: writes ~/.claude/channels/telegram/health.state with "down" or "up".
Only sends an alert on state transitions, not every run. Prevents spam.
Also sends a "back up" message when the bot recovers.

Scheduled by ai.yuno.mcp-health.plist (LaunchAgent) every 300s.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import time
import urllib.parse
import urllib.request


CHAT_ID = "REPLACE_WITH_YOUR_CHAT_ID"
CHANNEL_DIR = pathlib.Path.home() / ".claude" / "channels" / "telegram"
ENV_FILE = CHANNEL_DIR / ".env"
PID_FILE = CHANNEL_DIR / "bot.pid"
HEARTBEAT_FILE = CHANNEL_DIR / "heartbeat.json"
STATE_FILE = CHANNEL_DIR / "health.state"

# Heartbeat staleness threshold. server.ts writes every 10s; we allow 90s
# (9 heartbeats missed) before declaring the stdio pipe broken.
STALE_THRESHOLD_SEC = 90

# Auto-reconnect via tmux send-keys. The watchdog sends `/mcp reconnect ...`
# into the running claude REPL. Requires:
#   1. Claude is launched inside a tmux session (default name: "aeris")
#   2. tmux is installed (brew install tmux)
# Override session name with AERIS_TMUX_SESSION env var.
TMUX_SESSION = os.environ.get("AERIS_TMUX_SESSION", "aeris")
RECONNECT_CMD = "/mcp reconnect plugin:telegram:telegram"

MSG_DOWN = "⚠️ MCP Telegram plugin down. Auto-reconnect attempted via tmux."
MSG_STALE = "⚠️ MCP Telegram plugin stale (no heartbeat). Auto-reconnect attempted via tmux."
MSG_RECONNECT_FAILED = (
    "⚠️ Auto-reconnect failed. Tap /mcp en Claude Code para reconectar manualmente."
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


def _tmux_session_exists() -> bool:
    tmux = shutil.which("tmux")
    if not tmux:
        return False
    try:
        r = subprocess.run(
            [tmux, "has-session", "-t", TMUX_SESSION],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _send_reconnect_via_tmux() -> bool:
    """Inject /mcp reconnect command into the claude REPL via tmux send-keys.
    Returns True if the command was sent (not whether it succeeded)."""
    tmux = shutil.which("tmux")
    if not tmux or not _tmux_session_exists():
        return False
    try:
        subprocess.run(
            [tmux, "send-keys", "-t", TMUX_SESSION, RECONNECT_CMD, "Enter"],
            check=True, capture_output=True, timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False


def main() -> int:
    current = _current_status()
    previous = _read_state()

    if current == previous:
        return 0

    token = _load_token()

    if current in ("down", "stale"):
        # Try auto-reconnect via tmux first.
        sent = _send_reconnect_via_tmux()

        # Wait for the reconnect to land + heartbeat to refresh.
        if sent:
            time.sleep(8)
            recovered = _current_status() == "up"
            if recovered:
                # Self-healed silently — log state, don't spam telegram.
                _write_state("up")
                return 0
            # Reconnect didn't take; alert with failure message.
            if token:
                try:
                    _send(token, MSG_RECONNECT_FAILED)
                except Exception:
                    return 1
        else:
            # Couldn't send reconnect (tmux missing or session not found) — alert.
            if token:
                try:
                    msg = MSG_DOWN if current == "down" else MSG_STALE
                    _send(token, msg)
                except Exception:
                    return 1
    else:
        # Transition to "up" — recovery message.
        if token:
            try:
                _send(token, MSG_UP)
            except Exception:
                return 1

    _write_state(current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
