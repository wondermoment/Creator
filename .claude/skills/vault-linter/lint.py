#!/usr/bin/env python3
"""vault-linter — read-only knowledge-graph integrity check for the Obsidian vault.

Checks:
  ERROR  broken [[wikilinks]] / ![[embeds]] that resolve to no note or attachment
         (path-style targets must match by path — Obsidian resolves them against the
         vault root, so a basename fallback would hide links broken in Obsidian)
  ERROR  tables with no blank line before them — a table cannot interrupt an open
         paragraph/list/blockquote, so it renders as raw "| ... |" text in Obsidian
         (a heading or HTML comment closes its block, so those are allowed above a table)
  WARN   orphaned knowledge notes (no inbound and no outbound links)
  WARN   capture notes missing `source` / `captured_from` frontmatter
  WARN   ambiguous bare links (basename shared by 2+ notes — should be path-qualified)
  WARN   non-compliant Areas (missing the files/folders init-area scaffolds)

READ-ONLY by default: the normal run never modifies anything, it only prints a report.
The ONE exception is --headless (routine/unattended mode): instead of printing, it writes a
dated report under 99-system/maintenance/lint-report/ and opens/refreshes a single
correction card (assigned to Claude) in 99-system/maintenance/agent-kanban.md. It never
touches a vault note — only those two maintenance files. Use it from a scheduled routine.

  python3 .claude/skills/vault-linter/lint.py [vault_path]
  python3 .claude/skills/vault-linter/lint.py [vault_path] --headless

Scope decisions (documented so they are tunable, not magic):
  - Skipped entirely: .obsidian/, .trash/, 99-system/templates/ (scaffolding).
  - Links inside code fences / inline `code` are ignored (they are illustrative,
    e.g. `[[wikilinks]]`), as are `{{placeholder}}` targets.
  - Orphan check covers *knowledge notes* only: excludes 99-system/**, any
    daily-notes/** and README.md / TODO.md (structural, legitimately standalone).
  - Traceability check covers *captured* notes only: 00-inbox/** and any draft/ folder.
    Generated outputs (scout/, synthesis/) aggregate other notes and are exempt — they
    have no single source.
  - Area-compliance covers every immediate subdirectory of AREA_PARENTS (the two
    areas/ roots). Nested product folders (areas/<area>/<product>/) are one level
    deeper, so they are not mistaken for Areas. Required set = what init-area scaffolds.
    Caveat: the three required dirs are created empty; an *empty* dir does not survive a
    git round-trip, so on a fresh clone the folder WARN may fire until a skill writes to
    them. This is a local dev check, run where the work happens — acceptable, and tunable.
"""
import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

SKIP_DIRS = {".obsidian", ".trash"}
SKIP_PREFIXES = ("99-system/templates/",)
CAPTURE_TOP = ("00-inbox/",)
CAPTURE_SEGMENTS = {"draft"}
# Per-area structural files share these basenames BY DESIGN (init-area scaffolds one per
# Area); bare links to them are ubiquitous, so they are exempt from the ambiguity WARN.
AMBIGUOUS_OK = {"todo-kanban", "to-check", "dashboard", "readme"}
ATTACH_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".canvas", ".md"}
# Area-compliance: the standard structure init-area scaffolds. "{slug}" -> the Area's
# folder name. Every immediate subdirectory of an AREA_PARENT is expected to carry these.
AREA_PARENTS = ("01-work/areas", "02-personal/areas")
AREA_REQUIRED_FILES = ("{slug}.md", "todo-kanban.md", "to-check.md", "{slug}-dashboard.md")
AREA_REQUIRED_DIRS = ("draft", "scout", "synthesis")
# --headless (routine) mode. Writes live under 99-system/ only.
LINT_REPORT_DIR = "99-system/maintenance/lint-report"
KANBAN_REL = "99-system/maintenance/agent-kanban.md"
# Which finding categories warrant a correction task. Orphans are excluded on
# purpose: most are structural files (kanbans/to-check/dashboards) that are
# legitimately standalone, so they must not trigger a daily task — they are still
# recorded in the written report for context.
ACTIONABLE_KEYS = ("broken", "broken_tables", "noncompliant", "missing_trace", "ambiguous")
# Stable marker so the routine refreshes its own card instead of stacking a new one.
ROUTINE_CARD_MARKER = "**Vault-linter routine —"

