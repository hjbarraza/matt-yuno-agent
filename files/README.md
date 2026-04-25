# Bonus pack — Implementation files + advanced extras

> Matt: **read status first.** Much of what this pack originally taught has been promoted into the main [`SETUP-PROMPT.md`](../SETUP-PROMPT.md) and [`STACK-GUIDE.md`](../STACK-GUIDE.md). Those now walk you through installing the required pieces directly.
>
> This folder is the **source of truth** for those implementation files — the hook scripts, skill SKILL.md files, Voxtral helper, LaunchAgent plist, and server.ts patch. The setup prompt copies from here.
>
> What's still optional: the four skills `boot`, `reflect`, `seven-rules`, `firewall-check`. Install after you've used the base stack for a week.

Everything here is sanitized — my operator's personal details, entity names, and specific identifiers have been replaced with placeholders you'll fill in.

## What's in this folder

```
files/
├── README.md                          ← you are here
├── coding-guidelines.md               ← drop in ~/.claude/
├── skills/                            ← drop each folder into ~/.claude/skills/
│   ├── boot/SKILL.md                  session-start dashboard
│   ├── voice-reply/SKILL.md           Telegram text+voice contract
│   ├── voice-filter/SKILL.md          strip AI tropes before sending
│   ├── reflect/SKILL.md               end-of-session goal-progress check
│   ├── seven-rules/SKILL.md           pre-action + post-session enforcement
│   └── firewall-check/SKILL.md        confidentiality between projects/clients
├── hooks/                             ← drop each file into ~/.claude/hooks/
│   ├── coding-guidelines-enforcer.py  blocks code edits until guidelines loaded
│   └── telegram-reply-enforcer.py     blocks session stop without voice reply
├── scripts/                           ← drop each file into ~/.claude/scripts/
│   ├── kokoro-tts.py                  text→speech helper (Kokoro 82M, fast default, ~3s wall time)
│   ├── voxtral-tts.py                 text→speech helper (Voxtral 4B, slower ~30s wall time but more personality)
│   ├── TTS-TUNING.md                  ← READ FIRST — chunking strategy + Voxtral params + writing style (saves a debugging evening)
│   └── mcp-health-check.py            detects MCP disconnect (patched-server-aware)
├── launchagents/
│   └── mcp-health.plist               runs the health check every 300s
└── patches/
    └── server.ts.patch                add heartbeat + stderr tee to the Telegram plugin
```

## Install order (recommended)

> **Shortcut:** if you're following [`SETUP-PROMPT.md`](../SETUP-PROMPT.md) or [`STACK-GUIDE.md`](../STACK-GUIDE.md), steps 1, 2, 3, 4, 5, and 6 below are done for you automatically. This ordered install is useful when (a) you're picking pieces à la carte, or (b) something broke and you want to install one thing at a time.

The pack has dependencies. Install in this order — later pieces assume earlier pieces exist.

### Step 1 — Coding guidelines + hook

Why first: protects your codebase from hasty edits before the agent has loaded the rules.

```bash
cp files/coding-guidelines.md ~/.claude/coding-guidelines.md
mkdir -p ~/.claude/hooks
cp files/hooks/coding-guidelines-enforcer.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/coding-guidelines-enforcer.py
```

Register in `~/.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [{ "type": "command", "command": "/Users/YOUR_USERNAME/.claude/hooks/coding-guidelines-enforcer.py" }]
      }
    ]
  }
}
```

Test: open `claude`, ask it to edit any `.py` file. It should refuse until you've done a `Read` on `~/.claude/coding-guidelines.md`.

### Step 2 — Skills

Drop each skill folder into `~/.claude/skills/`. The agent discovers them automatically on session start.

```bash
cp -r files/skills/* ~/.claude/skills/
```

Each `SKILL.md` has a frontmatter block with `description` — that's what the agent reads to decide when to invoke. Customize the descriptions to fit your own vocabulary if you want.

### Step 3 — TTS script (pick Kokoro, Voxtral, or both)

Two engines ship in `files/scripts/`:

| Engine | Wall time | Best for |
|---|---|---|
| **Kokoro 82M** (recommended default) | ~3s for 10s of audio | Speed, auto-language-detect, 54 voices across 9 languages |
| **Voxtral 4B** | ~30s for 10s of audio | A distinctive, more-designed voice. ~10x slower than Kokoro. |

**Install Kokoro (fast, recommended):**
```bash
pip install mlx-audio
cp files/scripts/kokoro-tts.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/kokoro-tts.py
```
First run auto-downloads the Kokoro model (~175 MB) + spaCy (~50 MB). Default voice is `bf_emma` (British female). Script auto-detects language in the text and switches voice to `ef_dora` for Spanish, `ff_siwis` for French, `if_sara` for Italian, `pf_dora` for Portuguese; override per-call with `--voice <preset>`.

**Install Voxtral (slower, more personality):**
```bash
python3.11 -m venv ~/voice-venv            # must be 3.11; voxtral-mlx breaks on 3.13+
source ~/voice-venv/bin/activate
pip install 'mlx-audio[tts]' huggingface_hub tiktoken
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='mlx-community/Voxtral-4B-TTS-2603-mlx-4bit')"
cp files/scripts/voxtral-tts.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/voxtral-tts.py
```
Update the shebang in the copied script to `#!~/voice-venv/bin/python3`, or always invoke the script with that Python explicitly. Default voice is `neutral_female` (English-safe). Language-prefixed presets (`fr_female`, `it_male`, `es_female`, ...) need matching-language text — feeding English to `fr_female` sounds wrong.

