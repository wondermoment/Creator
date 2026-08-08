---
name: synthesize-drafts
description: >-
  Synthesize multiple research notes from an Area's draft/ and scout/ folders into a
  plain-language decision memo using best-fit framework synthesis: the Area's MISSION —
  not its current experiment — is the coding framework (hierarchy: mission / constraints
  / current bets), every source claim is judged against it (Optimize / Innovate /
  Conflict / Discard), parked paths resurface as options when evidence changes,
  contradictions get an explicit ruling or a [CONFLICT] choice with a stated lean, and
  surviving items become an executable implementation plan. Use when you have collected
  multiple curated drafts and/or scout sweeps and need to decide what they change about
  the Area. Both a curated draft and a scout are synthesis inputs.
---

# Synthesize Drafts

Analyze a collection of research notes — curated **drafts** (`draft/`) and broad **scouts** (`scout/`) alike — against the parent Area's goals, and answer one question: **what should this Area do because of these documents?** Synthesis ≠ summary: the output is a decision memo written for the user, not an evidence report written for an auditor. The scientific bookkeeping still happens — it lives in the appendix. A scout's `## Impact` analysis is as much a synthesis input as a draft's "what we can steal"; treat both folders as the same source class. (The name says "drafts" for history; the skill consumes both.)

## Method: Best-Fit Framework Synthesis

The framework comes first, **from the Area — not from the sources**.

