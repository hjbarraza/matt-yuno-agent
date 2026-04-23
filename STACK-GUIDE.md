# Personal AI Chief of Staff — Mac Setup

> Long-form manual. For the fastest path (one copy/paste and a conversation), see [`SETUP-PROMPT.md`](./SETUP-PROMPT.md). Use *this* doc when you want to understand *why* something is set up a particular way, or to debug.

## What this is

A personal AI agent that lives on your Mac, listens on Telegram (voice + text), talks back with a synthesized voice, and maintains a durable wiki of everything it learns. Claude Code is the runtime. Everything else is bolt-on.

The pieces you interact with day-to-day:

- **Telegram** — input/output channel. Voice notes from your phone get transcribed and answered with both text and a voice reply.
- **Your assistant's name + persona** — identity file that shapes tone, rules, priorities.
- **Knowledge wiki** — the long memory. Anything worth remembering goes here, auto-maintained.

Plumbing you stop thinking about once it's running:

- Whisper (speech → text), Voxtral (text → speech), the Telegram plugin (with a required debug patch), a Mac that stays on, a bot token from BotFather, a Bun runtime to host the plugin's MCP server, a LaunchAgent watchdog, a reply-enforcer hook, a coding-guidelines hook.

## Architecture

See `architecture.svg` (note: may lag slightly behind this guide; the hooks, LaunchAgent watchdog, and patched server were added later). High-level flow: your phone ↔ Telegram cloud ↔ a Bun MCP server on your Mac ↔ Claude Code ↔ (Whisper | Voxtral | local wiki | your memory file).

## Orientation (for the non-technical)

Two places you'll be typing commands:

- **Terminal** — the macOS app. Commands here look like `brew install …` and run at a prompt ending in `%` or `$`.
- **Claude REPL** — what you see *after* running `claude` in Terminal. Prompt changes to `>`. Commands starting with `/` (like `/plugin install …`) go here, not in the shell.

Conventions:

- `~/` means your home folder (`/Users/<your-mac-username>/`).
- `~/.claude/` is a hidden folder. In Finder, press `Cmd+Shift+.` to show hidden folders.
- `sudo` commands prompt for your Mac login password.
- `<angle brackets>` are placeholders — replace before pasting.

## Naming your assistant

Give it a proper name. Persona sticks better when there's a name behind it.

| Name | Rationale |
|------|-----------|
| **Aria** | Clean, musical, Italian. Short to say. Lead pick. |
| **Calliope** | Greek muse of music + eloquence. More gravity. |
| **Sonus** | Latin for "sound". Gender-neutral. Terse. |

Pick one or invent your own. **Caveat:** the bot `@handle` in Telegram (Part 4) must be ASCII-only and end in `bot`. Display name can be anything (accents, emoji, Greek letters). Plan a separate ASCII handle if your chosen name is non-ASCII.

---

## Prerequisites

Before you start:

