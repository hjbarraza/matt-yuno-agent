# knowledge — a personal wiki

Adapted from [Andrej Karpathy's LLM-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). File-based, git-versioned, LLM-maintained. No database, no search infrastructure — just markdown in folders.

Three layers:

1. **`raw/`** — immutable primary sources. Transcripts, articles, session dumps. Never edit after ingest; create new dated directories for new material.
2. **`wiki/`** — LLM-maintained derived notes. Summaries, entity pages, concept pages, overviews, syntheses. Linked with Obsidian-style `[[wikilinks]]`.
3. **`CLAUDE.md`** (this file) — schema + workflows.

## Layout (convention, not strict)

Karpathy's design is deliberately flexible. The layout below is the convention we've adopted — adjust to fit the domain.

```
~/knowledge/
├── CLAUDE.md
├── raw/
│   └── YYYY-MM-DD_<slug>/
│       └── source.md        # primary source; attachments alongside
└── wiki/
    ├── index.md             # content-oriented catalog, organized by category
    ├── log.md               # append-only chronological record
    ├── entities/            # people, projects, orgs — one node per entity
    ├── concepts/            # ideas, definitions, frameworks
    ├── topics/              # broader areas spanning multiple concepts
    └── sources/             # curated summaries of raw/ entries
```

The four subfolder types (entities / concepts / topics / sources) are our naming convention; Karpathy names these kinds of pages but doesn't mandate separate folders. You can flatten or split further if that fits better — just be consistent.

## Frontmatter (recommended)

Karpathy notes frontmatter is optional but enables Dataview-style dynamic tables in Obsidian. We write it on every `wiki/*.md` node because the agent uses it for quick triage:

```yaml
---
type: entity|concept|topic|source
id: <kebab-case-slug>        # matches filename without .md
title: <Human-readable title>
tags: [tag1, tag2]
links: [[[other-node]], [[another]]]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: [[sources/<slug>]]   # for nodes derived from a specific raw source
---
```

Wikilinks are paths relative to `wiki/`: `[[entities/h]]`, `[[concepts/mcp-plugin]]`. Reciprocate links when possible.

## Log format

`wiki/log.md` is an append-only chronological record. Entries use the header format from Karpathy's gist:

```markdown
## [YYYY-MM-DD] operation | title

Optional prose body with details + wikilinks.
```

Common operations: `scaffold`, `ingest`, `update`, `reflect`, `lint`. Add more as needed.

## Workflows

### Ingest

1. Save the primary source to `raw/YYYY-MM-DD_<slug>/source.md` (+ attachments). Lead with paste-date and origin (URL, session, who said what).
2. Write `wiki/sources/<slug>.md` — tight summary with TL;DR. Quote from raw where useful.
3. Extract entities, concepts, topics into their respective folders. Reuse existing nodes where they match; don't duplicate.
4. Link bidirectionally between new and existing nodes.
5. Append to `wiki/log.md` using the `## [YYYY-MM-DD] ingest | <slug>` format.
6. Update `wiki/index.md` if the ingest adds a node worth surfacing at the top level.
7. Commit with `ingest: <slug>`.

Karpathy's emphasis: **stay involved** — ingest sources one at a time with discussion, don't let the LLM run unattended.

### Query

Start at `wiki/index.md`, follow wikilinks, dereference `source:` back to `raw/` when verification matters. If a fact isn't in the wiki, say so — don't guess from training data.

Per Karpathy, `index.md` scales to ~100 sources before you need a dedicated search tool. Below that threshold, grep is enough.

### Lint (periodic, not per-commit)

Look for:
- Every `wiki/*.md` has frontmatter (if you've adopted our convention).
- Every `[[wikilink]]` resolves to an existing file.
- `created`/`updated` are ISO dates; `updated` ≥ `created`.
- No orphan nodes: each is reachable from `index.md` or linked from `log.md`.
- Contradictions between pages — flag or reconcile.
- Stale claims — check against `source:` references; freshen if needed.

Run periodically, not on every commit. Karpathy's framing: lint is a health check, not a gate.
