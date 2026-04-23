# Paste-and-go setup prompt

> Matt: paste the block below into a fresh `claude` session. Claude will run the setup interactively — ask you questions, run commands with your permission, and check each step worked before moving on. Total time: **60–90 min** depending on how chatty you get.

---

## Orientation (for the non-technical)

You'll be reading and copying commands into two places:

- **Terminal** — the macOS app at `Applications → Utilities → Terminal`. Commands run here look like `brew install …`. The text you see before the cursor (e.g. `h@mini ~ %`) is the **shell** prompt.
- **Claude REPL** — what you see *after* you run `claude` in Terminal. You'll know you're there when the prompt changes to a `>`. Commands starting with `/` (like `/plugin install …` or `/telegram:configure …`) go **here, not in the shell**.

Some conventions:

- `~/` means your home folder (`/Users/<your-mac-username>/`).
- `~/.claude/` is a hidden folder. In Finder, press `Cmd+Shift+.` to show hidden folders.
- Commands with `sudo` will prompt for your Mac login password.
- **Angle brackets like `<my-handle>` are placeholders** — replace them with your real values before pasting.

---

## Prerequisites (do this before pasting the prompt)

**1. Get the matt-stack files.** You need this folder at `~/matt-stack/` before the guided install can reference it:

```bash
cd ~
git clone https://github.com/hjbarraza/matt-yuno-agent.git ~/matt-stack
```

The repo is named `matt-yuno-agent` on GitHub; the target argument (`~/matt-stack`) renames it locally to match every path used in this guide. If you received the folder another way — zip, USB, AirDrop — place it at `~/matt-stack/` and skip the clone.

**2. Personal Claude account, NOT team/enterprise.** Team and enterprise plans disable `--channels` / remote-control server-side. The Telegram bot will *receive* messages and show a "typing…" indicator, but the MCP server's notifications never reach your CLI session. It looks like the plugin is broken; it isn't — the account plan is blocking it. Sign out and in with a personal account before Part 4, or skip Parts 4–5 entirely. Check at claude.ai → profile → plan.

**3. Homebrew packages:**

```bash
brew install anthropic/claude/claude-code   # if not already
brew install openai-whisper ffmpeg jq
brew install oven-sh/bun/bun                # required by the Telegram plugin's MCP server
```

Bun is not flagged as a hard prereq by the official Telegram plugin README, but the plugin's MCP server (`server.ts`) runs on Bun — without it the server fails to spawn and Claude silently swallows the error. `jq` is needed for safe JSON edits to `settings.json` in Part 5.

**4. Claude Code OAuth.** Run `claude` once — it opens your browser for OAuth on first launch.

**5. Keep-awake strategy.** You want the Mac idle-awake (so the bot stays online) but the display free to sleep (energy + screen life). The `ct` alias installed in Part 6 wraps Claude Code in `caffeinate -is`, which holds the Mac idle-awake for the lifetime of the session and releases when you `/exit`. No system-wide `pmset` changes needed.

Deployment targets:
- **Mac Mini** (desktop, AC): works out of the box.
- **MacBook in clamshell mode** (lid closed, external display + keyboard/mouse + AC, all connected at boot): supported.
- **MacBook with lid open on AC**: supported.
- **MacBook on battery**: not a supported deployment for a 24/7 bot. The battery will drain.

## How to use

1. Open Terminal.
2. Complete the Prerequisites above.
3. **`cd ~`** — launch Claude Code from your home folder. The install writes to `~/.claude/`, `~/knowledge/`, and `~/Library/LaunchAgents/`; starting from `~` keeps every relative reference working and avoids Claude scoping its session to a nested project directory.
4. Run `claude` and wait for the `>` prompt.
5. Paste the prompt below **in one shot** (include the triple-backtick fence or not — both work).
6. Follow along. Claude will ask for your assistant's name, then drive the install through seven parts.

---

## The prompt

Copy everything between the `>>>` markers. Before pasting, **replace the placeholders in the "My context" block** with your own details.

>>>

You are guiding me through setting up a personal AI chief-of-staff stack on my Mac. This is adapted from H's setup. Be my hands: read files, run shell commands (ask permission first), verify each step, and wait for me between milestones.

