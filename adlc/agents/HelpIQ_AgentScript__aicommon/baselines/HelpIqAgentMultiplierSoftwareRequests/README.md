# Baseline — HelpIqAgentMultiplierSoftwareRequests

**Established:** 2026-05-13 (Phase 3c of HELPEXP-286 `adlc-drive`)
**Owner topic:** `HelpIqAgentMultiplierSoftwareRequests` (sub-agent of `HelpIQ_AgentScript`)
**Org:** `aicommon`

## What's here

| File | Source | Purpose |
|---|---|---|
| `utterances.txt` | Built from `~/HelpIQ-Evaluation/HelpIQ-Evals-Evals-Master.csv` (filtered: 27 rows tagged `Expected Subagent = HelpIqAgentMultiplierSoftwareRequests` + 58 unique rows in `Category = Software Access`) and `~/HelpIQ-Evaluation/helpiq-jsm-supplemental-eval-utterances.csv` (24 unique rows). 109 unique utterances, deduped. | Canonical regression-utterance pool for the multiplier topic. **Stage probe sets sample from this file** (typically 30/stage); the file itself is the reference set. Add to it across tickets — never delete. |
| `utterances.csv` | Same source, structured form with `source`, `product`, `category`, `subcategory`, `expected_subagent`, `expected_action`, `source_chat_id` columns. | Use for stratified sampling — top-N apps by frequency, license-required apps, qualifier-bearing apps, etc. |
| `scenarios/SW-ACCESS-0{1..4}.yaml` | Copied verbatim from `~/HelpIQ-Evaluation/evals/scenarios/SW-ACCESS-*.yaml` | Pre-existing multi-turn fixtures using simulator_rules format (NOT the new scripted-variation format — operator interpretation required). Coverage: Figma happy path (01), Zoom multiple access types (02), vague start probing (03), unsupported app (04). |

## Sourcing rationale

Per `adlc-drive` SKILL Phase 3c: "Baseline utterances live in ONE place only: `adlc/agents/{agent-dev-name}__{org-alias}/baselines/{topic}/utterances.txt`." This file is the SoT going forward.

Filter heuristic for the initial build:
1. **High-confidence multiplier** (27 rows): `Expected Subagent = HelpIqAgentMultiplierSoftwareRequests` in master CSV.
2. **Category-level multiplier** (58 unique rows): `Category = Software Access` in master CSV minus rows already tagged. Includes specific subcategories: New Access Request (45), License Request (9), Salesforce Access (7), Existing Access Issue (16) — though "Existing Access Issue" has overlap with troubleshooting that may route to general_qna.
3. **JSM supplemental** (24 unique rows): platform-specific access patterns from `helpiq-jsm-supplemental-eval-utterances.csv`.

**Known gap:** `Expected Subagent` was blank for 425 of 453 master rows. The category-based filter catches access patterns not explicitly tagged but is broader than strict "definitely multiplier" — some rows may actually route to general_qna at runtime. **Consequence: this baseline overcovers slightly. Stage probe sets curated from this file should weight toward the 27 tagged rows + apply explicit per-app/per-pattern stratification.**

## How execution should use this baseline

- **Stage 0.5 (pre-change baseline)** in `adlc-execute`: sample ~30 utterances stratified per the ticket's `Stage 0.6 Sampling rule` (top-20 apps + patterns-doc highlights + long-tail + leakage holdout). Run against v4 Active production AND fork starting state (two-pointer) through the new judge.
- **Per-stage probe sets**: 30 single-turn + 1-3 multi-turn YAMLs, refreshed each stage with leakage-holdout discipline. Holdout authors must NOT have seen the patterns-doc summary for those specific tickets.
- **Closeout regression sweep**: re-run all 109 baseline utterances against the closeout candidate; deltas vs. Stage 0.5 baseline must be within hard-gate tolerances (multiplier-row metrics within ±2 pts of v4).
- **Multi-turn YAMLs**: walk all 4 existing SW-ACCESS scenarios at Stage 0.5 baseline and at each stage gate; capture rubric scores. New stage-specific YAMLs (`SW-ACCESS-05-on-behalf-of.yaml`, `06-license-type.yaml`, `07-disambiguation.yaml`, `08-bulk-and-other.yaml`) authored in scripted-variation format per the ticket draft and added to `scenarios/` as the ticket progresses.

## Maintenance rules

- **Append-only.** New utterances added across tickets stack on top; existing utterances never removed (regression coverage shouldn't shrink).
- **No org outputs stored here.** Run results go in ticket folders' `eval/` or `results/` subdirs. This baseline is **utterances**, not **outputs** (per `adlc-drive` SKILL: "Baseline = utterances, not outputs. Old CSVs are invalid because org state changes between runs").
- **Source provenance required.** Every utterance in `utterances.txt` should be traceable to a source row in `utterances.csv` (or to the `# === Source: ===` group it appears under).

## Pointers

- HELPEXP-286 ticket folder: `../../tickets/HELPEXP-286-multiplier-ugb-port/`
- Ticket draft: `../../multiplier-ticket-draft.md`
- Sibling baseline: `../GeneralQnA_HelpIQ/`
- Master CSV: `~/HelpIQ-Evaluation/HelpIQ-Evals-Evals-Master.csv` (external)
- Patterns doc: `~/HelpIQ-Evaluation/access-request-patterns-2026q1.md` (external)
- Jira-audit (frequency analysis source): `~/HelpIQ-Evaluation/jira-audit-2026-0{1,2,3}/*-category-audit.csv` (external; verified present 2026-05-13)
