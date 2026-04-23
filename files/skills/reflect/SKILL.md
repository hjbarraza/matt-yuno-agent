---
name: reflect
description: End-of-session reflection that measures PROGRESS ON REAL GOALS — not a session summary. Use when the operator types /reflect, says "capture what we learned today", "save this session", "reflect on this". Reads priorities/projects/clients/topics in ~/knowledge/wiki/, checks what moved vs what's drifting, proposes specific next actions. User-triggered only — never run unprompted.
---

# reflect

**Reflection is not a session summary.** A session summary says "we did X, Y, Z." That belongs in `log.md` — not a new reflection file.

A reflection asks:
> Given the goals on the operator's board, did today move them forward? What's drifting? What's blocked? What specific action would move the needle?

Reflection should make the operator better at their work and personal growth. If it reads like an AI activity log, it's wrong. Start over.

## When to invoke

- Operator types `/reflect`
- Operator says "capture what we learned today", "save this session", "reflect on this"
- End of a substantive session *if the operator signals they're done*

**Never reflect unprompted.** Never run on a cron.

## Workflow

### 0. Load context BEFORE writing anything

Read these wiki pages, in order:
1. `~/knowledge/wiki/index.md` — the map
2. Current priorities snapshot — what matters right now
3. Operating rules — how the operator wants to work
4. Every current entity page (clients, projects, products)
5. Last ~10 entries of `wiki/log.md` — recent-history context
6. Any existing reflection for the current month

Only then assess this session.

### 1. Propose a slug

Propose a short kebab-case slug. Name the *business/personal question* the reflection answers, not the topic of the session. Examples:
- `pipeline-sequencing` (if today revealed a queuing decision is pending)
- `infrastructure-vs-revenue` (if today was all infra and revenue work stalled)
- `focus-block-health` (if the work blocks aren't holding)

Ask the operator to confirm or override. Wait.

### 2. Write the reflection

Path: `~/knowledge/raw/reflections/YYYY-MM-DD_HH-MM_<slug>/source.md`

Template (fill sections honestly, skip any without real signal — don't pad):

```markdown
# <Reflection title — the question being asked>

**Date**: YYYY-MM-DD HH:MM
**Slug**: <slug>
**Session duration**: ~N minutes
**This reflection covers**: <one sentence — the scope>

---

## What actually moved (on real goals)

For each active priority / project / client, one line:
- **<item>** — [moved / blocked / untouched today] — <one-line evidence>

Be specific. "Touched the page" ≠ moved it. "Shipped X" = moved.

## What's drifting (stale or unmoved N+ days)

Look at the priorities snapshot, client commitments, open commitments. Anything the operator said would happen that hasn't. Anything queued too long.

- **<item>**: last active <date>, N days ago. Status: <blocked on X / forgotten / deprioritized?>.

If nothing is drifting, say so.

## What I learned about the operator

One or two lines max. A pattern, preference, or fact that should update future behavior. Not a compliment. Not a summary.

## Next specific actions

3-5 concrete moves the operator should take in the next 24-72 hours. Each with a single actor + action. Prioritize by impact × urgency.

- <who> <does what> by <when>
- ...

## What I'd ask the operator

One question that would unblock or sharpen the next phase. Not rhetorical.
```

### 3. Write the wiki sources page

Create `~/knowledge/wiki/sources/<slug>.md` with a short summary + cross-links to any entities/topics referenced.

### 4. Touch related pages

Update `wiki/index.md` with the new reflection. Append to `wiki/log.md`:
```
## [YYYY-MM-DD HH:MM] reflect | <question>
- raw: raw/reflections/<slug>/source.md
- key takeaway: <one line>
- next action: <first item from the list>
```

### 5. Commit

```
git -C ~/knowledge add -A && git -C ~/knowledge commit -m "reflect: <slug>"
```

### 6. Report

Two-line Telegram reply + voice TL;DR. Don't voice-read the reflection — it's long and list-heavy.

## Anti-patterns (throw it out if)

- Reads like "today we did X, Y, Z"
- Compliments the operator without evidence
- Lists things touched without saying which moved
- Avoids naming what's drifting because it's uncomfortable
- Proposes vague next actions ("continue working on X")

## Customize this

- Your priority file conventions (step 0.2)
- Your operating-rules location (step 0.3)
- The question-types you reflect on (step 1 examples)