My context:
- Mac on Apple Silicon (Mac Mini or MacBook — ask me which if it matters for a given step)
- Homebrew installed, with `claude-code`, `openai-whisper`, `ffmpeg`, `jq`, and `bun` already installed (per the guide's Prerequisites)
- `~/matt-stack/` folder exists with all templates, hooks, skills, scripts, patches
- Personal Claude account (NOT team or enterprise — those disable `--channels`)
- Fresh Claude Code install
- I am Matt (Matteo Turzo) — I build audio plug-ins, ex-Lyft, Italian
- My dogs are Gemma and Juno (for reference if I mention them)

The stack has seven parts. Build them in order and stop at a checkpoint between each. After every part, summarize what exists now in 2 lines and wait for me to say "next". Each part ends with a concrete verify command — run it, show me the output, don't proceed on silent failure.

**Part 1 — Naming the assistant.** Before anything else, ask me which name I want for my AI. Offer these three with a one-line rationale each, then wait for my reply:
- Aria (Italian, musical, short; the lead pick)
- Calliope (Greek muse of music; more gravity)
- Sonus (Latin for "sound"; minimal)

Accept any other name I propose. Note: BotFather requires an ASCII-only `@handle` in Part 4; if my chosen name is Unicode (e.g. `λris`), plan on a separate ASCII handle for the bot.

**Verify Part 1:** repeat my chosen name back to me and ask for confirmation.

**Part 2 — Persona file.** Create `~/.claude/CLAUDE.md` with:
- Identity section (my chosen name, "chief of staff to Matt", Italian-accented voice)
- 5 hard rules (candid not cruel; voice first work second; no surprises; "I don't know" is a complete answer; act on small reversible moves, ask on big or irreversible)
- Voice guidance (sentence rhythm varied, no AI tropes, bold for real emphasis only)
- Role priorities (protect time → drive accountability → thinking partner → comms)
- A "never write these" list (hope this helps, feel free to, please let me know, great question, let's dive in, here's a breakdown, in summary, to conclude)

Back up any existing `~/.claude/CLAUDE.md` to `~/.claude/CLAUDE.md.bak-<timestamp>` before writing. After writing, `cat` the file and ask me to approve or tweak it.

**Verify Part 2:** `ls -la ~/.claude/CLAUDE.md*` shows the new file and (if applicable) a `.bak-*` copy.

**Part 3 — Voice layer.**

a) Verify Whisper:
```
whisper --help | head
```

b) Ask me which TTS engine I want and present the tradeoff:

> You've got two options, both local, both Apple-Silicon accelerated, both Apache 2.0.
>
> **Kokoro 82M** — fast. ~3 seconds of wall time per 10 seconds of audio. 54 voices across 9 languages. Auto-detects the language in the text and picks a matching voice. Recommended default — replies feel snappy.
>
> **Voxtral 4B** — slow. ~30 seconds of wall time per 10 seconds of audio. Larger model (4B params vs 82M), more characterful prosody and a more "designed" feel. Worth it if you want a distinctive voice, but every reply will take noticeably longer.
>
> Which one do you want as your default? You can install both and swap later.

Wait for my pick. Default to Kokoro if I say "whatever is best."

c) Install the chosen one.

**If Kokoro:**
```
pip install mlx-audio
mkdir -p ~/.claude/scripts
cp ~/matt-stack/files/scripts/kokoro-tts.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/kokoro-tts.py
```
First run of `kokoro-tts.py` auto-downloads the model (~175 MB) + spaCy English (~50 MB).

**If Voxtral (Python 3.11 venv required — voxtral-mlx is incompatible with Python 3.13+):**
```
python3.11 -m venv ~/voice-venv
source ~/voice-venv/bin/activate
pip install 'mlx-audio[tts]' huggingface_hub tiktoken
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='mlx-community/Voxtral-4B-TTS-2603-mlx-4bit')"
mkdir -p ~/.claude/scripts
cp ~/matt-stack/files/scripts/voxtral-tts.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/voxtral-tts.py
```
Update the shebang at the top of the copied `voxtral-tts.py` to `#!~/voice-venv/bin/python3` (or always invoke the script with that Python explicitly).

**Do not** install a package called `voxtral-mlx` — it does not exist on PyPI. Voxtral TTS lives inside `mlx-audio`.

d) **Voice preset rule.**