- **Mac** on Apple Silicon (Mac Mini or MacBook). Apple Silicon matters for local voice models.
- **macOS** with admin rights.
- **Homebrew** installed: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`.
- **Personal Claude account, NOT team/enterprise.** Team accounts silently disable `--channels` — the bot will receive messages and show "typing…" but nothing reaches your agent session. Check at claude.ai → profile → plan. Switch to personal before Part 4.
- **Bun runtime.** The Telegram plugin's MCP server runs on Bun, not Node. Not flagged as a hard prereq by the plugin's official README, but it is one. `brew install oven-sh/bun/bun`.
- **`jq`** — used in Part 5 for safe JSON edits to `settings.json`.
- **~3 GB free disk** for the Voxtral model (4-bit quantized).
- **A phone number** registered on Telegram.
- **The matt-stack folder** at `~/matt-stack/` — clone from GitHub:

```bash
cd ~ && git clone https://github.com/hjbarraza/matt-yuno-agent.git ~/matt-stack
```

The repo is named `matt-yuno-agent` on GitHub; the target argument (`~/matt-stack`) renames it locally to match every path used in this guide.

Install everything Homebrew at once:

```bash
brew install anthropic/claude/claude-code openai-whisper ffmpeg jq oven-sh/bun/bun
```

Run `claude` once to OAuth (opens your browser).

## The stack — what you'll install

| Layer | Tool | Runs where |
|-------|------|-----------|
| Agent | Claude Code CLI | Terminal |
| Channel | Telegram MCP plugin (Bun/TS) | Spawned by Claude Code |
| STT | openai-whisper (Homebrew) | Local CPU/GPU |
| TTS | Voxtral-4B-TTS (MLX, via `mlx-audio`) | Local GPU |
| Knowledge | Plain markdown + git | `~/knowledge/` |
| Observability | Patched plugin + LaunchAgent watchdog | `launchctl`, every 5 min |
| Guardrails | Hooks (telegram-reply, coding-guidelines) | Claude Code harness |
| Keep-awake | `caffeinate` (wrapping `ct` alias) | Lifetime of session |

---

## Part 1 — Claude Code CLI

Already installed via brew in Prerequisites. First-time login:

```bash
claude
# follow the OAuth flow; state persists in ~/.claude/
```

Verify: `claude --version`. Run `claude`, type a message, `/exit` when satisfied.

What lives where (learn these paths — you'll touch them often):

```
~/.claude/
  CLAUDE.md               # global persona + rules (you write this)
  coding-guidelines.md    # coding rules the enforcer hook checks
  settings.json           # hooks, permissions, plugin enable list
  hooks/                  # your hook scripts (PreToolUse, Stop, etc.)
  skills/                 # your skill SKILL.md files (voice-reply, voice-filter, …)
  scripts/                # helper scripts (voxtral-tts, mcp-health-check, …)
  plugins/cache/          # MCP plugins live here after install
  projects/-Users/*/      # session transcripts (auto-generated) + memory/MEMORY.md
  channels/               # channel state (Telegram access list, bot.pid, server.log, …)
```

## Part 2 — Persona (`~/.claude/CLAUDE.md`)

The single most important file. It shapes every response.

```markdown
# Identity
You are **[Name]**, chief of staff to **[You]**.
Voice: [preset / accent].

# Hard rules (no exceptions)
- Candid, never cruel.
- Voice first, work second.
- No surprises — flag before acting on anything irreversible.
- "I don't know" is a complete answer.
- Act on small, reversible moves. Ask on big or irreversible ones.

# Voice
[How you want text to sound. Varied sentence rhythm. Words to use, words to never write.]

# Role priorities
1. Protect my time.
2. Drive accountability on commitments.
3. Thinking partner — pressure-test my ideas.
4. Comms — triage inbound, draft outbound in my voice.
```

Drop this in `~/.claude/CLAUDE.md`. It loads on every session automatically. Back it up before consequential rewrites (`cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak-$(date +%Y%m%d-%H%M)`).

### Auto-memory — worth knowing about

Claude Code also writes an **auto-memory** file at `~/.claude/projects/*/memory/MEMORY.md`. The agent reads it on session start and appends facts worth persisting across conversations (e.g. "User prefers terse replies", "Voice preset is `fr_female` and should be fed French only"). Useful to look at once a week to prune anything stale or wrong. You can also paste text in there manually — the agent will surface it as context in future sessions.

**Verify Part 2:** `ls -la ~/.claude/CLAUDE.md*` shows the file and any `.bak-*` copies.

## Part 3 — Voice layer

### Whisper (speech → text)

Installed via Homebrew. Models download lazily on first use.

```bash
whisper --help | head             # verify
whisper --model small some.ogg    # first run downloads the 'small' model
```

`tiny` for speed; `small` for accuracy (sweet spot); `medium` for maximum accuracy if you speak quickly.

### TTS (text → speech) — pick one

Two local options, both Apple-Silicon-accelerated, both Apache-2.0. Pick based on what matters more: **speed** or **personality**.

| Engine | Wall time (~10s of audio) | Model size | Best for |
|--------|--------------------------|-----------|----------|
| **Kokoro 82M** (recommended default) | ~3s | 82M params, ~175 MB weights | Daily driver. Replies feel snappy. 54 voices across 9 languages. Auto-detects the language of the text and picks an appropriate voice. |
| **Voxtral 4B** | ~30s | 4B params, ~2.5 GB 4-bit weights | A distinctive, more-designed voice. ~10x slower than Kokoro on the same Mac. Pick this if a specific "character" matters more than response latency. |

You can install both and flip between them per message — skills and hooks call the scripts by filename (`kokoro-tts.py` or `voxtral-tts.py`) and both share the same CLI contract.

---

#### Option A — Kokoro (recommended)

```bash
pip install mlx-audio           # system Python is fine; no venv required
```

Install the helper:

```bash
mkdir -p ~/.claude/scripts
cp ~/matt-stack/files/scripts/kokoro-tts.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/kokoro-tts.py
```

First run auto-downloads the Kokoro weights (~175 MB) and the spaCy English model (~50 MB).

**Auto-language switching.** If you call the script without `--voice`, it sniffs the text:

| Text looks like | Voice picked |
|---|---|
| English (or unknown) | `bf_emma` (British female) |
| Spanish (ñ / ¿ / ¡ / stopword probe) | `ef_dora` |
| French (é, è, œ, etc.) | `ff_siwis` |
| Italian | `if_sara` |
| Portuguese BR | `pf_dora` |

Override per-message with `--voice <preset>`. Full voice list after first run under `~/.cache/huggingface/hub/models--prince-canuma--Kokoro-82M/snapshots/*/voices/` — 54 presets covering English US/UK, Spanish, French, Italian, Portuguese BR, Japanese, Mandarin, Hindi.

**Verify Part 3 (Option A):**

```bash
~/.claude/scripts/kokoro-tts.py "Hi, this is your new assistant" --output /tmp/test.ogg
afplay /tmp/test.ogg
~/.claude/scripts/kokoro-tts.py "Hola, ¿cómo estás?" --output /tmp/hola.ogg   # auto-switches to ef_dora
afplay /tmp/hola.ogg
```

---

#### Option B — Voxtral (slower, more personality)

Voxtral-4B-TTS is Mistral's multilingual TTS, optimized for Apple Silicon via `mlx-audio`.

**Python 3.11 venv required** — the `voxtral-mlx` code inside `mlx-audio[tts]` is incompatible with Python 3.13+.

**Do not** try to install a package called `voxtral-mlx` — it does not exist on PyPI, despite older guides suggesting otherwise. The real package is `mlx-audio`; Voxtral TTS lives inside it.

```bash
python3.11 -m venv ~/voice-venv
source ~/voice-venv/bin/activate
pip install 'mlx-audio[tts]' huggingface_hub tiktoken
```

Download the weights (~2.5 GB, takes a minute or two):

```bash
python -c "from huggingface_hub import snapshot_download; \
  snapshot_download(repo_id='mlx-community/Voxtral-4B-TTS-2603-mlx-4bit')"
```

Install the TTS helper:

```bash
mkdir -p ~/.claude/scripts
cp ~/matt-stack/files/scripts/voxtral-tts.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/voxtral-tts.py
```

Open the file and update the shebang at the top to point at `~/voice-venv/bin/python3`, or always invoke the script with that Python explicitly.

##### Voice presets — the language rule

20 presets across 9 languages. Two categories:

| Preset group | Use for | Examples |
|---|---|---|
| Language-agnostic | English or mixed text | `neutral_female`, `casual_male`, `cheerful_female` |
| Language-prefixed | That language only | `fr_female`, `it_male`, `es_female`, `de_male`, `hi_female`, `pt_male`, `nl_female`, `ar_male` |

Feed English to `fr_female` and it sounds like a French person struggling to read English. Pick per your dominant language; override per-message with `--voice` when context calls for it.

**Verify Part 3 (Option B):**

```bash
~/.claude/scripts/voxtral-tts.py "<short phrase in chosen preset's language>" --output /tmp/test.ogg --voice <preset>
afplay /tmp/test.ogg
```

---

#### Running both side-by-side (optional)

Keep both in `~/.claude/scripts/`. The voice-reply skill (see `files/skills/voice-reply/SKILL.md`) calls whichever script you point it at. Easiest setup: Kokoro as daily driver, Voxtral explicitly called for marquee messages where personality is the point.

## Part 4 — Telegram channel

Six concrete steps. Skip none.

### 4.1 Create the bot

1. On Telegram, DM `@BotFather`.
2. Send `/newbot`.
3. Display name: can be anything — emoji, Greek letters, accents.
4. Username (`@handle`): **ASCII only**, must end in `bot`, globally unique. Example: `haeris_bot`.
5. Save the HTTP API token BotFather sends — looks like `123456789:AAHfiqksKZ8...`.
6. Optional polish: `/setdescription`, `/setuserpic`.

### 4.2 Install the plugin

```
claude
# inside the REPL:
/plugin install telegram@claude-plugins-official
/reload-plugins
```

### 4.3 Save the token

```
# inside the REPL:
/telegram:configure <paste-your-token>
```

Writes `~/.claude/channels/telegram/.env` with chmod 600.

### 4.4 Apply the observability patch — do NOT skip

The stock plugin swallows its own stderr. When things break (and they will), you get zero signal. This patch adds a log file + heartbeat.

```bash
cd ~/.claude/plugins/cache/claude-plugins-official/telegram/*/
patch -p1 < ~/matt-stack/files/patches/server.ts.patch
```

**Caveat**: plugin auto-updates overwrite the patch. Reapply after each update.

### 4.5 Launch with the channel flag

```bash
# inside the REPL:
/exit
# back in the shell:
claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official --continue
```

**Verify 4.5:**

```bash
tail ~/.claude/channels/telegram/server.log
# last line should read: boot: MCP StdioServerTransport connected — plugin is fully serving tools
```

If that line is missing, the server didn't start. Most common causes: Bun not installed, or you're on a team Claude account.

### 4.6 Pair + lock

1. DM `@<your-bot-handle>` any text.
2. The bot replies with a **6-character pairing code**.
3. In the REPL:
   ```
   /telegram:access pair <code>
   ```
4. **Immediately** lock the policy so strangers can't trigger new pairing codes:
   ```
   /telegram:access policy allowlist
   ```

### 4.7 Text round-trip test

Send the bot a plain-text message → it arrives in your REPL as a `<channel source="plugin:telegram:telegram" ...>` tag → the agent replies using the `reply` tool, back to your phone. Voice round-trip is deferred to Part 5 (after the voice-reply skill + hook are installed).

**Verify Part 4:** `cat ~/.claude/channels/telegram/access.json` — `dmPolicy: "allowlist"`, your numeric user ID in `allowFrom`.

### Plugin state directory

```
~/.claude/channels/telegram/
  .env              # TELEGRAM_BOT_TOKEN=…           (chmod 600)
  access.json       # who's allowed, dmPolicy, pairing state
  bot.pid           # current server process
  heartbeat.json    # liveness — written every 10s by the patched server
  server.log        # stderr capture — written by the patched server
  inbox/            # downloaded attachments from Telegram
  approved/         # pairing handoff markers
