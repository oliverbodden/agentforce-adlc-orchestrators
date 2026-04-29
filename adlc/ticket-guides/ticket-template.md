# JIRA Ticket Template: Topic Instruction Optimization

> Copy this into a new PROJECT ticket. Fill in the bracketed fields.

---

**Title:** [Topic Name] — Compact topic instructions to ~60% without quality regression

**Type:** Story

**Labels:** `prompt-optimization`, `[agent-name]`, `[topic-name]`

---

## Context

The `[Topic Name]` topic instruction for `[Agent Display Name]` is currently [X] words. Longer instructions increase latency, consume more tokens, and are harder to maintain. We want to reduce the instruction to ~60% of its current length while maintaining or improving response quality.

**Agent:** [Agent Display Name] (`[Agent API Name]`)
**Org:** [org alias]
**Topic:** `[Topic DeveloperName]`
**Instruction record:** `GenAiPluginInstructionDef` ID `[instruction_def_id]`
**Instruction source of truth:** [authoring-bundle / UI-built Tooling API / unknown; adlc-drive will verify]
**Current instruction size:** [X] words
**Requested staging:** [single-stage / Stage 1: compaction, Stage 2: style polish / other]

## Requirements

1. Compact the topic instruction to ~60% of original word count (~[target] words)
2. Preserve all decision logic (strategy selection, escalation rules, match logic)
3. Preserve all reasoning scaffolding (Store: directives, step checkpoints)
4. Preserve all response templates (prescribed openers, closing lines, formatting)
5. Run full eval (102+ utterances) and compare against baseline

## Acceptance Criteria

- Overall eval results improve or hold vs baseline
- No individual metric regresses more than 10%
- Cross-topic regression check: other topics not affected
- Strategy-specific template adherence >= baseline (metrics vary per topic)
- Redundancy does not exceed [X]% (or accepted threshold)

## ADLC Acceptance State

`adlc-drive` will create `config.json` in Phase 3d after fresh baseline analysis. Criteria start as `proposed` and become authoritative only after the Phase 3 checkpoint is approved.

Suggested criteria to convert into `config.json`:

- `ticket_goal`: [target behavior or size reduction], priority [critical/high/medium/low], tolerance [exact/strict/standard/flexible/manual_review/informational], blocking [yes/no], stage [stage_1/current/future]
- `regression`: no approved metric regresses more than [threshold], priority [critical/high/medium/low], tolerance [standard or explicit number], blocking [yes/no]
- `product_acceptance`: [representative scenarios], priority [critical/high/medium/low], tolerance [manual_review], blocking [yes/no]

If this ticket intentionally defers work, state the future stage and reason here so deferred criteria are not misreported as failures.

## Eval Baseline

- **Baseline CSV:** [attach to ticket or provide local path]
- **Baseline version:** [e.g., v21]
- **Prior eval report (optional):** [attach if available — for context only, drive will generate a new one]
- **Baseline location:** `adlc/agents/[agent-dev-name]__[org-alias]/baselines/[topic]/utterances.txt`

> Note: `adlc-drive` will generate a fresh baseline from stored utterances where possible. Prior CSVs/reports are context, not a substitute for a fresh before-state run.

## Dependencies / Testability

- **Required context variables / routable IDs:** [none / list]
- **Required user/account/contact data:** [none / list]
- **Permissions / feature flags:** [none / list]
- **External systems / tokens:** [none / list]
- **RAG / retriever sources:** [none / list]
- **Lower-env testability:** [fully-testable-lower-env / partially-testable-lower-env / requires-prod-like-data / requires-token-or-context / requires-external-system / not-lower-env-testable]

## Product Acceptance Notes

- **Representative scenarios:** [list]
- **Tone / brand requirements:** [list]
- **Escalation / refusal / safety / auth / PII / payment concerns:** [list]
- **Diagnostic mode caveat:** [not expected / may need temporary user-facing diagnostic traces; requires HITL approval and removal/internalization before final GO]

## Approach

This ticket uses `adlc-drive` to orchestrate the optimization:

1. **Goal:** Pull this ticket via JIRA integration
2. **Refine:** Confirm topic scope, instruction record, baseline reference
3. **Discover:** Resolve canonical metadata/source of truth, pull current instruction, run baseline tests with fresh routable ID, create `discovery.json` and proposed `config.json`
4. **Plan:** Surgical compaction strategy (never full rewrite — preserves reasoning scaffolding), including staged execution if approved
5. **Execute:** Iterative loop — compact → test → evaluate → iterate against current-stage blocking criteria
6. **Present:** Eval report with before/after comparison and per-criterion `config.json` results
7. **Hand off:** Deploy/publish via `developing-agentforce` or leave in sandbox

## Key Learnings from Prior Optimizations

- **Never do a full rewrite** — removing Store: blocks and step checkpoints causes the LLM to shortcut to default/fallback behaviors
- **Surgical approach works:** cut separators, duplicate rules, verbose prose. Keep all reasoning flow intact
- **Test with routable ID** via Testing Center (sf agent preview doesn't support context variables)
- **HTML encoding in Testing Center output** — use `html.unescape()` in scoring scripts
- **Account data affects results** — always verify apparent regressions by running baseline instruction with same routable ID before fixing
- **Early directive sections are high-impact** — the LLM reads these first and forms its mental model. Removing directives from the top of the instruction has outsized effect
- **Eval metrics are topic-specific** — each topic has its own strategies, templates, and quality criteria. Discover these in Phase 3 before defining acceptance criteria

## Definition of Done

- Instruction compacted to target word count
- Apples-to-apples eval report generated (HTML + JSON where possible)
- `discovery.json` records source of truth, canonical ticket folder, instruction IDs, baseline CSV, config path, suite name, and diagnostic mode if used
- `config.json` records approved acceptance criteria, thresholds, stages, and Phase 6 results
- Regression and ticket-goal results reported separately
- Product acceptance and technical/process review completed or explicitly waived
- Environment/testability caveats documented
- Any temporary diagnostic traces removed/internalized or explicitly product-approved to remain
- Instruction deployed to target org
- Baseline promoted if shipping to prod
- Eval artifacts saved locally and submitted to the shared ADLC artifact repo when closing out: `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO`