**If Kokoro:** in the common case the script auto-detects the language of the text and picks an appropriate default voice (`bf_emma` for English, `ef_dora` for Spanish, `ff_siwis` for French, etc.). Override per-message with `--voice <preset>`. 54 presets available; full list under `~/.cache/huggingface/hub/models--prince-canuma--Kokoro-82M/snapshots/*/voices/` after first run.

**If Voxtral:** 20 voice presets split into two categories:

| Preset group | Use for | Examples |
|---|---|---|
| Language-agnostic | English or mixed text | `neutral_female`, `casual_male`, `cheerful_female` |
| Language-prefixed | Text in that specific language only | `fr_female`, `it_male`, `es_female`, `de_male`, `hi_female`, `pt_male`, `nl_female`, `ar_male` |

Feeding English to `fr_female` sounds wrong. Ask me what language I'll mostly use, pick a preset, tell me which.

**Verify Part 3:** generate a short phrase and play it:
```
# Kokoro:
~/.claude/scripts/kokoro-tts.py "Hi, this is your new assistant" --output /tmp/test.ogg
afplay /tmp/test.ogg
# Voxtral:
~/.claude/scripts/voxtral-tts.py "<phrase in preset's language>" --output /tmp/test.ogg --voice <preset>
afplay /tmp/test.ogg
```
Ask me if the voice sounds right before continuing.

**Part 4 — Telegram channel.**

0) Confirm I'm on a personal Claude account. Ask me: "Are you signed in at claude.ai with a personal account, or a team/enterprise account?" If team/enterprise, stop and tell me to switch — the channel feature will not work otherwise, and the failure mode is silent (bot receives messages, shows typing, but the session never sees them).

a) Walk me through creating the bot on Telegram:
- DM `@BotFather` and send `/newbot`
- When asked for a display name: can be anything — emoji, Greek letters, accents all fine
- When asked for a username (the `@handle`): **must be ASCII**, must end in `bot`, globally unique (e.g. `haeris_bot`, `matteo_ai_bot`)
- Copy the HTTP API token BotFather sends. Looks like `123456789:AAHfiqksKZ8...`
- Paste the token to me when you have it
- Optional: set description and picture with `/setdescription`, `/setuserpic`

b) Install the plugin and reload (in the Claude REPL, not the shell):
```
/plugin install telegram@claude-plugins-official
/reload-plugins
```

c) Save the token via the configure skill:
```
/telegram:configure <token>
```
Writes `~/.claude/channels/telegram/.env` with chmod 600.

d) **Apply the matt-stack debug patch before first launch.** Without this, the MCP server's stderr is swallowed and any failure is invisible.
```bash
cd ~/.claude/plugins/cache/claude-plugins-official/telegram/*/
patch -p1 < ~/matt-stack/files/patches/server.ts.patch
```

e) Exit the REPL and relaunch with the channel flag:
```sh
/exit
claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official --continue
```

**Verify Part 4e:** `tail ~/.claude/channels/telegram/server.log` should end with `boot: MCP StdioServerTransport connected — plugin is fully serving tools`. If that line is missing, the server didn't start. Most likely causes: Bun not installed, or a team Claude account.

f) Pair. DM your bot `@<handle>` any text on Telegram. The bot replies with a 6-character pairing code. In the REPL:
```
/telegram:access pair <code>
```

g) **Lock the policy immediately.** The default `dmPolicy: pairing` means any stranger who finds the bot can trigger pairing codes. Run:
```
/telegram:access policy allowlist
```
From here on, only allowlisted IDs reach the session.

h) **Text round-trip test.** I DM the bot any plain-text message → it should arrive in the session as a `<channel source="plugin:telegram:telegram" ...>` tag → you reply with the `reply` tool using my `chat_id`. I should see your text reply in Telegram within seconds.

(Voice round-trip comes *after* Part 5 — we need the voice-reply skill + hook installed first.)

**Verify Part 4:** `cat ~/.claude/channels/telegram/access.json` shows `dmPolicy: "allowlist"` and my user ID in `allowFrom`.

**Part 5 — Agent behavior (hooks, skills, watchdog).**

This turns the agent from a chatbot into an operator-facing assistant with guardrails.