1. **Build the framework — a hierarchy, not a flat list.** From the Area's hub note extract three layers and keep them distinct:
   - **Mission** — why the Area exists (the hub's goal section). This is the yardstick for every relevance judgment. Only the user changes it.
   - **Constraints** — the non-negotiables (validation gates, risk rules, scope exclusions). They bind every option.
   - **Current bet(s)** — the approach/instrument the Area is running right now (a rig, a venue, a chosen track), plus the recorded user decisions (chosen / parked / closed paths). A bet is one falsifiable experiment under the mission — revisable, and **never the yardstick**. A hub log dominated by one bet's activity does not promote that bet to mission.
   No hub note → infer from the folder and notes, and say so in the output.
2. **Deconstruct the sources:** Extract each source's core claims, facts, and ideas, tracking *which source* each came from — traceability is mandatory.
3. **Code every claim against the mission — never against a current bet.** Mission-relevance decides the code; fit with a current bet is a second, *labeled* dimension ("mission-relevant, outside the current bet"), never grounds for discarding. Each claim gets exactly one code:
   - **Optimize** — improves how the Area pursues the mission through an existing bet. Name the bet it touches.
   - **Innovate** — serves the mission via a path the Area isn't running, **including parked or closed paths**: never silently reopen a recorded decision, but never bury it as noise either — resurface it as a decision option, stating what changed since it was parked.
   - **Conflict** — contradicts the mission, a constraint, another source, or challenges a current bet.
   - **Discard** — serves neither the mission nor a constraint, or adds no value. Say why in one plain line.
4. **Weigh the evidence, don't just tally it:** Convergence ≠ truth. Check whether agreeing sources are *independent* or echoing each other (the same blog post cited five times is one signal, not five). Weight by source authority and independence; flag echo-chamber agreement.
5. **Rule on every Conflict:** Weigh the sides by independence, authority, recency, and fit to the Area's constraints. Clear winner → write a visible ruling: *"Ruling: X — because Y."* No clear winner, **or** the call is high-stakes (money, deployment, anything irreversible) or otherwise the user's to make → a `[CONFLICT]` block: 2–3 options with tradeoffs, your lean stated first. Never resolve silently; never leave a contradiction undiscussed.
6. **Write the decision memo** (template below), ending in an implementation plan concrete enough to execute without reading the sources.

**Bet-status trigger (mandatory):** if the hub log shows a current bet just failed, stalled, or sits at an open fork (a negative result, a pending decision), the memo must pose the mission-level question — *given this result, which path serves the mission best?* — and parked paths re-enter the `[CONFLICT]` options. Never write a memo that optimizes a bet the log says is in doubt without asking whether the bet itself should continue.

## Language Contract (binding — checked in Done When)

The memo is read by a human, not a model. Every sentence obeys CLAUDE.md §12 (COMMS-PROFILE). Specifically:

- **TL;DR first:** ≤3 sentences at the top answering "what do these sources change about the Area, and what is the #1 action."
- **Concrete before abstract, every time:** name the tool, file, number, or quote before stating any principle.
- **No invented abstractions:** domain jargon is fine (§12: assume mastery), but coined abstract phrases are not — write "the testing rig and its rules", not "the validation boundary"; "a log of rejected strategies and why", not "structured rejection memory".
- **≤150 words of prose per section** (tables and the appendix exempt — a table is already the compression, and the verdict table must scale with source count); use a table wherever the content is multi-part, and keep table cells to one plain line.
- **Read-aloud test:** if a sentence would need a re-read when said to the user's face, rewrite it.

## Vault Paths

- Work areas: `vault/01-work/areas/`
- Personal areas: `vault/02-personal/areas/`
- Area Context: `vault/<part>/areas/<area-slug>/<area-slug>.md` (the `type: moc` hub note)
- Draft Folder: `vault/<part>/areas/<area-slug>/draft/` (curated "what we can steal" notes)
- Scout Folder: `vault/<part>/areas/<area-slug>/scout/` (broad discovery sweeps — same source class as drafts)
- Output Plan: `vault/<part>/areas/<area-slug>/synthesis/strategic-plan-{{kebab-topic}}.md`
- Output Template: `assets/templates/strategy-draft.md` (in this skill folder)

## Interactive Workflow

1.  **Discover Areas:** List subdirectories of `vault/01-work/areas/` and `vault/02-personal/areas/`.
2.  **Ask User for Area:** Present the list of Areas and ask which one to work in.
3.  **List Sources:** List the `.md` files in **both** the chosen Area's `draft/` and `scout/` folders (either may be empty or absent — skip a missing folder), **excluding any whose frontmatter is already `status: synthesized`** (those were processed in a prior run) and any `strategic-plan-*.md`. Only un-synthesized sources are candidates. Label each candidate with its folder (e.g. `[draft] foo`, `[scout] bar`) so the user can tell them apart. (If the user explicitly asks to re-process a synthesized source, they can override; otherwise it stays skipped.)
4.  **Ask User for Files:** Present the combined list of drafts and scouts and ask which ones to include in the synthesis (multi-select). A synthesis can mix both freely.
5.  **Read Context & Sources:**
    - Read the Area's hub note (`<area-slug>.md`, `type: moc`) and build the framework (method step 1). If the hub is missing, fall back to a `README.md`; if neither exists, infer context from the folder name and other notes, and record that the synthesis ran without an explicit hub note.
    - Read every selected source (draft or scout) **in full** — skimming breaks traceability and weighting. For a scout, the `## Impact` section carries its analytical read; mine it the same way you mine a draft's "what we can steal." **A scout's Tier-2 "More candidates (unverified)" links are leads, not evidence** — they can suggest a theme worth a row, but must not *support* a claim or raise its weight unless you fetch and verify them first. Only the scout's verified picks + its `## Impact` analysis count as evidence.
6.  **Analyze & Generate:**
    - **Determine the mode by source count first.** *Multi-source* (≥2 selected): full method. *Single-source* (exactly 1 selected — e.g. one rich scout): cross-source convergence is **impossible**, so every matrix row is `Unique` by definition and the memo is a **single-source appraisal** (see Output Standards). Never claim "Convergent", "independently-convergent", or "echoed" from a single source.
    - Apply the Best-Fit Framework Synthesis method (steps 1–6 above) and the Language Contract.
    - Fill `assets/templates/strategy-draft.md`.
    - `topic_name`: A descriptive name for the synthesis (ask the user or derive from context).
    - `today`: `YYYY-MM-DD`.
7.  **Write Output:**
    - Ensure the `synthesis/` folder exists (`mkdir -p`).
    - Save the plan to the Area's `synthesis/` folder as `strategic-plan-<kebab-topic>.md` — keep the `strategic-plan-` prefix (the Vault Paths contract and step 3's exclusion depend on it).
