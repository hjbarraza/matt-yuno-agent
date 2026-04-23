---
name: firewall-check
description: Enforce confidentiality firewalls across projects, clients, or entities that must NOT cross-contaminate. Invoke BEFORE loading entity/topic pages, drafting external comms, or running queries that touch entities on opposite sides of a wall. Breaking a firewall is a real confidentiality violation.
---

# firewall-check

Some of your operator's work has hard walls between parties. Treat them as constraints, not guidelines.

## Why this skill exists

If the operator has two clients who must not know about each other, two product surfaces with exclusive partner deals, or a strategic partner vs. a competitor — the agent can leak context across that wall by accident. This skill is the guardrail.

## Defining your walls

Create a file at `~/knowledge/wiki/topics/firewalls.md` that enumerates every wall, in this format:

```markdown
# Firewalls

## Firewall 1: <Entity A> ↔ <Entity B>

- **<Entity A>** is <what it is>.
- **<Entity B>** is <what it is>.
- Hard rule: never cross.

**What must NOT leak (A → B):** code, client names, deliverables, scope of engagement, strategic intent, rates, internal docs.
**What must NOT leak (B → A):** same, symmetric.

**Allowed to cross:** (enumerate explicitly) — e.g., "that the operator exists", "public marketing material for A".

## Firewall 2: <Entity C> ↔ <Entity D>

...
```

## When to invoke this skill

**Before:**
- Loading a wiki entity page that's on one side of a wall
- Drafting external comms (email, PR, post) mentioning any walled entity
- Running a query or synthesis that could touch entities across a wall
- Any action where you'd reference entity X in a context belonging to entity Y

## Check pattern

Before loading an entity page:
1. Read `wiki/topics/firewalls.md` if not already in context
2. Identify which wall the entity sits behind
3. Identify which walls the current conversation/output sits behind
4. If current output side ≠ entity side → STOP. You cannot use this entity in this output.

Pattern for violation: "I was about to reference entity X. That entity sits behind firewall Y. The current output is on the other side. Not citing."

## Ambiguous cases

If you're unsure whether a piece of info is behind a wall, default to "assume yes, don't use it, ask the operator". Wrong side of caution is cheap; leaking is not.

## Post-session audit

As part of `/reflect` or `seven-rules` post-session audit, scan the transcript for mentions of walled entities in the wrong context. Flag any findings as incidents.

## Customize this

- Fill in your own walls in `wiki/topics/firewalls.md`. Don't copy anyone else's entities — they're confidential by definition.
- Add entity metadata (`firewall:` field in frontmatter) so this skill can auto-detect without reading `firewalls.md` every time.
- If you have >3 walls, consider a hook that blocks file reads for walled entities when the session state indicates the wrong side.
