#!/usr/bin/env python3
"""
Stop-hook enforcer for Telegram replies.

Rule: if the last real user message arrived via Telegram, the assistant
must reply during this turn with at least one
`mcp__plugin_telegram_telegram__reply` call that attaches a `.ogg` file.
That single attachment covers both requirements — the reply carries the
text (Telegram requires non-empty text when files are attached) and the
voice is the `.ogg`.

The hook is a safety net, not the primary mechanism. Behavior is enforced
first by the `voice-reply` skill. This catches the clean failure mode:
forgot to call the tool at all.

Install:
  1. Place at ~/.claude/hooks/telegram-reply-enforcer.py
  2. chmod +x ~/.claude/hooks/telegram-reply-enforcer.py
  3. Register in ~/.claude/settings.json under Stop matcher ""

Configure: set YOUR_CHAT_ID below to your own Telegram user ID.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys


TELEGRAM_MARKER = 'source="plugin:telegram:telegram"'
REPLY_TOOL = "mcp__plugin_telegram_telegram__reply"
YOUR_CHAT_ID = "REPLACE_WITH_YOUR_CHAT_ID"
HOME = os.path.expanduser("~")
VOXTRAL_PATH = os.path.join(HOME, ".claude", "scripts", "voxtral-tts.py")


def _text_of(entry: dict) -> str:
    msg = entry.get("message", entry)
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        return " ".join(parts)
    return ""


def _reply_tool_uses(entry: dict) -> list[dict]:
    msg = entry.get("message", entry)
    content = msg.get("content", [])
    if not isinstance(content, list):
        return []
    return [
        c for c in content
        if isinstance(c, dict)
        and c.get("type") == "tool_use"
        and c.get("name") == REPLY_TOOL
    ]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        return 0

    p = pathlib.Path(transcript_path)
    if not p.exists():
        return 0

    entries = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    last_user_idx = None
    for i in range(len(entries) - 1, -1, -1):
        e = entries[i]
        if e.get("type") != "user":
            continue
        content = (e.get("message", {}) or {}).get("content", "")
        is_tool_result = False
        if isinstance(content, list):
            is_tool_result = any(
                isinstance(c, dict) and c.get("type") == "tool_result"
                for c in content
            )
        if is_tool_result:
            continue
        last_user_idx = i
        break

    if last_user_idx is None:
        return 0

    if TELEGRAM_MARKER not in _text_of(entries[last_user_idx]):
        return 0

    for e in entries[last_user_idx + 1:]:
        for tool_use in _reply_tool_uses(e):
            files = (tool_use.get("input") or {}).get("files") or []
            if any(str(f).lower().endswith(".ogg") for f in files):
                return 0

    print(json.dumps({
        "decision": "block",
        "reason": (
            f"The last user message arrived via Telegram. Every Telegram "
            f"turn must reply with BOTH text AND a Voxtral voice (.ogg) "
            f"attachment. Generate the voice via {VOXTRAL_PATH} and attach "
            f"it to a {REPLY_TOOL} call (to chat_id {YOUR_CHAT_ID}). "
            f"See the voice-reply skill for the full workflow."
        )
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