8.  **Stamp the sources:** In each source (draft **or** scout) included in this synthesis, edit **only the frontmatter** — set `status: synthesized` (overwriting `draft`/`active`) and record the plan in `synthesized_into`, which is a **list** (YAML sequence): on first synthesis write `synthesized_into: ["[[<plan-filename-without-ext>]]"]`; if the user explicitly re-processes an already-synthesized source into a *different* plan, **append** the new plan link to the existing list — never overwrite earlier entries (that would erase the first plan's traceability). Never touch the body. This is what makes step 3 skip them next time and lets the user see at a glance which sources are done and where they went.

## Output Standards

- **TL;DR:** the answer, ≤3 sentences — what changes for the Area and the #1 action. In single-source mode, open it with "Single-source appraisal:" and never claim convergence-based confidence.
- **Verdict per source (table):** one row per selected source — what it says in **one plain line** · verdict ∈ **Use now / Test first / Park / Discard** · why, tied to the **mission or a constraint** (name bet-fit separately when relevant — "helps the rig" is never a complete why). Every selected source appears here; nothing silently dropped.
- **Optimize / Innovate sections:** each entry opens with the concrete thing (tool, pattern, number) and names its supporting sources. Optimize entries name the bet they touch. Innovate entries are explicitly proposals for the user, never adopted-by-default; a resurfaced parked path states what changed since it was parked.
- **Rulings & conflicts:** every claim coded Conflict appears here, as a Ruling or a `[CONFLICT]` block. High-stakes calls always get the `[CONFLICT]` treatment with a lean — never a unilateral ruling.
- **Implementation plan:** `- [ ]` steps generated **only** by Use-now / Test-first verdicts — each names what to do, where (file/repo/tool), effort (S/M/L), and what it depends on. Executable without opening the sources. `plan-to-kanban` reads this section.
- **Discard pile:** every rejected idea with one plain reason — so it doesn't come back. Be ruthless: if an idea doesn't fit the Area's goals, it goes here explicitly.
- **Appendix — evidence matrix (traceable at any scale):** one row per theme; columns `Theme | Supporting Sources | Weight | Status`, where **Supporting Sources names the actual sources** (e.g. `[[a]], [[c]]`) so any claim can be traced back. Do **not** use one column per source — that breaks past a handful of drafts. A *complete* matrix covers every non-trivial theme and lists every selected source against at least one theme. Status ∈ Convergent (independent) / Convergent (echoed) / Divergent / Unique. Weight (High/Med/Low) reflects source authority and independence, not raw count. **Multi-source anchors:** `High` = ≥2 substantially independent, authoritative sources (or primary evidence: docs, data, code you verified); `Med` = one authoritative source, or several weak-but-independent ones; `Low` = a single weak source, or agreement that is echoed rather than independent. In **single-source** mode every row is `Unique`, and "High" weight means the *one* source traces the claim to multiple authoritative, substantially independent references **inside itself** — it does **not** mean vault notes converged.
- **Link disambiguation:** A bare `[[basename]]` resolves to the wrong note when that basename is not unique vault-wide (draft/scout filenames *do* collide across Areas). Before emitting any source link — in the verdict table, the matrix, the `Sources:` header, anywhere — check whether its basename is unique; if not, **path-qualify** it as `[[<part>/areas/<area>/<draft|scout>/<name>|<name>]]`. Paths in wikilinks are relative to the **Obsidian vault root** (the `vault/` folder — where `.obsidian/` lives), so never include a `vault/` prefix: Obsidian cannot resolve it. Unique basenames may stay bare.

## Constraints

- Never modify a source's **body/content** (draft or scout). The *only* permitted change is the frontmatter stamp from step 8 (`status: synthesized` + `synthesized_into`).
- Never write directly into the root of an Area folder — always use `draft/`/`scout/` for raw inputs or `synthesis/` for strategic plans.
- If the Area has no hub note (or `README.md`), infer the context from the folder name and other notes in the root of the Area.

## Done When

Do not report the synthesis complete until **all** of these hold — fix and re-check, don't stop early:

- [ ] **Coverage:** every selected source has a row in the verdict table **and** appears in ≥1 matrix row; nothing was silently dropped.
- [ ] **TL;DR:** present, ≤3 sentences, states the #1 action.
- [ ] **Conflicts closed:** every claim coded Conflict has a Ruling or a `[CONFLICT]` block with options + a stated lean; high-stakes calls are `[CONFLICT]`, never unilateral rulings.
- [ ] **Mission-anchored:** every verdict's "why" traces to the mission or a constraint — not merely to a current bet; if the hub log shows a bet in question, the memo poses the mission-level question and parked paths appear among the options.
- [ ] **Language contract:** no section over 150 words of prose (tables and appendix exempt; table cells stay one plain line); every Optimize/Innovate entry opens with its concrete referent; no coined abstractions survive the read-aloud test.
- [ ] **Plan executable:** each implementation step has what / where / effort / depends-on, and traces to a Use-now or Test-first verdict.
- [ ] **No placeholders:** no `{{...}}` template tokens remain in the output plan.
- [ ] **Links resolve:** every `[[wikilink]]` (verdict table, matrix, `Sources:` header, `synthesized_into`) points to a real note; non-unique basenames are path-qualified.
- [ ] **Mode honored:** one source → single-source appraisal with **no** convergence claim; ≥2 sources → `Convergent` status reflects real independence, not a tally.
- [ ] **Evidence discipline:** no claim rests on an unverified Tier-2 scout candidate.
- [ ] **Source diffs are frontmatter-only:** the sole change to each source is the step-8 stamp; no body was touched.
- [ ] **Next-run exclusion:** each synthesized source now carries `status: synthesized`, so step 3 will skip it next time.