```

## Part 5 — Agent behavior (hooks, skills, watchdog)

This is where the agent stops feeling like a chatbot and starts feeling like an assistant with guardrails.

### 5.1 Voice-reply contract (skills + hook)

Two skills + one hook. The skills teach the behavior; the hook enforces it.

```bash
mkdir -p ~/.claude/hooks ~/.claude/skills/voice-reply ~/.claude/skills/voice-filter

# skills
cp ~/matt-stack/files/skills/voice-reply/SKILL.md ~/.claude/skills/voice-reply/
cp ~/matt-stack/files/skills/voice-filter/SKILL.md ~/.claude/skills/voice-filter/

# hook
cp ~/matt-stack/files/hooks/telegram-reply-enforcer.py ~/.claude/hooks/
sed -i '' "s/REPLACE_WITH_YOUR_CHAT_ID/<your-telegram-user-id>/" \
  ~/.claude/hooks/telegram-reply-enforcer.py
chmod +x ~/.claude/hooks/telegram-reply-enforcer.py
```

What each piece does:

- **`voice-reply` skill** — teaches "every Telegram reply carries BOTH readable text AND a Voxtral voice note in one message."
- **`voice-filter` skill** — strips AI tropes (hope this helps, let me know, etc.) from outbound text and voice scripts.
- **`telegram-reply-enforcer` hook** — blocks the session from stopping if the last user message came via Telegram but the reply didn't attach a `.ogg`.

(Your Telegram user ID is the numeric `chat_id` visible on inbound channel tags, or DM `@userinfobot` to get it.)

### 5.2 Coding-guidelines enforcer

Blocks source edits until the agent has read your rules file in the current session. Prevents hasty hallucinated code.

```bash
cp ~/matt-stack/files/coding-guidelines.md ~/.claude/coding-guidelines.md
cp ~/matt-stack/files/hooks/coding-guidelines-enforcer.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/coding-guidelines-enforcer.py
```

Edit `~/.claude/coding-guidelines.md` to fit your own taste — the defaults are a starter kit (think before coding, simplicity first, surgical changes, goal-driven execution).

### 5.3 Register both hooks in `settings.json`

**Do not hand-edit the JSON.** Use `jq` for an idempotent merge that preserves any existing hooks (like `clauditor`) and is safe to re-run.

```bash
TG_HOOK="$HOME/.claude/hooks/telegram-reply-enforcer.py"
CG_HOOK="$HOME/.claude/hooks/coding-guidelines-enforcer.py"