**Running both side-by-side:** install both. Call `kokoro-tts.py` from the voice-reply skill as the daily driver; call `voxtral-tts.py` explicitly for marquee messages where personality > speed. Both scripts share the same CLI contract (`text --output file.ogg [--voice preset]`) and return JSON with `{success, file_path, duration, provider, voice}`, so wiring them interchangeably is trivial.

### Step 4 — Telegram reply enforcer hook

Only install this after you've tested the Telegram MCP plugin and voxtral-tts.py works end-to-end.

```bash
cp files/hooks/telegram-reply-enforcer.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/telegram-reply-enforcer.py
```

Edit the file: set `YOUR_CHAT_ID` to your Telegram user ID (DM `@userinfobot` on Telegram to find it).

Register in `~/.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [
      { "matcher": "", "hooks": [{ "type": "command", "command": "/Users/YOUR_USERNAME/.claude/hooks/telegram-reply-enforcer.py" }] }
    ]
  }
}
```

### Step 5 — Server.ts patch (for debuggability + heartbeat)

The stock Telegram plugin swallows its own stderr. When it dies, you get nothing useful. This patch adds:
- stderr tee to `~/.claude/channels/telegram/server.log`
- `heartbeat.json` written every 10s (enables stale-detection)
- `shutdown(reason)` logging so you know *why* the plugin died

```bash
cd ~/.claude/plugins/cache/claude-plugins-official/telegram/0.0.6
cp server.ts server.ts.bak-$(date +%Y%m%d-%H%M)
patch -p3 < /path/to/files/patches/server.ts.patch
```

**Caveat**: this patch lives in the Claude Code plugin cache. If you update/reinstall the plugin, the patch gets wiped. Re-apply after updates, or open a PR upstream.

Restart Claude Code for the patch to take effect (`/exit` then re-launch).

Verify:
```bash
cat ~/.claude/channels/telegram/heartbeat.json      # should have current pid + recent updatedMs
tail ~/.claude/channels/telegram/server.log         # should have boot lines with timestamps
```

### Step 6 — Health-check script + LaunchAgent

Only useful after step 5 (the script depends on heartbeat.json for full coverage).

```bash
cp files/scripts/mcp-health-check.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/mcp-health-check.py
```

Edit the script: set `CHAT_ID` to your Telegram user ID.

Install the LaunchAgent:
```bash
# Replace YOUR_USERNAME in the plist first
sed -i '' "s/YOUR_USERNAME/$(whoami)/g" files/launchagents/mcp-health.plist
# Also change the Label to something unique for you, e.g. com.yourdomain.mcp-health
cp files/launchagents/mcp-health.plist ~/Library/LaunchAgents/com.yourdomain.mcp-health.plist
launchctl load ~/Library/LaunchAgents/com.yourdomain.mcp-health.plist
```

Verify:
```bash
launchctl list | grep mcp-health    # should show the agent
```

Every 300s it'll check bot.pid + heartbeat.json. You'll get a Telegram message if the plugin dies or goes stale. If the state stays "up", it stays silent.

## What you end up with

After installing all six steps:

- **Agent behavior is opinionated**: it refuses to edit code without reading guidelines first, it must reply to Telegram with voice, it runs a dashboard on every `/boot`.
- **Debugging is tractable**: when the Telegram MCP breaks (and it will, eventually), you have server.log and heartbeat.json to diagnose. You get pinged on your phone within 5 minutes when it goes sideways.
- **The agent has a stance**: seven-rules enforces the principles you set, voice-filter enforces your voice, firewall-check enforces confidentiality between your walled-off work streams.

## What you should NOT just copy verbatim

- **The rule contents themselves** — write your own seven rules. Mine (or H's) wouldn't fit you.
- **The firewall definitions** — those are personal to each operator's client/project map. Create your own `wiki/topics/firewalls.md` from scratch.
- **The voice** — `voice-filter/SKILL.md` has generic anti-tropes. Add your own banned phrases and preferred cadence.
- **The assistant's identity** — name her/him/it whatever you want; define the persona in your own `~/.claude/CLAUDE.md`, not mine.

## Minimum-safe-subset if the full pack is too much

If you just want the two highest-leverage pieces:
1. `hooks/telegram-reply-enforcer.py` + `skills/voice-reply/` + `skills/voice-filter/` — ensures every Telegram reply has text + voice, stripped of AI tropes. This is the piece that makes the agent feel like a real assistant instead of a chatbot.
2. `patches/server.ts.patch` + `scripts/mcp-health-check.py` + LaunchAgent — gives you observability into the plugin and ping-back-to-you when it breaks. Without this, silent failures will eat hours.

Everything else is polish. These two are load-bearing.

## Questions

Most of the "why did we build it this way" answers live in the skills themselves. If something feels confusing, open the corresponding `SKILL.md` and read the rationale. The pattern for the whole setup: name the behavior in a markdown file, let the agent route to it via descriptions, enforce the non-negotiables with a hook.

If a skill fires when it shouldn't (or fails to fire when it should), update its `description:` frontmatter. That's the dispatcher.

Good luck.
