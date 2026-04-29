---
name: weekly-retro
description: Weekly cross-session retrospective on the operator-agent collaboration. Use when the operator types `/weekly-retro`, `/retro`, `weekly retro`, or "let's reflect on this week". Reads the last 7 days of session transcripts across `~/.claude/projects/*/`, surfaces patterns (recurring friction, repeated agent mistakes, verbal feedback that didn't make it to memory), proposes durable updates, and writes a retro doc that crosses to the operator's shared knowledge dir so any twin instances benefit. User-invoked only — never auto, never on cron.
---

# weekly-retro

**This is not a session summary or a per-session reflection.** Those exist (`reflect` skill). This skill exists to tune the **collaboration** itself — the way the operator and agent work together — across a multi-session window.

A good retro asks:
> Across this week's sessions: where did the operator have to repeat themselves? Where did the agent claim "done" before it was? What feedback signal landed verbally but never crossed to durable memory? What pattern is forming that neither of us has named yet?

If the output reads like an activity log of what got built, it's wrong. Start over.

## When to invoke

- Operator types `/weekly-retro`, `/retro`, "weekly retro", "let's reflect on this week", "retro"
- Operator explicitly proposes a reflection on the prior week's work

**Never invoke unprompted. Never run on a cron.** A retro that fires when the operator's attention is elsewhere is the opposite of the point.

## Configuration

The skill reads two operator-defined paths:

- **Knowledge dir** — where the operator's shared codex / wiki lives. Default: `~/knowledge/`. Override by setting an env var or by editing the paths below to your own location.
- **Retro output dir** — where retro docs are written. Default: `<knowledge-dir>/wiki/retro/`.

If the operator runs a single instance with no twin and no shared codex, the retro can still run — write the output to a local file (e.g. `~/.claude/retros/`) and skip the codex-sync section.

## Inputs

1. **Session transcripts (last 7 days):**
   ```bash
   find ~/.claude/projects -name "*.jsonl" -type f -mtime -7
   ```
   Each `.jsonl` is one session. Each line is a JSON event (user message, assistant message, tool use). Group by project slug (the parent directory name) so cross-session patterns within one project surface clearly.

2. **Current memory state across projects:**
   ```bash
   find ~/.claude/projects -path "*/memory/MEMORY.md"
   ```
   What's already captured durably — so the retro doesn't propose redundant entries.

3. **Recent knowledge-dir updates:** read `<knowledge-dir>/wiki/log.md` last ~20 entries (or whatever the operator's equivalent journal is). Anchors the retro in what's already documented.

4. **Prior retros:** glob `<retro-output-dir>/*.md`, read the last 1–2. Surface patterns that recur week-over-week — those are the load-bearing ones.

## Workflow

### 0. Pull the knowledge dir first
```bash
cd <knowledge-dir> && git pull --rebase
```
Any twin instance may have written something since the last sync. Skip if the operator has no shared codex.

### 1. First-pass synthesis (without the operator)

Read the inputs. Draft a structured first pass with these sections:

- **What got done.** Two lines max — anchor the rest, don't dwell.
- **Friction the operator surfaced.** Verbatim quotes from operator messages where they pushed back, corrected, or expressed dissatisfaction. Examples: "you didn't verify", "this is the third time you forgot X", "no, that's the wrong framing." Source-cite by project + approximate timestamp.
- **Agent mistakes by detail.** Specific bugs the agent caused, dressed-up confidence that didn't hold up, scope overshoots, claimed-done-but-wasn't moments. Aim for the level of specificity that lets the operator recognize the moment, e.g. "used wrong API slug — guessed from training data instead of confirming via the provider's models endpoint" — not generic apology.
- **Verbal feedback that didn't cross to memory.** The most important section. Search for moments where the operator said something like a rule ("verify before claiming done", "small reversible moves", "no auto-firing skills") and check whether that phrase made it into `MEMORY.md` or the operator's knowledge dir. If it didn't, propose the entry.
- **Pattern forming.** Cross-session, cross-project. Where the same shape of problem keeps reappearing under different surfaces. Name it, even tentatively.
- **Decisions made off-camera.** Topics where the operator clearly decided something the logs don't fully explain. Flag explicitly: "I see X happened but the why isn't in the logs — what was the call?"

### 2. Sit with the operator

Show the first pass. Then ask, in this order:
1. "What's missing from the logs that I couldn't see?" — the load-bearing question. Decisions, intuitions, energy state, off-channel context.
2. "Of the patterns I named, which ones land? Which are wrong?"
3. "Of the verbal-feedback items, are any worth crossing to memory or your knowledge dir?"

Listen. The interpretation is the part the operator can't outsource.

### 3. Convert durable findings

For each agreed-on item:
- **Memory entry** (per-project preference, ephemeral): `~/.claude/projects/<slug>/memory/<topic>.md` + register in `MEMORY.md`
- **Knowledge-dir entry** (cross-instance, durable): `<knowledge-dir>/wiki/concepts/` or wherever the operator's wiki organizes durable concepts
- **Skill update** (behavioral rule that should fire automatically): edit the relevant SKILL.md in the operator's skills source-of-truth

### 4. Write the retro doc

`<retro-output-dir>/YYYY-MM-DD-weekly.md` (Sunday's date — the retro covers the week ending Sunday).

Suggested frontmatter (adapt to the operator's wiki schema):
```yaml
---
type: retro
id: retro-YYYY-MM-DD
title: "Weekly retro — week ending YYYY-MM-DD"
tags: [retro, weekly, collaboration]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Sections (omit any that have no content for the week):
- **Friction surfaced** — bullet list with verbatim quotes + source
- **Agent mistakes** — bullet list with detail
- **Verbal feedback now durable** — with link to the new memory/knowledge-dir/skill entry
- **Patterns named** — short prose, one paragraph per pattern
- **Action items for next week** — concrete behaviors to change, attributable to either operator or agent

### 5. Commit + push the knowledge dir
```bash
cd <knowledge-dir>
git add wiki/retro/ wiki/concepts/
git commit -m "retro: week ending YYYY-MM-DD"
git push
```

If skill files were updated, also commit + push the skills source-of-truth so any twin instance picks them up on the next pull.

Skip both git steps if the operator runs a single instance without a shared repo.

## Output format example

```markdown
# Weekly retro — week ending 2026-04-29

## Friction surfaced
- "you test it. verify it works before asking labour from me." (project-slug, 2026-04-29) — landed in memory as `feedback_verification.md`
- "shadow on form is weird. it shouldnt." (project-slug, 2026-04-29) — pattern: scope overshoot on UI polish, agent adds visual flourishes the operator didn't ask for

## Agent mistakes
- Used a wrong API model slug — guessed from training data instead of confirming via the provider's models endpoint. Broke the dependent feature silently for hours.
- Doubled apostrophes inside Postgres dollar-quoted strings — forgot dollar-quotes treat content literally. Live data fix via REPLACE; source patched in a follow-up migration.
- Claimed "verified" once before running runtime smoke. Operator caught it. Now: gates pass ≠ done.

## Verbal feedback now durable
- `~/.claude/projects/<slug>/memory/feedback_verification.md` — added "tests/lint/build green is necessary not sufficient; smoke test against real HTTP before claiming done"

## Patterns named
- **Confidence-without-evidence**: agent claims a fix works before exercising the runtime. Three instances this week. Counter: every "verified" claim must point to a concrete observation (DB row, network response, screenshot).

## Action items
- Agent: before saying "verified", produce one piece of runtime evidence in the same message
- Operator: keep pushing back when the framing is the bug; the chain analysis only happened because you pressed
```

## Common mistakes / red flags

| Anti-pattern | Why it's wrong |
|---|---|
| Listing what got built | That's a session summary. The retro is about how we worked, not what we shipped. |
| Generic "the agent will improve" claims | If there's no specific behavioral change, there's no retro. Skip it. |
| Skipping the gap-filling step | Logs are evidence, not interpretation. The conversation with the operator is the load-bearing half. |
| Auto-firing on a cron | Retros require attention. Forced retros calcify into ritual. Operator-invoked only. |
| Writing the retro without syncing | Any twin instance won't see it. The whole point is cross-instance learning. |
| Mistakes phrased as apology rather than detail | "I'm sorry I made an error" is empty. "I used the wrong slug because I trusted training data over the API" is useful. |

## Integration

**Pairs with:**
- `reflect` — per-session goal-progress reflection. Different cadence, different question. A weekly retro can reference the week's reflections.
- `boot` — start-of-session orientation. The retro updates the knowledge-dir log so the next `boot` surfaces the new context.

**Read by:** any agent instance that has access to the same knowledge dir. The skill source-of-truth is shared via the operator's skills repo; output flows through the knowledge dir.