# create settings.json if missing
[ -f ~/.claude/settings.json ] || echo '{}' > ~/.claude/settings.json

jq --arg tg "$TG_HOOK" --arg cg "$CG_HOOK" '
  .hooks //= {}
  | .hooks.Stop //= [{"matcher":"","hooks":[]}]
  | .hooks.Stop[0].hooks //= []
  | (.hooks.Stop[0].hooks |= (map(select(.command != $tg)) + [{"type":"command","command":$tg}]))
  | .hooks.PreToolUse //= []
  | (.hooks.PreToolUse |= (map(select(.matcher != "Write|Edit|MultiEdit|NotebookEdit")) + [{"matcher":"Write|Edit|MultiEdit|NotebookEdit","hooks":[{"type":"command","command":$cg}]}]))
' ~/.claude/settings.json > ~/.claude/settings.json.new && mv ~/.claude/settings.json.new ~/.claude/settings.json
```

### 5.4 Health watchdog — `mcp-health-check` LaunchAgent

Polls every 5 minutes, distinguishes "bot process dead" from "bot process alive but stdio pipe broken" (using the heartbeat file from 4.4), and DMs you on state transitions via the raw Telegram Bot API (not via MCP — which is what it's monitoring).

```bash
cp ~/matt-stack/files/scripts/mcp-health-check.py ~/.claude/scripts/
sed -i '' "s/REPLACE_WITH_YOUR_CHAT_ID/<your-telegram-user-id>/" \
  ~/.claude/scripts/mcp-health-check.py