WIKILINK_RE = re.compile(r"!?\[\[([^\[\]]+?)\]\]")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
TRACE_RE = re.compile(r"^(source|captured_from)\s*:", re.IGNORECASE)
# A GFM table delimiter row, e.g. "| :-- | :-- |" or "|---|---|". Requires >=2 columns
# (the trailing group needs one more pipe), so a bare "---" HR or frontmatter fence never
# matches — the pipe is the table's unambiguous signature.
TABLE_DELIM_RE = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$")
# Prev-line kinds that a table is allowed to sit directly under (they close their own
# block, so the table still renders). Everything else open before a table — a paragraph,
# a bold caption, a list item, a blockquote — swallows the table into itself and it renders
# as raw "| ... |" text. See conventions.md "Tables".
TABLE_OK_PREV_RE = re.compile(r"^\s*(#{1,6}\s|<!--|%%)")


def find_vault(vault_arg=None) -> Path:
    if vault_arg:
        return Path(vault_arg).resolve()
    # .claude/skills/vault-linter/lint.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3] / "vault"


def is_skipped(rel: str) -> bool:
    if rel.split("/", 1)[0] in SKIP_DIRS:
        return True
    return any(rel.startswith(p) for p in SKIP_PREFIXES)


def is_capture(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    if name == "README.md":
        return False
    if any(rel.startswith(t) for t in CAPTURE_TOP):
        return True
    return any(seg in CAPTURE_SEGMENTS for seg in rel.split("/")[:-1])


def is_knowledge_note(rel: str) -> bool:
    if rel.startswith("99-system/"):
        return False
    if "daily-notes/" in rel:
        return False
    return rel.rsplit("/", 1)[-1] not in {"README.md", "TODO.md"}


def clean_target(raw: str):
    """Normalise a raw wikilink target to a lookup key, or None to skip."""
    t = raw.replace("\\", "").strip()
    t = t.split("|", 1)[0].split("#", 1)[0].strip()  # drop alias + heading/block
    if not t or "{{" in t:
        return None
    return t


def extract_links(text: str):
    """Yield (lineno, target_key) skipping code fences and inline code."""
    fence_marker = None  # the marker that opened the current fence (``` or ~~~)
    for i, line in enumerate(text.splitlines(), 1):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if fence_marker is None:
                fence_marker = marker
            elif marker == fence_marker:  # only the matching marker closes the fence
                fence_marker = None
            continue
        if fence_marker is not None:
            continue
        for m in WIKILINK_RE.finditer(INLINE_CODE_RE.sub("", line)):
            key = clean_target(m.group(1))
            if key is not None:
                yield i, key


def find_broken_tables(text: str):
    """Yield (header_lineno, prev_snippet) for tables that will render as raw '| ... |'
    text in Obsidian because no blank line separates them from the block above.

    A GFM table cannot interrupt an open paragraph: if the line right before the header
    row is a paragraph (incl. a bold caption like '**Value**'), a list item, or a
    blockquote, the table is absorbed into it. A heading or an HTML comment closes its own
    block, so a table may sit directly under those. Code fences are skipped so a pipe row
    inside a ``` block is never mistaken for a table."""
    lines = text.split("\n")
    fence_marker = None
    for j, line in enumerate(lines):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if fence_marker is None:
                fence_marker = marker
            elif marker == fence_marker:
                fence_marker = None
            continue
        if fence_marker is not None:
            continue
        # j is a delimiter row → header is j-1, the block above it is j-2.
        if j < 2 or not TABLE_DELIM_RE.match(line):
            continue
        header = lines[j - 1]
        if not header.lstrip().startswith("|"):
            continue  # delimiter with no pipe header above → not a real table here
        prev = lines[j - 2]
        if not prev.strip():
            continue  # blank line before the table → renders fine
        if prev.lstrip().startswith("|"):
            continue  # part of another/preceding table row
        if TABLE_OK_PREV_RE.match(prev):
            continue  # heading / comment closes its block → table renders fine
        yield j, prev.strip()[:60]


def check_areas(vault: Path):
    """Return [(area_rel, [missing_item, ...]), ...] for non-compliant Areas.

    Missing files are listed as their name; missing dirs get a trailing "/".
    """
    problems = []
    for parent in AREA_PARENTS:
        pdir = vault / parent
        if not pdir.is_dir():
            continue
        for entry in sorted(pdir.iterdir(), key=lambda p: p.name):
            if not entry.is_dir() or entry.name in SKIP_DIRS:
                continue
            slug = entry.name
            missing = [
                tmpl.replace("{slug}", slug)
                for tmpl in AREA_REQUIRED_FILES
                if not (entry / tmpl.replace("{slug}", slug)).is_file()
            ]
            missing += [
                d + "/" for d in AREA_REQUIRED_DIRS if not (entry / d).is_dir()
            ]
            if missing:
                problems.append((f"{parent}/{slug}", missing))
    return problems


def has_traceability(text: str) -> bool:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if TRACE_RE.match(line):
            return True
    return False


def _issue_summary(counts) -> str:
    return (
        f"{counts['broken']} broken link(s), {counts['broken_tables']} broken table(s), "
        f"{counts['noncompliant']} non-compliant area(s), "
        f"{counts['missing_trace']} missing-traceability, {counts['ambiguous']} ambiguous link(s)"
    )


def _report_md(stamp: str, report: str, counts, actionable: int) -> str:
    """The dated report file written in headless mode. Body is fenced so the linter's
    own link scan ignores any [[broken-target]] lines listed inside it."""
    return (
        "---\n"
        "type: reference\n"
        "status: active\n"
        f"created: {stamp}\n"
        "tags:\n"
        "  - vault-linter\n"
        "  - maintenance\n"
        "---\n\n"
        f"# Vault-linter report — {stamp}\n\n"
        f"**{actionable} actionable issue(s)** — {_issue_summary(counts)}. "
        f"Orphans: {counts['orphans']} (mostly structural — informational, review before touching). "
        f"Generated headless by `vault-linter`; correction task tracked in [[agent-kanban]].\n\n"
        "```\n"
        f"{report}\n"
        "```\n"
    )


def _read_lines_preserving_newline(path: Path):
    """Return (lines, newline) reading bytes so we can rewrite with the file's original
    line ending. The vault is CRLF on Windows (git autocrlf=true); relying on
    read_text/write_text translation is os.linesep-dependent and would flip endings when a
    routine runs under a different Python build. Byte-level keeps the diff clean anywhere."""
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return text.split("\n"), newline


def _upsert_kanban_card(kanban: Path, counts, actionable: int, stamp: str, rel_report: str) -> str:
    """Refresh the single routine card in place if present, else insert it first under
    ## Todo. Assigned to Claude so the SessionStart hook surfaces it. Returns a status word."""
    if not kanban.is_file():
        return "skipped (agent-kanban.md not found)"
    lines, newline = _read_lines_preserving_newline(kanban)
    # Path-qualified link (bare date basenames collide with daily notes → would trip the
    # linter's own ambiguity check); drop the .md the way Obsidian path links do.
    link = f"[[{rel_report[:-3]}|lint-{stamp}]]"
    card = (
        f"- [ ] {ROUTINE_CARD_MARKER} {actionable} issue(s) to correct ({stamp})** "
        f"| Creator: vault-linter | Reviewer: Claude — Headless lint run found {actionable} "
        f"actionable issue(s): {_issue_summary(counts)}. Orphans: {counts['orphans']} "
        f"(mostly structural — review, don't blanket-fix). Full report: {link}. Fix the "
        f"actionable items, re-run `python3 .claude/skills/vault-linter/lint.py` to confirm "
        f"clean, then check this card off."
    )
    for i, ln in enumerate(lines):
        if ln.startswith("- [ ] ") and ROUTINE_CARD_MARKER in ln:
            lines[i] = card
            kanban.write_bytes(newline.join(lines).encode("utf-8"))
            return "refreshed"
    for i, ln in enumerate(lines):
        if ln.strip() == "## Todo":
            insert_at = i + 1
            while insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            lines.insert(insert_at, card)
            kanban.write_bytes(newline.join(lines).encode("utf-8"))
            return "created"
    return "skipped (## Todo lane not found)"


def run_headless(vault: Path, report: str, counts) -> int:
    """Routine mode: write a dated report + open/refresh one correction card, but only
    when there are actionable issues. Clean (or orphans-only) runs write nothing."""
    actionable = sum(counts[k] for k in ACTIONABLE_KEYS)
    if actionable == 0:
        print(
            f"vault-linter headless: clean — 0 actionable issue(s) "
            f"({counts['orphans']} orphan(s), informational). No report or card written."
        )
        return 0

    stamp = date.today().isoformat()
    rel_report = f"{LINT_REPORT_DIR}/lint-{stamp}.md"
    report_path = vault / rel_report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    # write_bytes (not write_text) so newlines aren't os.linesep-translated; git autocrlf
    # normalizes on add. Deterministic LF regardless of the platform the routine runs on.
    report_path.write_bytes(_report_md(stamp, report, counts, actionable).encode("utf-8"))

    card_status = _upsert_kanban_card(vault / KANBAN_REL, counts, actionable, stamp, rel_report)
    print(
        f"vault-linter headless: {actionable} actionable issue(s) — "
        f"report written to {rel_report}; kanban card {card_status}."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only knowledge-graph integrity check for the Obsidian vault."
    )
    parser.add_argument("vault_path", nargs="?", help="vault directory (default: the repo's vault/)")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="routine mode: write a dated report to 99-system/maintenance/lint-report/ and "
        "open/refresh a correction card in agent-kanban.md instead of printing to stdout",
    )
    args = parser.parse_args()

    vault = find_vault(args.vault_path)
    if not vault.is_dir():
        print(f"vault-linter: vault not found at {vault}", file=sys.stderr)
        return 2

    notes, all_files = [], []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            rel = (Path(root) / f).relative_to(vault).as_posix()
            if is_skipped(rel):
                continue
            all_files.append(rel)
            if f.endswith(".md"):
                notes.append(rel)

    files_set = {r.lower() for r in all_files}
    name_set = {Path(r).name.lower() for r in all_files}
    note_lookup = {}  # basename / path keys -> rel (first match wins)
    for r in notes:
        rl = r.lower()
        note_lookup.setdefault(rl[:-3], r)        # full path, no .md
        note_lookup.setdefault(Path(r).stem.lower(), r)  # basename

    stem_counts = {}  # basename stem -> how many notes share it (ambiguity check)
    for r in notes:
        stem = Path(r).stem.lower()
        stem_counts[stem] = stem_counts.get(stem, 0) + 1

    def resolve_note(target: str):
        # Path-style targets (containing "/") can only hit full-path keys in note_lookup;
        # basename keys never contain "/", so no wrong-path link resolves via basename here.
        low = target.lower()
        if Path(target).suffix.lower() in ATTACH_EXTS - {".md"}:
            return None
        return note_lookup.get(low) or note_lookup.get(low.removesuffix(".md"))

    def resolve_any(target: str) -> bool:
        low = target.lower()
        if "/" in target:
            # Path-style: exact path (with or without .md) only — no basename fallback.
            return low in files_set or (low + ".md") in files_set
        if Path(target).name.lower() in name_set or low in files_set:
            return True
        if (low + ".md") in files_set:
            return True
        return resolve_note(target) is not None

    broken = []                       # (note, lineno, target)
    broken_tables = []                # (note, lineno, prev_snippet) — table with no blank line before
    ambiguous = []                    # (note, lineno, target) — bare link, basename not unique
    outbound_any = {}                 # note -> bool (has any wikilink)
    inbound = {r: set() for r in notes}
    missing_trace = []

    for r in notes:
        try:
            text = (vault / r).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"vault-linter: cannot read {r}: {e}", file=sys.stderr)
            continue

        seen_link = False
        for lineno, target in extract_links(text):
            seen_link = True
            if not resolve_any(target):
                broken.append((r, lineno, target))
            elif (
                "/" not in target
                and target.lower().removesuffix(".md") not in AMBIGUOUS_OK
                and stem_counts.get(target.lower().removesuffix(".md"), 0) > 1
            ):
                # Bare link to a non-unique basename: Obsidian picks one silently —
                # it should be path-qualified so it can't repoint when notes move.
                ambiguous.append((r, lineno, target))
            tgt_note = resolve_note(target)
            if tgt_note and tgt_note != r:
                inbound[tgt_note].add(r)
        outbound_any[r] = seen_link

        for header_lineno, prev_snippet in find_broken_tables(text):
            broken_tables.append((r, header_lineno, prev_snippet))

        if is_capture(r) and not has_traceability(text):
            missing_trace.append(r)

    orphans = [
        r for r in notes
        if is_knowledge_note(r) and not outbound_any.get(r) and not inbound[r]
    ]

    noncompliant = check_areas(vault)

    # ---- report ----
    out = []
    out.append(f"vault-linter — knowledge-graph integrity")
    out.append(f"scanned {len(notes)} notes in {vault}")
    out.append("")

    out.append(f"ERRORS")
    if broken:
        out.append(f"  broken wikilinks ({len(broken)}):")
        for note, lineno, target in sorted(broken):
            out.append(f"    {note}:{lineno}  [[{target}]]")
    else:
        out.append("  broken wikilinks (0): none")
    if broken_tables:
        out.append(f"  tables with no blank line before them ({len(broken_tables)}) — render as raw text, add a blank line:")
        for note, lineno, prev in sorted(broken_tables):
            out.append(f"    {note}:{lineno}  (under: {prev})")
    else:
        out.append("  tables with no blank line before them (0): none")
    out.append("")

    out.append(f"WARNINGS")
    if orphans:
        out.append(f"  orphaned notes ({len(orphans)}) — no inbound or outbound links:")
        for r in sorted(orphans):
            out.append(f"    {r}")
    else:
        out.append("  orphaned notes (0): none")
    if missing_trace:
        out.append(f"  capture notes missing source/captured_from ({len(missing_trace)}):")
        for r in sorted(missing_trace):
            out.append(f"    {r}")
    else:
        out.append("  capture notes missing source/captured_from (0): none")
    if ambiguous:
        out.append(f"  ambiguous bare links ({len(ambiguous)}) — basename not unique, path-qualify them:")
        for note, lineno, target in sorted(ambiguous):
            out.append(f"    {note}:{lineno}  [[{target}]]")
    else:
        out.append("  ambiguous bare links (0): none")
    if noncompliant:
        out.append(f"  non-compliant Areas ({len(noncompliant)}) — missing init-area structure:")
        for area, missing in noncompliant:
            out.append(f"    {area}  — missing: {', '.join(missing)}")
    else:
        out.append("  non-compliant Areas (0): none")
    out.append("")

    out.append(
        f"summary: {len(broken)} broken link(s), {len(broken_tables)} broken table(s), "
        f"{len(orphans)} orphan(s), {len(missing_trace)} missing-traceability, "
        f"{len(ambiguous)} ambiguous link(s), {len(noncompliant)} non-compliant area(s) "
        f"across {len(notes)} notes."
    )
    report = "\n".join(out)
    counts = {
        "broken": len(broken),
        "broken_tables": len(broken_tables),
        "orphans": len(orphans),
        "missing_trace": len(missing_trace),
        "ambiguous": len(ambiguous),
        "noncompliant": len(noncompliant),
    }

    if args.headless:
        return run_headless(vault, report, counts)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