a) Install the voice-reply contract:
```bash
mkdir -p ~/.claude/hooks ~/.claude/skills/voice-reply ~/.claude/skills/voice-filter
cp ~/matt-stack/files/hooks/telegram-reply-enforcer.py ~/.claude/hooks/
sed -i '' "s/REPLACE_WITH_YOUR_CHAT_ID/<my-telegram-user-id>/" ~/.claude/hooks/telegram-reply-enforcer.py
chmod +x ~/.claude/hooks/telegram-reply-enforcer.py
cp ~/matt-stack/files/skills/voice-reply/SKILL.md ~/.claude/skills/voice-reply/
cp ~/matt-stack/files/skills/voice-filter/SKILL.md ~/.claude/skills/voice-filter/
```

b) Install the coding-guidelines enforcer:
```bash
cp ~/matt-stack/files/coding-guidelines.md ~/.claude/coding-guidelines.md
cp ~/matt-stack/files/hooks/coding-guidelines-enforcer.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/coding-guidelines-enforcer.py
```

c) **Register both hooks in `~/.claude/settings.json` using `jq`** (safer than hand-editing JSON):
```bash
# Install location used by the hooks — expand ~ to absolute path
TG_HOOK="$HOME/.claude/hooks/telegram-reply-enforcer.py"
CG_HOOK="$HOME/.claude/hooks/coding-guidelines-enforcer.py"

# Create settings.json if missing
[ -f ~/.claude/settings.json ] || echo '{}' > ~/.claude/settings.json

# Merge in both hooks idempotently
jq --arg tg "$TG_HOOK" --arg cg "$CG_HOOK" '
  .hooks //= {}
  | .hooks.Stop //= [{"matcher":"","hooks":[]}]
  | .hooks.Stop[0].hooks //= []
  | (.hooks.Stop[0].hooks |= (map(select(.command != $tg)) + [{"type":"command","command":$tg}]))
  | .hooks.PreToolUse //= []
  | (.hooks.PreToolUse |= (map(select(.matcher != "Write|Edit|MultiEdit|NotebookEdit")) + [{"matcher":"Write|Edit|MultiEdit|NotebookEdit","hooks":[{"type":"command","command":$cg}]}]))
' ~/.claude/settings.json > ~/.claude/settings.json.new && mv ~/.claude/settings.json.new ~/.claude/settings.json
```

This idempotently adds the telegram-reply hook to the `Stop` array and the coding-guidelines hook to `PreToolUse`, preserving any existing hooks (like `clauditor`). Safe to re-run.

d) Install the MCP health watchdog:
```bash
cp ~/matt-stack/files/scripts/mcp-health-check.py ~/.claude/scripts/
sed -i '' "s/REPLACE_WITH_YOUR_CHAT_ID/<my-telegram-user-id>/" ~/.claude/scripts/mcp-health-check.py
chmod +x ~/.claude/scripts/mcp-health-check.py

LABEL="com.<my-handle>.mcp-health"
sed -e "s|YOUR_USERNAME|$(whoami)|g" -e "s|com.yourdomain.mcp-health|$LABEL|g" \
  ~/matt-stack/files/launchagents/mcp-health.plist > ~/Library/LaunchAgents/$LABEL.plist
launchctl load ~/Library/LaunchAgents/$LABEL.plist
```

e) **Reload Claude to pick up new hooks:**
```
/exit
claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official --continue
```

f) **Voice round-trip test.** I DM the bot a short question → you should reply with **both** text and a Voxtral voice `.ogg` in a single `reply` call. If you forget the voice, the new `telegram-reply-enforcer` hook will block your turn stop and make you redo it.

**Verify Part 5:**
```bash
ls ~/.claude/hooks/ ~/.claude/skills/ ~/.claude/scripts/
launchctl list | grep mcp-health
jq '.hooks | keys' ~/.claude/settings.json   # should show Stop, PreToolUse among others
```

**Part 6 — Shell aliases + remote access.**