chmod +x ~/.claude/scripts/mcp-health-check.py

LABEL="com.<your-handle>.mcp-health"
sed -e "s|YOUR_USERNAME|$(whoami)|g" -e "s|com.yourdomain.mcp-health|$LABEL|g" \
  ~/matt-stack/files/launchagents/mcp-health.plist \
  > ~/Library/LaunchAgents/$LABEL.plist
launchctl load ~/Library/LaunchAgents/$LABEL.plist
launchctl list | grep mcp-health
```

After this, you learn about breakage from your phone within 5 minutes — not from staring at a dead terminal.

### 5.5 Reload + voice round-trip

Reload to pick up the new hooks:

```
/exit
```

Back in shell, relaunch with the channel flag (this becomes the `ct` alias in Part 6):

```bash
claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official --continue
```

**Voice round-trip test:** DM the bot a short question → the agent should reply with both text and a Voxtral voice `.ogg` in one `reply` call. If it forgets the voice, the `telegram-reply-enforcer` hook will block the turn stop and make it redo the reply.

**Verify Part 5:**

```bash
ls ~/.claude/hooks/ ~/.claude/skills/ ~/.claude/scripts/
launchctl list | grep mcp-health
jq '.hooks | keys' ~/.claude/settings.json
```

Four more optional skills live in `~/matt-stack/files/skills/` (boot, reflect, seven-rules, firewall-check). Install after a week of using the base stack — or never, your call. The base setup works without them.

## Part 6 — Shell aliases + keep-awake + remote access

### 6.1 Aliases

Claude Code takes flags that are tedious to retype. Add to `~/.zshrc`:

```bash
# Daily driver — permissions auto-approved
alias cc='claude --dangerously-skip-permissions'

