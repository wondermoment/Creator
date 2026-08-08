---
name: vault-linter
description: >-
  Read-only knowledge-graph integrity check for the vault. Reports broken
  [[wikilinks]], tables that render as raw text because they lack a blank line
  before them, orphaned notes (no links in or out), capture notes missing
  source/captured_from frontmatter, and Areas missing the standard init-area
  structure (kanban, to-check, hub, dashboard, draft/scout/synthesis). Use when the
  user wants to check vault health, find broken/dead links, fix broken/garbled
  tables, find orphan or disconnected notes, audit the linking graph, verify
  traceability, or check that every Area is structurally compliant. Read-only by
  default; a --headless routine mode instead writes a dated report to
  99-system/maintenance/lint-report/ and opens a correction card for Claude in
  agent-kanban.md.
---

# Vault Linter

Protects the linking graph CLAUDE.md §7 calls "the value of the vault." The check is
**deterministic** — the work is done by `lint.py`, not by eyeballing notes — so it is
exhaustive and repeatable. **Read-only: it never edits the vault, only prints a report.**

## Run it

```
python3 .claude/skills/vault-linter/lint.py
```

Both Claude and Codex run the same script via the shared skills folder. Optionally pass
a vault path as the first argument to lint a different vault.

## Headless (routine) mode

For unattended/scheduled runs, add `--headless`:

```
python3 .claude/skills/vault-linter/lint.py --headless
```

This is the **only** mode that writes anything (the default run stays strictly read-only).
Instead of printing the report to stdout, headless mode:

1. **Writes a dated report** to `99-system/maintenance/lint-report/lint-<YYYY-MM-DD>.md`
   (a fenced copy of the full report, with a short markdown header).
2. **Opens or refreshes a single correction card** in `99-system/maintenance/agent-kanban.md`
   under `## Todo`, assigned `Reviewer: Claude` so the SessionStart hook surfaces it. The
   card links to the report and tells Claude to fix the items and re-run to confirm clean.

Design rules that keep the routine sane:
- **It only fires on *actionable* findings** — broken links, broken tables, non-compliant
  Areas, missing traceability, ambiguous links. **Orphans are excluded from the trigger** (most are
  structural files that are legitimately standalone; a daily "fix 50 orphans" card would be
  permanent noise) but are still counted in the written report.
- **A clean run writes nothing** — no report file, no card, just a one-line stdout status.
- **The card is refreshed in place, never duplicated** — a stable marker
  (`**Vault-linter routine —`) means repeated runs update the one card rather than stacking.
- **It never checks the card off** — closing it is Claude's/the user's job after the fixes
  land and a re-run confirms clean. It never edits a vault note; it touches only those two
  `99-system/` maintenance files.

## What it checks

- **Broken wikilinks (ERROR)** — every `[[link]]` / `![[embed]]` resolving to no note or
  attachment. Resolution is Obsidian-style: bare targets by basename (case-insensitive),
  path-style targets (containing `/`) **by path only** — paths resolve against the vault
  root, so a `vault/`-prefixed or otherwise wrong path is broken even if the basename
  exists. Aliases (`|`) and headings/blocks (`#`) are stripped first. Links inside code
  fences / inline `code` and `{{placeholder}}` targets are ignored.
- **Tables with no blank line before them (ERROR)** — a Markdown table cannot interrupt an
  open block, so a table placed directly under a paragraph, a **bold caption**, a list item,
  or a blockquote is swallowed into it and renders as raw `| … |` text in Obsidian. A heading
  or an HTML comment closes its own block and is allowed directly above a table. Pipe rows
  inside code fences are ignored. The report gives the `file:line` of each header row and the
  line above it; the fix is a single blank line. (See conventions.md "Tables".)
- **Ambiguous bare links (WARN)** — a bare `[[name]]` whose basename is shared by 2+ notes:
  Obsidian silently picks one; path-qualify these so they can't repoint when notes move.
- **Orphaned notes (WARN)** — knowledge notes with no inbound *and* no outbound links.
  Structural files are excluded (`99-system/**`, `daily-notes/**`, `README.md`, `TODO.md`).
- **Missing traceability (WARN)** — *captured* notes (`00-inbox/**` and any `draft/`
  folder) lacking `source` or `captured_from` frontmatter, per CLAUDE.md §6. Generated
  outputs (`scout/`, `synthesis/`) and other notes are exempt — they have no single source.
- **Non-compliant Areas (WARN)** — every immediate subdirectory of `01-work/areas/` and
  `02-personal/areas/` is expected to carry the structure `init-area` scaffolds: the four
  files `<slug>.md`, `todo-kanban.md`, `to-check.md`, `<slug>-dashboard.md` and the three
  folders `draft/`, `scout/`, `synthesis/`. The report lists exactly what each Area is
  missing. Nested product folders (`areas/<area>/<product>/`) sit one level deeper and are
  never mistaken for Areas. Caveat: the required folders are scaffolded empty, and an empty
  dir does not survive a git round-trip, so a fresh clone may warn on a folder until a skill
  writes into it — acceptable for a local check run where the work happens.

## Using the output

1. Run the script; read the report (counts + `file:line` per issue).
2. **Report, don't auto-fix.** This skill only diagnoses. Surface findings to the user.
   Many copies of the *same* broken target (e.g. `[[second-brain]]`) usually means an Area
   hub note doesn't exist yet — not 20 separate typos.
3. If asked to fix, do it as a separate, explicit step. The linter itself stays read-only.

## Tuning

Exclusions and capture-folder names are constants at the top of `lint.py` (`SKIP_DIRS`,
`CAPTURE_SEGMENTS`, …). The Area-compliance contract is likewise tunable there
(`AREA_PARENTS`, `AREA_REQUIRED_FILES`, `AREA_REQUIRED_DIRS`) — keep it in sync with what
`init-area` scaffolds. Adjust any of these if the vault's conventions change.