a) Append to `~/.zshrc` (check if they already exist first, don't duplicate):
```
alias cc='claude --dangerously-skip-permissions'
alias ct='caffeinate -is claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official --continue'
```
Then `source ~/.zshrc`.

- `cc` — daily driver, standard sleep behavior.
- `ct` — launch-with-Telegram-and-resume, wrapped in `caffeinate -is` so the Mac stays idle-awake for as long as the session is alive. When you `/exit`, caffeinate releases and the Mac sleeps normally.
- Warn me: `--dangerously-skip-permissions` means the agent runs shell commands without asking. Only use on a trusted machine.

b) Remind me to set up Chrome Remote Desktop for phone-based debugging: install the `chrome-remote-desktop` host, pair at `remotedesktop.google.com`, set a PIN. Don't run the install — just tell me the URL and why.

c) MCP-disconnect recovery ritual. If the Telegram tools silently stop working:
- First: `tail -20 ~/.claude/channels/telegram/server.log` for the last boot line and any errors.
- `/reload-plugins` does NOT reliably fix channel plugins (bun server can end up orphaned, still polling Telegram but writing notifications into a dead MCP stdio pipe).
- Reliable fix: `/exit` then `ct` (full process replacement).

**Verify Part 6:** `alias cc ct` in the shell lists both aliases.

**Part 7 — Knowledge wiki.**

Initialize the Karpathy-style wiki:
```bash
mkdir -p ~/knowledge/{raw,wiki/entities,wiki/concepts,wiki/topics,wiki/sources}
cp ~/matt-stack/templates/knowledge-CLAUDE.md ~/knowledge/CLAUDE.md
cd ~/knowledge && git init -b main
```

The template at `~/matt-stack/templates/knowledge-CLAUDE.md` defines the schema: three layers (raw/ immutable, wiki/ LLM-maintained, CLAUDE.md schema), Obsidian-style wikilinks, YAML frontmatter rules, ingest + query + lint workflows. Read it so you understand what goes where.

Seed the two always-present files:
- `wiki/index.md` — top-level entrypoint with sections for People / Sources / Topics
- `wiki/log.md` — append-only changelog of ingests

Both need YAML frontmatter per the schema. Create an entity stub for me at `wiki/entities/matt.md` (basic handles + preferences). Commit with `wiki: initial scaffold`.

Ingest this setup session as the first source to prove the workflow works:
- `raw/<today>_matt-stack-setup/source.md` with a paste-date, origin (this REPL session), a section covering what happened in each of Parts 1–7
- `wiki/sources/matt-stack-setup.md` — curated summary with TL;DR and cross-links to `[[entities/matt]]`
- Update `wiki/index.md` and `wiki/log.md`
- Commit with `ingest: matt-stack-setup`

**Make the wiki discoverable from every session** (without this, only sessions launched from `~/knowledge/` will see the schema):

- Add a `# Knowledge wiki` section to `~/.claude/CLAUDE.md` (between "Never write these" and "working preferences") that says: consult `~/knowledge/` before claiming facts from training data; follow the ingest workflow when durable new sources appear; the wiki is long-term durable knowledge, auto-memory is short-term session-persistent preferences.
- Write `~/.claude/projects/<current-session-slug>/memory/reference_wiki.md` — a memory file with YAML frontmatter `type: reference` and a body naming the wiki, its location, its structure, and when to use it.
- Append one line to `~/.claude/projects/<current-session-slug>/memory/MEMORY.md` pointing at the new reference file.

(You know your current session's slug from your own environment — it's the slugified cwd, e.g. `-Users-matt`.)

**Verify Part 7:**
```bash
cd ~/knowledge && git log --oneline && find . -type f -name "*.md" | head -10
grep -c "Knowledge wiki" ~/.claude/CLAUDE.md          # >= 1
ls ~/.claude/projects/*/memory/reference_wiki.md      # file exists
```

**Part 8 — Verification (MANDATORY final step — do not skip).**

Open `~/matt-stack/SETUP-PROMPT.md` and run every single command in the "Setup verification checklist" section (at the bottom of that file). For each check:

1. Run the command.
2. Report pass or fail with the actual output.
3. If it fails, jump back to the Part responsible, fix the cause, re-run.

You are NOT done with the install until all 20 automated checks pass AND both manual round-trip tests (Part 4 text DM, Part 5 voice DM) have been confirmed by me. Do not move to Part 9, do not say "setup complete," do not cheer. Run the full list, show me the output, wait for my "looks good" before you call it finished.

**Part 9 — Gotchas I should know (tell me these at the end, not earlier).**

Read these aloud to me (literally, in text) as the final checkpoint:

- **Team/enterprise Claude accounts silently drop `--channels` notifications.** If Telegram ever stops working after an account switch, check your plan first.
- MCP plugins are stdio-bound to the CLI session. If tools "disappear", `/exit` + relaunch with `--channels --continue` is more reliable than `/reload-plugins` for channel plugins.
- The debug-log patch at `~/matt-stack/files/patches/server.ts.patch` is not optional. Plugin updates will overwrite it — reapply after each update.
- BotFather `@handle` usernames are ASCII-only. Display names can be anything.
- Voxtral voice presets: language-prefixed voices (`fr_*`, `it_*`, etc.) need matching-language text.
- Voxtral max ≈ 60s of speech — keep voice scripts under 500 chars.
- Voice ≠ markdown. Strip `**bold**`, `- bullets`, code fences before sending to TTS or they get read literally.
- `chmod 600 ~/.claude/channels/telegram/.env` — the bot token is a credential. If it ever appears in a transcript, rotate via `@BotFather` → `/revoke`.
- `~/.claude/CLAUDE.md` is not in git — `cp` it to a `.bak-<date>` before big edits.
- macOS darkwake ≠ sleep. Background processes can be throttled overnight — if you see intermittent failures between 2–6 AM, `pmset -g log` is the first place to look.
- **Auto-memory** lives at `~/.claude/projects/*/memory/MEMORY.md`. The agent reads on session start and writes facts worth persisting. Worth a look once a week to prune.

**Rules for you (the guiding agent) during this setup:**

- Ask before running shell commands. Use `Bash`, show me the command first, explain why.
- Verify each step using the verify command at the bottom of each Part. Don't proceed on silent failure.
- Keep replies short. Fragment sentences when it's faster. No "Great! Now let's..." filler.
- If I say "skip" for a part, move to the next with a note about what I missed.
- If something breaks, don't try 3 workarounds — tell me the actual error and ask.
- After every part, summarize what exists now in 2 lines and wait for "next".
- **Part 8 is mandatory.** Do NOT declare the setup complete until every item in the verification checklist passes and I've confirmed the two manual round-trip tests.

Let's start with **Part 1** — ask me which name I want.

<<<

---

## Troubleshooting the paste

If Claude Code chokes on the paste (rare — usually because the REPL treats the `>>>` / `<<<` markers as something they're not), strip those markers. The content between them is the full instruction.

If your session times out mid-setup, restart with `claude` and say: *"continue my stack setup from Part N"* — the agent will read the existing files and pick up where it left off.

**If mid-setup Telegram goes silent** (bot shows "typing…" but nothing reaches your session): you're probably on a team/enterprise Claude account. The failure is at the account-plan layer, not in anything you installed. Sign out and in with a personal account at claude.ai.

## What you'll have at the end

Files:
- `~/.claude/CLAUDE.md` — persona with your chosen name
- `~/.claude/coding-guidelines.md` — your starter ruleset
- `~/.claude/scripts/voxtral-tts.py` + `mcp-health-check.py`
- `~/.claude/skills/voice-reply/` + `voice-filter/`
- `~/.claude/hooks/telegram-reply-enforcer.py` + `coding-guidelines-enforcer.py`
- `~/Library/LaunchAgents/com.<handle>.mcp-health.plist`

State:
- Telegram bot created, paired, policy locked to `allowlist`
- Debug patch applied to the Telegram plugin; `server.log` + `heartbeat.json` live
- `~/.zshrc` with `cc` + `ct` aliases (caffeinate-wrapped)
- `~/knowledge/` — initialized wiki + first source ingested (matt-stack-setup)

Services:
- Whisper (on demand)
- Voxtral MLX (on demand, via the TTS helper)
- MCP health LaunchAgent (every 5 min)
- Caffeinate-held awake state (whenever `ct` is running)

---

## Setup verification checklist

**This is the mandatory final step of the install (Part 8).** Every command below must pass before the setup is considered complete. The guiding agent is instructed to run every item, report pass/fail, and refuse to declare "done" until 100% pass plus both manual round-trip tests are confirmed.

Also useful as a regression check any time later — after a system update, plugin refresh, or if something starts feeling off, run the full list to find the regression fast.

Expected pass condition in parens for each.

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

---

One afternoon. Enjoy.