# Channel mode — daily driver plus Telegram plugin, resume last session,
# wrapped in caffeinate so the Mac stays idle-awake for the session lifetime
alias ct='caffeinate -is claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official --continue'
```

Then `source ~/.zshrc` or open a new terminal.

- `cc` — everyday use. Fast. Standard sleep behavior.
- `ct` — "answer Telegram from my desk" mode. `caffeinate -is` keeps the Mac idle-awake so the bun plugin + MCP stay alive and Telegram long-poll doesn't drop. When you `/exit`, the assertion releases and the Mac sleeps normally.

`caffeinate -is` flag choices (deliberate):
- `-i` prevent idle sleep (the one that matters — keeps the plugin alive)
- `-s` prevent system sleep (reinforces `-i` on AC-powered laptops)
- *No* `-d` — we *want* the display to sleep normally
- *No* `-u` — we don't want to fake user activity

**Why caffeinate, not `pmset`:** caffeinate is process-scoped and sudo-free. When the Claude session dies, the Mac sleeps again — which is what you want, because when `ct` isn't running there's no bot listening anyway. `pmset` would leave the Mac permanently sleep-disabled.

**`--dangerously-skip-permissions` caveat**: the agent runs shell commands without asking. Fine on a trusted personal machine. Drop the flag if in doubt.

### 6.2 Keep-awake strategy (deployment targets)

| Target | Status | Notes |
|---|---|---|
| Mac Mini (desktop, AC) | ✅ Supported | Works out of the box with `ct`. |
| MacBook, clamshell mode | ✅ Supported | Lid closed + external display + keyboard/mouse + AC all connected at boot. macOS treats as desktop. |
| MacBook, lid open on AC | ✅ Supported | Standard case. |
| MacBook on battery | ❌ Not supported | Battery will drain in hours — not viable for a 24/7 bot. |

What this strategy gets you:
- Bot stays online as long as `ct` is running.
- Display sleeps normally (energy + screen protection).
- When you `/exit` or the session crashes, the Mac goes back to normal sleep behavior — no orphaned "why isn't my Mac sleeping" state.
- The `mcp-health` LaunchAgent keeps firing every 5 minutes during caffeinate-awake periods (its whole job is to monitor the bot *while* the session is alive).

### 6.3 Remote access to the Mac

You'll want to reach the Mac from elsewhere to debug, restart, tail logs:

1. **Chrome Remote Desktop** (recommended): install `chrome-remote-desktop` on the Mac, pair at `remotedesktop.google.com`, set a PIN. Works from any Chrome or the Google app on your phone. Good for live debugging with visual feedback.
2. **SSH**: `sudo systemsetup -setremotelogin on`, then `ssh user@mini.local`. Good for scripted ops and `tail -f`ing logs.

### 6.4 MCP disconnect — the recovery ritual

You will hit this. The Telegram MCP tools will silently go stale in an otherwise-healthy session. Symptoms: the agent can't reply to Telegram; the bot appears dead from your phone.

The reliable recovery:

1. `tail -20 ~/.claude/channels/telegram/server.log` — see the last boot line and any shutdown reason.
2. `/exit` inside the REPL.
3. `ct` to relaunch. `--continue` keeps conversation history; the bun server's orphan watchdog will self-terminate any stale process and a fresh one spawns.

**Do not rely on `/reload-plugins` for channel plugins** — it often leaves the bun server orphaned, still polling Telegram but writing notifications into a dead MCP stdio pipe. Full process replacement beats in-place reconnect.

**Verify Part 6:** `alias cc ct` in the shell lists both aliases.

## Part 7 — Knowledge wiki

Karpathy-style LLM-maintained wiki. Three layers:

- `raw/` — immutable primary sources (transcripts, articles, session dumps). Never edit after ingest.
- `wiki/` — curated derived notes, maintained by the agent. Entities, concepts, topics, sources.
- `~/knowledge/CLAUDE.md` — schema + workflows (copied from the matt-stack template).

Initialize:

```bash
mkdir -p ~/knowledge/{raw,wiki/entities,wiki/concepts,wiki/topics,wiki/sources}
cp ~/matt-stack/templates/knowledge-CLAUDE.md ~/knowledge/CLAUDE.md
cd ~/knowledge && git init -b main
```

The template defines the schema: YAML frontmatter rules, wikilink conventions, ingest/query/lint workflows. Open it before your first ingest — you'll refer back to it.

Every ingest produces:

- `raw/YYYY-MM-DD_<slug>/source.md` — immutable capture with paste-date and origin
- `wiki/sources/<slug>.md` — curated summary with TL;DR and `[[wikilinks]]` to related entities/concepts
- Updates (or new nodes) to `wiki/entities/…`, `wiki/concepts/…`, `wiki/topics/…`
- An append to `wiki/log.md`
- Conditional update to `wiki/index.md` if the ingest adds a top-level node
- A git commit: `ingest: <slug>`

**Query**: "what do I know about X?" — the agent reads `wiki/index.md`, follows `[[wikilinks]]`, dereferences `source:` back to `raw/` when verification matters. If the fact isn't in the wiki, the agent should say so rather than guess from training data.

**Seed ingest**: ingest this setup session itself as the first source to prove the workflow works. Commit messages: `wiki: initial scaffold`, then `ingest: matt-stack-setup`.

### Make the wiki discoverable from every session

By default, `~/knowledge/CLAUDE.md` only auto-loads when you run `claude` from inside `~/knowledge/`. From any other directory the agent has no idea the wiki exists. Two small changes fix that:

1. **Global persona** — add a `# Knowledge wiki` section to `~/.claude/CLAUDE.md` that tells the agent: consult `~/knowledge/` before claiming facts from training data; follow the ingest workflow in `~/knowledge/CLAUDE.md` when durable new sources appear; the wiki is long-term durable knowledge, auto-memory is short-term session-persistent.
2. **Auto-memory reference** — write `~/.claude/projects/<current-session-slug>/memory/reference_wiki.md` (YAML frontmatter `type: reference`, short body naming the wiki and when to use it) and append one line to the adjacent `MEMORY.md` pointing at it. `MEMORY.md` is always in the agent's session-start context, so the wiki becomes discoverable everywhere.

**Verify Part 7:**

```bash
cd ~/knowledge && git log --oneline && find . -type f -name "*.md"
grep -c "Knowledge wiki" ~/.claude/CLAUDE.md          # >= 1
ls ~/.claude/projects/*/memory/reference_wiki.md      # file exists
```

## Part 8 — Gotchas (learned the hard way, ordered by pain)

