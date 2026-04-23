#!/usr/bin/env python3
"""
PreToolUse hook: block Write/Edit/MultiEdit/NotebookEdit on source files
until ~/.claude/coding-guidelines.md has been Read in this session.

Scans the current session transcript for a prior Read of the guidelines file;
allows the edit if found, blocks otherwise with a clear reason.

Skips trivial content paths (wiki notes, memory files, plain .md writes) —
the guideline itself says "skip for trivial edits or content work".

Install:
  1. Place this file at ~/.claude/hooks/coding-guidelines-enforcer.py
  2. chmod +x ~/.claude/hooks/coding-guidelines-enforcer.py
  3. Register in ~/.claude/settings.json under PreToolUse matcher
     "Write|Edit|MultiEdit|NotebookEdit"
  4. Write your ~/.claude/coding-guidelines.md with your rules
"""
from __future__ import annotations

import json
import os
import pathlib
import sys


HOME = os.path.expanduser("~")
GUIDELINES_PATH = os.path.join(HOME, ".claude", "coding-guidelines.md")
GATED_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

# Paths where edits are content/config, not source code — skip gating.
SKIP_PREFIXES = (
    os.path.join(HOME, "knowledge") + os.sep,
    os.path.join(HOME, ".claude", "projects") + os.sep,   # auto-memory files
    os.path.join(HOME, ".claude", "channels") + os.sep,   # Telegram inbox
    "/tmp/",
    "/private/tmp/",
)
SKIP_SUFFIXES = (".md", ".txt", ".log")


def _guidelines_read_in_transcript(transcript_path: str) -> bool:
    p = pathlib.Path(transcript_path)
    if not p.exists():
        return False
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = entry.get("message", entry)
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use" and c.get("name") == "Read":
                fp = (c.get("input") or {}).get("file_path", "")
                if fp == GUIDELINES_PATH:
                    return True
    return False


def _should_skip(file_path: str) -> bool:
    if not file_path:
        return True
    if any(file_path.startswith(pre) for pre in SKIP_PREFIXES):
        return True
    if any(file_path.endswith(suf) for suf in SKIP_SUFFIXES):
        return True
    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = data.get("tool_name", "")
    if tool_name not in GATED_TOOLS:
        return 0

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if _should_skip(file_path):
        return 0

    transcript_path = data.get("transcript_path", "")
    if transcript_path and _guidelines_read_in_transcript(transcript_path):
        return 0

    print(json.dumps({
        "decision": "block",
        "reason": (
            "Mandatory: read ~/.claude/coding-guidelines.md before editing "
            "source files. Use the Read tool on that exact path, then retry "
            "this edit."
        )
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
