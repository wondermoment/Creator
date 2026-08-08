---
type: synthesis
status: active
created: {{today}}
area: "{{area_slug}}"
tags:
  - {{area_slug}}
---

# Synthesis: {{topic_name}}
**Date:** {{today}} · **Area:** {{area_link}} · **Sources:** {{sources_list}}

**TL;DR:** {{tldr}} <!-- ≤3 sentences: what these sources change about the Area + the #1 action. Single-source mode: open with "Single-source appraisal:". -->

## 1. Verdict per source
<!-- One row per selected source. "What it says" is ONE plain line. Verdict ∈ Use now / Test first / Park / Discard. "Why" ties to the MISSION or a constraint — "helps the current bet" is never a complete why. -->
| Source | What it says | Verdict | Why |
| :--- | :--- | :--- | :--- |
| {{source_1}} | {{one_plain_line_1}} | {{verdict_1}} | {{why_1}} |

## 2. What this means for {{area_display_name}}
<!-- Concrete before abstract: open every bullet with the thing (tool/pattern/number), then the point. Name sources. ≤150 words of prose per subsection. -->
### Optimize — hardens a current bet (name the bet)
- **{{concrete_thing}}** ({{sources}}): {{example_then_point}}

### Innovate — mission paths outside the current bets (proposed, not adopted — your call)
<!-- Includes parked/closed paths when evidence changed: state what changed since the parking decision. Never reopen silently. -->
- **{{concrete_thing}}** ({{sources}}): {{example_then_point}}

### Rulings & conflicts
<!-- Every Conflict-coded claim lands here. Clear winner → Ruling. User's call / high-stakes / undecidable → [CONFLICT] with the lean FIRST. -->
- **Ruling:** {{plain_ruling}} — because {{evidence}}.
- **[CONFLICT]** {{the_open_question}} — **Lean:** {{lean}}. Options: {{options_with_tradeoffs}}

## 3. Implementation plan
<!-- Only Use-now / Test-first verdicts generate steps. Executable without reading the sources. plan-to-kanban reads this section. -->
- [ ] **{{step_1}}** — where: {{artifact_or_location}} · effort: {{S_M_L}} · needs: {{dependency_or_dash}}

## 4. Discard pile
- **{{rejected_item}}** — {{one_plain_reason}}

## Appendix — evidence matrix
<!-- The scientific bookkeeping. One row per theme; Supporting Sources NAMES the sources (traceability). Status ∈ Convergent (independent) / Convergent (echoed) / Divergent / Unique; Weight per the SKILL.md anchors. Every selected source appears ≥1 time. -->
*Framework: {{area_context_status}} (hub note present / inferred).*

| Theme / Claim | Supporting Sources | Weight | Status |
| :--- | :--- | :---: | :--- |
| {{theme_1}} | {{sources_for_theme_1}} | {{weight_1}} | {{status_1}} |

---
*Generated via Best-Fit Framework Synthesis.*