1. **Team/enterprise Claude accounts silently disable `--channels`.** Bot receives your DM, shows "typing…", and the agent never sees it. Personal account required. Check first.
2. **`voxtral-mlx` does not exist on PyPI.** The real package is `mlx-audio[tts]`. The real API is `from mlx_audio.tts.utils import load; model = load("mlx-community/Voxtral-4B-TTS-2603-mlx-4bit")`.
3. **Bun must be installed before the Telegram plugin spawns its MCP server.** The plugin's official README doesn't flag this as a hard prerequisite, but it is. `brew install oven-sh/bun/bun`.
4. **BotFather `@handle` usernames are ASCII-only.** Display names can be Unicode. Plan separately if your chosen assistant name isn't ASCII.
5. **Language-prefixed Voxtral voices (`fr_*`, `it_*`, ...) need matching-language text.** Use `neutral_*` / `casual_*` for English.
6. **`/reload-plugins` does not reliably restart channel plugins.** Full `/exit` + relaunch does. Trust the full restart.
7. **The `server.ts` patch is required, not optional.** Without it the plugin's stderr is swallowed and any silent failure becomes guesswork.
8. **Voice scripts under ~500 chars.** Voxtral's max frames ≈ 60 seconds of speech. Longer and it truncates.
9. **Don't read markdown aloud.** Strip `**bold**`, `- bullets`, code fences before sending to TTS — they get read literally.
10. **Telegram rejects empty-text replies.** When attaching a voice note, the `text` field must still be non-empty.
11. **Back up `~/.claude/CLAUDE.md` before editing.** Not in git. `cp` it to a `.bak-YYYY-MM-DD-HHMM`.
12. **The bot token is a credential.** `chmod 600 ~/.claude/channels/telegram/.env`. If the token ever leaks (into a transcript, log, paste buffer), rotate via `@BotFather` → `/revoke`.
13. **macOS darkwake ≠ sleep.** Background processes can be throttled overnight. If you see intermittent failures between 2–6 AM, `pmset -g log` is the first place to look.
14. **Auto-memory is real.** `~/.claude/projects/*/memory/MEMORY.md` is read on every session start. Look at it once a week and prune anything wrong or stale.

## Setup verification checklist

**Mandatory final step.** Run this checklist after Parts 1–7 are done. The install is NOT complete until every automated check passes AND the two manual round-trip tests (text + voice) come back clean.

If you used `SETUP-PROMPT.md`, the guiding agent is instructed to run every item here and refuse to declare the setup done until everything passes. If you followed this long-form guide by hand, run it yourself — no exceptions.

Also useful as a regression check after plugin updates or OS upgrades.

### Part 1–2: Identity + Persona

- [ ] `test -f ~/.claude/CLAUDE.md && grep -qE "Identity|Hard rules" ~/.claude/CLAUDE.md` *(file exists with core sections)*
- [ ] `grep -q "Knowledge wiki" ~/.claude/CLAUDE.md` *(wiki section present — added in Part 7)*

### Part 3: Voice

- [ ] `whisper --help >/dev/null 2>&1` *(Whisper on PATH)*
- [ ] `~/voice-venv/bin/python -c "from mlx_audio.tts.utils import load" 2>&1` *(no error — mlx-audio[tts] installed)*
- [ ] `ls ~/.cache/huggingface/hub/ | grep -q Voxtral` *(weights downloaded)*
- [ ] `~/.claude/scripts/voxtral-tts.py "uno due tre" --output /tmp/verify.ogg --voice it_female && afplay /tmp/verify.ogg` *(audible speech matches voice preset language)*

### Part 4: Telegram channel

- [ ] `bun --version >/dev/null 2>&1` *(Bun installed — plugin prereq)*
- [ ] `test -f ~/.claude/channels/telegram/.env && grep -q "^TELEGRAM_BOT_TOKEN=" ~/.claude/channels/telegram/.env` *(token saved)*
- [ ] `jq -e '.dmPolicy == "allowlist" and (.allowFrom | length > 0)' ~/.claude/channels/telegram/access.json` *(policy locked, at least one allowed ID)*
- [ ] With `ct` running: `tail -20 ~/.claude/channels/telegram/server.log | grep -q "StdioServerTransport connected"` *(MCP server up and patched version running)*
- [ ] **Manual**: DM your bot "ping". Receive a text reply within a few seconds.

### Part 5: Agent behavior

