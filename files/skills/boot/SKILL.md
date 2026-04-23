---
name: boot
description: Session-start status dashboard. Invoke at the beginning of a working session or whenever the operator types "boot" / "/boot" / "status" / "dashboard" / "what's on". Prints a drift-aware snapshot — local time + current schedule block, priorities-snapshot freshness, named focus for today, open tasks, open GitHub issues, today's calendar, wiki entities with stale `updated:`, and health-first nudges if bedtime or workout windows are in play.
---

# boot

## Purpose

Surface drift and current state at the start of a working session, so the operator doesn't have to ask "where am I?". Opposite of a reflection — this is *right now*, not a look back.

Everything the operator would ask about if they sat down cold. If they regularly have to ask "wait, what about X?" after `/boot`, the skill is missing a source — update the data-sources list.

## When to invoke

- Operator types: `boot`, `/boot`, `status`, `dashboard`, `what's on`
- Start of a substantive working session, unprompted (once per session)
- Resumed session after >4h gap, if re-orientation helps

**Skip:**
- Mid-task — don't interrupt flow with a dashboard
- Quick one-liners that don't need orientation

## Data sources — run in parallel

1. **Time + schedule block.** Current local time. Map to block from `~/knowledge/wiki/topics/schedule-and-rhythm.md` (create this file with your own schedule). Example blocks:
   - 06:00–09:00 → morning / pre-workout
   - 09:00–13:00 → focus block 1
   - 13:00–15:00 → lunch / transition
   - 15:00–19:00 → focus block 2
   - 19:00–22:00 → evening / wind down
   - 22:00–06:00 → bedtime (health-first nudge fires)

2. **Priorities snapshot.** Find the latest priorities page in `~/knowledge/wiki/topics/priorities-*.md`. Read frontmatter `updated:`. If > 7 days old, flag STALE. Print top 3 items.

3. **Named focus for today.** Grep `~/knowledge/wiki/log.md` for today's date + "focus named". If nothing, show the most recent focus entry.

4. **Open tasks.** `TaskList` — all pending + in_progress. Title + short status.

5. **Open GitHub issues across your repos.** `gh search issues --owner <YOUR_USERNAME> --state open --limit 20 --json repository,number,title,updatedAt`. Group by repo. Newest first.

6. **Today's calendar.** Via Google Calendar MCP. Print summary + start time. Flag current/next event.

7. **Drift radar (wiki).** Glob `~/knowledge/wiki/{entities,topics}/*.md`. Read each frontmatter `updated:`. Filter: age > 7 days. Exclude: `index.md`, `log.md`, intentionally-dated pages. Print as "entities not touched in >7d — still active?".

8. **Health-first nudge (conditional).**
   - If current time ≥ 22:00 and < 06:00 → "Sleep window. This can wait to tomorrow if not urgent."
   - If current time ≥ 23:30 → stronger reminder.
   - If past 18:00 and no workout flag today → "Trained yet today?"

## Output format

Telegram-readable, plain text. Short, scannable.

```
BOOT — 2026-MM-DD HH:MM <tz>
────────────────────────────────────
BLOCK: <current block>
FOCUS TODAY: <named focus or fallback>

PRIORITIES (snapshot Nd stale — refresh?):
• item 1
• item 2
• item 3

OPEN TASKS:
• task 1
• task 2

CALENDAR (today):
• HH:MM  event
• HH:MM  event

GITHUB ISSUES:
• repo#123  title
• repo#124  title

DRIFT RADAR (wiki, >7d untouched):
• entities/foo
• topics/bar

────────────────────────────────────
```

## Voice-reply (Telegram)

When invoked via Telegram, voice-reply applies. Voice script = 2–3 sentence TL;DR of the most actionable line. Never voice-read the dashboard verbatim — it has lists, dates, issue numbers. Text carries structure; voice carries the narrative.

## Terminal vs Telegram

- **Telegram:** full dashboard as text + voice TL;DR.
- **Terminal:** dashboard only, no voice.

## Implementation notes

Run the 8 data sources in parallel where the tool permits. Time budget ≤ 10 seconds for a cold boot. If a source fails, skip it and note the miss rather than blocking the whole dashboard.

## Falsifier

If the operator regularly has to ask "and what about X?" after `/boot` → a data source is missing. Update the list.

## Customize this

- Your timezone + schedule blocks (step 1)
- Your GitHub username (step 5)
- Your priorities / focus file conventions
- Nudge thresholds + language (step 8)