- [ ] `test -x ~/.claude/hooks/telegram-reply-enforcer.py && test -x ~/.claude/hooks/coding-guidelines-enforcer.py` *(both hooks executable)*
- [ ] `test -f ~/.claude/skills/voice-reply/SKILL.md && test -f ~/.claude/skills/voice-filter/SKILL.md` *(both skills in place)*
- [ ] `jq -e '(.hooks.Stop | length > 0) and (.hooks.PreToolUse | length > 0)' ~/.claude/settings.json` *(both hooks registered)*
- [ ] `launchctl list | grep -q mcp-health` *(LaunchAgent loaded)*
- [ ] **Manual**: DM the bot "tell me a short joke". Receive BOTH a text reply AND a `.ogg` voice note in Telegram.

### Part 6: Aliases + keep-awake

- [ ] `zsh -ic 'alias cc ct' | grep -q caffeinate` *(ct alias includes caffeinate)*
- [ ] With `ct` running: `pmset -g assertions | grep -q PreventUserIdleSystemSleep` *(caffeinate holding idle-awake)*

### Part 7: Wiki

- [ ] `test -f ~/knowledge/CLAUDE.md` *(schema present)*
- [ ] `[ $(git -C ~/knowledge log --oneline | wc -l) -ge 2 ]` *(scaffold + at least one ingest)*
- [ ] `find ~/knowledge/wiki -type f -name "*.md" | head -1` *(at least one wiki node exists)*
- [ ] `grep -q "reference_wiki" ~/.claude/projects/*/memory/MEMORY.md` *(wiki discoverable from all sessions)*

If every box checks, the stack is live. If anything fails, jump to the Part responsible before moving on.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Bot shows "typing…" but session never sees messages | Team/enterprise Claude account | Switch to personal account at claude.ai → profile → plan |
| `server.log` missing or empty after launch with `--channels` | Bun not installed OR patch not applied | `brew install oven-sh/bun/bun`, reapply `server.ts.patch` |
| Telegram tools disappear mid-session | Orphaned bun MCP server | `/exit` + `ct` (do NOT rely on `/reload-plugins`) |
| Voice sounds distorted / wrong language | Preset-language mismatch | Use `neutral_*` for English or match text language to `fr_*`/`it_*`/etc. |
| `voxtral-mlx` install fails | That package doesn't exist | Install `mlx-audio[tts]` instead |
| Bot handle rejected by BotFather | Non-ASCII or missing `bot` suffix | Use ASCII only, end in `bot` |
| `/telegram:access pair` fails with "code expired" | Pairing codes expire in ~5 min | DM the bot again for a fresh code |
| LaunchAgent doesn't fire | Plist label doesn't match filename | Rename plist to match its `Label` element |

## Where to customize

- **Voice**: swap `--voice <preset>` for any of the 20 presets. Record your own for voice cloning (Voxtral supports it).
- **Extra MCPs**: filesystem, browser automation, any API. See `claude.com/code/docs/mcp`.
- **Skills**: `~/.claude/skills/` is your extension point. Each is a markdown file with YAML frontmatter and a `description` line the agent reads to decide when to invoke.
- **Memory**: `~/.claude/projects/*/memory/MEMORY.md` — the agent reads on session start. Paste things you want it to remember between sessions.
- **Hooks**: `~/.claude/hooks/` — add more enforcers (PreCompact, SessionStart, etc.) as you find behaviors worth locking in.

---

## Fastest path: paste-and-go

If you just want to be running by the end of the afternoon, use [`SETUP-PROMPT.md`](./SETUP-PROMPT.md). One paste into a fresh `claude` session, and the agent walks you through Parts 1–7 interactively, running commands with your permission and checking each step.

Use this guide (the longer manual) when you want to understand *why* something is set up a particular way, or to debug a specific failure.

## Minimum viable setup (if you want to talk to it today, polish later)

1. `brew install claude-code openai-whisper oven-sh/bun/bun jq`.
2. `claude` → `/plugin install telegram@claude-plugins-official` → `/reload-plugins`.
3. BotFather → new bot → `/telegram:configure <token>`.
4. Relaunch with `--channels plugin:telegram@claude-plugins-official`. DM bot, pair, lock to allowlist.
5. Write a 20-line `~/.claude/CLAUDE.md` with your name, persona, 3 hard rules.
6. Skip Voxtral on day 1 — text replies are still useful. Add voice in week 2.
7. Skip the wiki on day 1 — start notes manually. Graduate to the Karpathy schema once you've used it a week.

Enough to be talking to a named agent over Telegram in an afternoon. Everything else is polish.

---

## Credits

Stack originally assembled by H (hjbarraza / hjyuno) for Yuno/Path MBA operations. This guide is the "how do I do it too" version — bring your own persona, tokens, wiki. If something breaks, `~/.claude/channels/telegram/server.log` and `pmset -g log` are the two most useful places to look.
